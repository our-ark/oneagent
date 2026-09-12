# Add your scenario to OneAgent

The reusable core lives in `oneagent.collaboration`. It contains no travel or
shopping assumptions. Python 3.11+; the message store, HTTP transport, service,
and tool registry use the standard library. The optional OneAgent runtime bridge
uses the repository's existing provider dependencies.

## Quick start

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python examples/notes/roundtrip.py
.venv/bin/python examples/notes/roundtrip.py --real-model
.venv/bin/python -m unittest tests.test_collaboration -v
```

The default example is explicitly a transport fixture. The real-model option
requires an authenticated, configured OneAgent runtime. No hardcoded answers are
used by the runtime bridge.

## Application side

Create a `MessageStore(Path(...), app_id, shared_fields=(...))` in your backend.
Call `session(authenticated_owner)` and `message(authenticated_owner, body)` after
authenticating your user. Never take the owner from an untrusted request body.

A message body has `id`, `session_id`, `text`, arbitrary JSON-object `context`, and
optional `share` (the permitted structured return fields for this message).
Override `snapshot_context` to validate/enrich browser selections from your own
catalog, document, or domain state. The snapshot is saved at send time.

Use your own UI and authenticated endpoints to submit messages and render
`transcript(owner, session_id)`. This SDK does not impose a chat component.

`AppServer((host, port), store, {bearer_token: owner})` exposes:

- `GET /collaboration/events?after=0`: account-scoped events with increasing cursors.
- `POST /collaboration/sessions/{session_id}/outputs`: correlated agent replies.

Replies contain `id`, `in_reply_to`, `text`, and optional `shared_context`.
Only fields listed in the original message's `share` are accepted. Free-text
answers can also disclose information; the model must avoid unrelated private
context. Structured field checks are not a complete privacy guarantee.

The server is a headless reference adapter, not browser authentication or a public
production web server. Generate high-entropy tokens, keep them server-side, and
terminate HTTPS before exposing it beyond localhost. The client rejects remote
plain HTTP and redirects. Revocation removes the token/app registration.

## Agent side

```python
from pathlib import Path
from oneagent.collaboration import (
    AppClient, AgentState, CollaborationService, OneAgentResponder,
)

apps = [AppClient("my-app", "https://my-app.example", app_account_token)]
state = AgentState(Path("private/alice/journal.sqlite"), "alice-conversation")
service = CollaborationService(apps, state, OneAgentResponder(Path("private/alice/runtime")))
service.process_once()  # Host schedules polling and handles transient failures.
```

Every connected app continues the same conversation. App/session IDs still select
the reply destination. Register apps in trusted host code; no model-driven URL
connection is allowed. Each visitor needs separate agent state **and runtime root**
so inherited long-term memory is not shared between visitors. Keep one service
worker per state file. One instance serializes turns with a lock; multi-process
worker leasing is not implemented.

A custom `respond(payload, session_key)` callable can replace the runtime. It gets
`current`, the latest 40 completed `history` entries, and connected `apps`, and
returns a string or `{text, shared_context}`. Complete history remains in SQLite;
the existing runtime also persists its session. Retrieval/summarization beyond
this bounded window is a future extension.

The service saves output before delivering it and advances the cursor afterward.
A delivery retry reuses the same output without another model call. A crash during
reasoning can repeat reasoning; do not perform effects inside the respond callback.
Events are processed in each app's order; this is not global timestamp ordering.

## Domain actions

`ToolRegistry` registers named `Tool` objects with descriptions, JSON input schemas,
app-provided argument validators, handlers, and a `mutating` flag. `invoke` passes
an authenticated owner and stable request ID. Mutations require an explicit
host-provided authorization callback. Handlers must durably deduplicate request
IDs before external effects. JSON schemas describe tools to models; the required
validator is the enforcement boundary.

Tool registration is separate from message transport: the core does not silently
execute tools proposed by a model. A scenario can build a bounded reasoning/tool
loop around this registry, or use ordinary app APIs, while retaining app authority.

## Extension boundary

A new scenario supplies its UI, context validation, data, tools, and permissions.
It should not need to change `collaboration/`. The notes example and two-app tests
exercise the same contracts without travel assumptions. Presence discovery, OAuth,
SSE, browser extensions, distributed scheduling, and production checkout are not
part of this first core release.
