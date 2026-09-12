import {
  mkdirSync,
  existsSync,
  readFileSync,
  writeFileSync,
  renameSync,
} from "node:fs";
import { randomUUID } from "node:crypto";
import { join } from "node:path";

export function createStore(directory) {
  mkdirSync(directory, { recursive: true });
  const path = join(directory, "sessions.json");
  const records = existsSync(path)
    ? JSON.parse(readFileSync(path, "utf8"))
    : {};
  const persist = () => {
    writeFileSync(path + ".tmp", JSON.stringify(records), { mode: 0o600 });
    renameSync(path + ".tmp", path);
  };
  return {
    get(id) {
      return records[id];
    },
    save(session) {
      records[session.id] = session;
      persist();
    },
    create() {
      const id = randomUUID();
      const session = {
        id,
        createdAt: new Date().toISOString(),
        revision: 0,
        preferences: {
          budget: 120,
          size: 9,
          priority: "Comfort for the walk to work",
        },
        grants: {
          dayform: { connected: true, shareBudget: false },
          stride: { connected: true, shareBudget: false },
        },
        messages: [],
        events: [],
        candidates: [],
        quote: null,
        orders: [],
        turns: {},
        stock: { "day-one": 4, "arc-02": 3 },
        taskStatus: "ready",
      };
      records[id] = session;
      persist();
      return session;
    },
  };
}

export function record(session, type, source, description, details = {}) {
  session.events.unshift({
    id: randomUUID(),
    type,
    source,
    description,
    details,
    at: new Date().toISOString(),
  });
  session.events = session.events.slice(0, 150);
  session.revision++;
}

export function addMessage(session, role, content, source, extra = {}) {
  const message = {
    id: randomUUID(),
    role,
    content,
    source,
    at: new Date().toISOString(),
    ...extra,
  };
  session.messages.push(message);
  return message;
}
