import express from "express";
import { networkInterfaces } from "node:os";
import { resolve } from "node:path";
import { existsSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { createServer as createHttpServer } from "node:http";
import { createStore, record, addMessage } from "./store.mjs";
import { products } from "./catalog.mjs";
import {
  AgentError,
  prepareTurn,
  reason,
  optionalModelAnswer,
  approveQuote,
} from "./agent.mjs";

if (existsSync(".env")) process.loadEnvFile(".env");
const app = express();
const httpServer = createHttpServer(app);
const store = createStore(resolve(process.env.DATA_DIR || "data"));
const clients = new Map();
const locks = new Set();
const port = Number(process.env.PORT || 3107);
app.use(express.json({ limit: "32kb" }));
app.use("/api", (_req, res, next) => {
  res.setHeader("Cache-Control", "no-store");
  next();
});
const snapshot = (s) => {
  const { turns, ...rest } = s;
  return {
    ...rest,
    products,
    mode: process.env.ANTHROPIC_API_KEY ? "live" : "demo",
  };
};
const publish = (s) => {
  store.save(s);
  for (const response of clients.get(s.id) || [])
    response.write(`data: ${JSON.stringify(snapshot(s))}\n\n`);
};
const sessionFor = (req) => {
  const s = store.get(req.params.id);
  if (!s)
    throw new AgentError("Session not found. Create a new demo session.", 404);
  return s;
};
const unlocked = (s) => {
  if (locks.has(s.id))
    throw new AgentError(
      "Bob is finishing a reply. Please try again in a moment.",
      409,
    );
};

app.get("/api/health", (_req, res) =>
  res.json({
    app: "oneagent-everywhere",
    ok: true,
    mode: process.env.ANTHROPIC_API_KEY ? "live" : "demo",
  }),
);
app.get("/api/network", (_req, res) => {
  const addresses = Object.values(networkInterfaces())
    .flat()
    .filter((x) => x && x.family === "IPv4" && !x.internal)
    .map((x) => `http://${x.address}:${port}`);
  res.json({ addresses });
});
app.post("/api/sessions", (_req, res) =>
  res.status(201).json(snapshot(store.create())),
);
app.get("/api/sessions/:id", (req, res) => res.json(snapshot(sessionFor(req))));
app.get("/api/sessions/:id/events", (req, res) => {
  const s = sessionFor(req);
  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
    "X-Accel-Buffering": "no",
  });
  res.write(`data: ${JSON.stringify(snapshot(s))}\n\n`);
  if (!clients.has(s.id)) clients.set(s.id, new Set());
  clients.get(s.id).add(res);
  const timer = setInterval(() => res.write(": heartbeat\n\n"), 15000);
  req.on("close", () => {
    clearInterval(timer);
    clients.get(s.id)?.delete(res);
  });
});
app.get("/api/sessions/:id/export", (req, res) => {
  res.setHeader(
    "Content-Disposition",
    'attachment; filename="bob-personal-context.json"',
  );
  res.json(snapshot(sessionFor(req)));
});
app.patch("/api/sessions/:id/grants/:app", (req, res) => {
  const s = sessionFor(req);
  unlocked(s);
  const grant = s.grants[req.params.app];
  if (!grant) throw new AgentError("Unknown store.");
  for (const key of ["connected", "shareBudget"])
    if (typeof req.body[key] === "boolean") grant[key] = req.body[key];
  if (!grant.connected) {
    grant.shareBudget = false;
    if (s.quote?.source === req.params.app) s.quote = null;
  }
  record(
    s,
    "PERMISSION",
    req.params.app,
    grant.connected
      ? "Store permissions updated by the user"
      : "Store access revoked by the user",
    grant,
  );
  publish(s);
  res.json(snapshot(s));
});
app.get("/api/sessions/:id/catalog/:app", (req, res) => {
  const s = sessionFor(req);
  const grant = s.grants[req.params.app];
  if (!grant?.connected)
    throw new AgentError("Store connection is revoked.", 403);
  const local = products.filter((p) => p.app === req.params.app);
  res.json({
    products: grant.shareBudget
      ? local.filter((p) => p.price <= s.preferences.budget)
      : local,
    authorizedContext: grant.shareBudget
      ? { budget: s.preferences.budget }
      : {},
    rankingSource: req.params.app,
  });
});
app.post("/api/sessions/:id/approve", (req, res) => {
  const s = sessionFor(req);
  unlocked(s);
  const order = approveQuote(
    s,
    req.body.quoteId,
    req.body.allowOverBudget === true,
  );
  publish(s);
  res.json(order);
});
app.post("/api/sessions/:id/cancel-quote", (req, res) => {
  const s = sessionFor(req);
  unlocked(s);
  if (s.quote?.id !== req.body.quoteId)
    throw new AgentError(
      "This checkout has changed. Refresh before cancelling.",
      409,
    );
  s.quote = null;
  s.taskStatus = "shopping";
  record(s, "APPROVAL", "user", "Checkout declined; no order created");
  publish(s);
  res.json(snapshot(s));
});

