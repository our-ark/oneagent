import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createStore } from "../server/store.mjs";
import {
  prepareTurn,
  reason,
  approveQuote,
  validateContext,
} from "../server/agent.mjs";
const newStore = () =>
  createStore(mkdtempSync(join(tmpdir(), "oneagent-test-")));
const ctx = (surface = "dayform", size = 9) => ({
  surface,
  productId: surface === "dayform" ? "day-one" : "arc-02",
  size,
  contextRevision: 1,
  sessionId: "source-session",
});

test("preferences and candidates persist across store switches and reloads", () => {
  const directory = mkdtempSync(join(tmpdir(), "oneagent-persistence-"));
  const store = createStore(directory),
    s = store.create();
  reason(s, "Find work sneakers under $120, US 9", { surface: "phone" });
  reason(s, "Will this pair be comfortable?", ctx());
  const reply = reason(s, "Is this better than the first pair?", ctx("stride"));
  assert.match(reply.content, /\$14 more/);
  assert.match(reply.content, /\$123.20/);
  store.save(s);
  assert.deepEqual(createStore(directory).get(s.id).candidates, [
    "day-one",
    "arc-02",
  ]);
});
test("message context is immutable when the visible selection changes", () => {
  const s = newStore().create(),
    context = ctx();
  const { bound } = prepareTurn(s, "What about this pair?", context, "turn-1");
  context.surface = "stride";
  context.productId = "arc-02";
  context.size = 10;
  assert.equal(bound.surface, "dayform");
  assert.equal(bound.size, 9);
  assert.equal(s.messages[0].context.productId, "day-one");
});
test("source app cannot claim another store product or revoked access", () => {
  const s = newStore().create();
  assert.throws(
    () => validateContext(s, { ...ctx(), productId: "arc-02" }),
    /does not belong/,
  );
  s.grants.dayform.connected = false;
  assert.throws(() => prepareTurn(s, "Buy this", ctx(), "turn-1"), /revoked/);
});
test("checkout requires exact approval and retry is idempotent", () => {
  const s = newStore().create();
  reason(s, "Order this pair", ctx());
  assert.equal(s.orders.length, 0);
  const quote = s.quote.id;
  assert.throws(() => approveQuote(s, "wrong"), /no longer pending/);
  const first = approveQuote(s, quote),
    replay = approveQuote(s, quote);
  assert.equal(first.id, replay.id);
  assert.equal(s.orders.length, 1);
  assert.equal(s.stock["day-one"], 3);
  assert.equal(first.total, 107.8);
});
test("over-budget, expired, revoked, and unavailable checkouts are blocked", () => {
  const s = newStore().create();
  reason(s, "Buy this pair", ctx("stride"));
  assert.throws(() => approveQuote(s, s.quote.id), /above your budget/);
  s.quote.expiresAt = 0;
  assert.throws(() => approveQuote(s, s.quote.id, true), /expired/);
  reason(s, "Buy this pair", ctx("stride"));
  s.grants.stride.connected = false;
  assert.throws(() => approveQuote(s, s.quote.id, true), /Reconnect/);
  s.grants.stride.connected = true;
  s.stock["arc-02"] = 0;
  assert.throws(() => approveQuote(s, s.quote.id, true), /Availability/);
});
test("cancel removes purchase authority and preferences can be corrected", () => {
  const s = newStore().create();
  reason(s, "Order this pair", ctx());
  const quote = s.quote.id;
  reason(s, "Cancel checkout", ctx());
  assert.throws(() => approveQuote(s, quote), /no longer pending/);
  reason(s, "Set my budget to $150, size 10", { surface: "phone" });
  assert.equal(s.preferences.budget, 150);
  assert.equal(s.preferences.size, 10);
});