// CopilotKit's HttpAgent consumes these AG-UI events. The durable session,
// rather than the frontend agent instance, owns the continuing conversation.
app.post("/api/agent", async (req, res) => {
  const input = req.body;
  const c = input.forwardedProps || {};
  const s = store.get(c.ownerSession);
  if (!s) throw new AgentError("Session not found.", 404);
  unlocked(s);
  const last = input.messages?.filter((m) => m.role === "user").at(-1);
  if (!last || typeof last.id !== "string")
    throw new AgentError("A user message with a stable ID is required.");
  const prepared = prepareTurn(s, last.content, c, last.id);
  const threadId = input.threadId || s.id;
  const runId = input.runId || randomUUID();
  locks.add(s.id);
  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });
  const emit = (event) => {
    if (!res.destroyed) res.write(`data: ${JSON.stringify(event)}\n\n`);
  };
  emit({ type: "RUN_STARTED", threadId, runId });
  try {
    let reply = prepared.replay;
    if (!reply) {
      publish(s);
      // A short visible turn makes source-bound replies easy to test when switching apps.
      await new Promise((resolve) =>
        setTimeout(resolve, Number(process.env.DEMO_DELAY_MS || 550)),
      );
      let result = reason(s, last.content, prepared.bound);
      try {
        result = await optionalModelAnswer(
          s,
          last.content,
          prepared.bound,
          result,
        );
      } catch {
        result.modelFallback = true;
        record(
          s,
          "MODEL",
          "agent",
          "Model unavailable; used the local shopping workflow",
        );
      }
      reply = addMessage(s, "assistant", result.content, c.surface, {
        ...result,
        replyTo: last.id,
        context: prepared.bound,
      });
      s.turns[last.id] = reply;
      record(
        s,
        "DELIVERY",
        c.surface,
        "Reply delivered to the original session",
        { replyTo: last.id, sessionId: c.sessionId, productId: c.productId },
      );
      publish(s);
    }
    emit({
      type: "TEXT_MESSAGE_START",
      messageId: reply.id,
      role: "assistant",
    });
    for (const chunk of reply.content.match(/.{1,64}(?:\s|$)|.{1,64}/gs) || [])
      emit({ type: "TEXT_MESSAGE_CONTENT", messageId: reply.id, delta: chunk });
    emit({ type: "TEXT_MESSAGE_END", messageId: reply.id });
    emit({
      type: "STATE_SNAPSHOT",
      snapshot: { revision: s.revision, taskStatus: s.taskStatus },
    });
    emit({ type: "RUN_FINISHED", threadId, runId });
  } catch (error) {
    emit({ type: "RUN_ERROR", message: error.message });
  } finally {
    locks.delete(s.id);
    res.end();
  }
});

app.use("/api", (_req, res) =>
  res.status(404).json({ error: "Unknown API endpoint." }),
);
app.use((error, _req, res, _next) => {
  if (!res.headersSent)
    res.status(error.status || 500).json({
      error: error.status
        ? error.message
        : "An unexpected server error occurred.",
    });
});
if (process.env.NODE_ENV === "production") {
  app.use(express.static(resolve("dist")));
  app.get("/{*path}", (_req, res) => res.sendFile(resolve("dist/index.html")));
} else {
  const { createServer } = await import("vite");
  const vite = await createServer({
    server: { middlewareMode: true, hmr: { server: httpServer } },
    appType: "spa",
  });
  app.use(vite.middlewares);
}
httpServer.once("error", (error) => {
  console.error(
    error.code === "EADDRINUSE"
      ? `OneAgent could not start: port ${port} is already in use. Choose another PORT.`
      : `OneAgent could not start: ${error.message}`,
  );
  process.exit(1);
});
httpServer.listen(port, process.env.HOST || "0.0.0.0", () =>
  console.log(
    `OneAgent is ready at http://127.0.0.1:${port}\nMode: ${process.env.ANTHROPIC_API_KEY ? "Live model" : "Local demo (no API key required)"}`,
  ),
);
