# Shopping feature adapted from Enoch

OneAgent can use the `shop` skill to compare products through Shopify UCP,
send separate product cards in Telegram, and save completed searches to a local
browser page. The page offers product tabs, merchant links, cached thumbnails,
conversation history, and follow-up chat with the selected product in context.
Purchases remain a handoff to the human on the merchant website.

## Source and adaptation

The implementation was copied from `/Users/yuhangan/enoch`, branch
`yuhang/shop-feature`, HEAD `a34390a`. It includes the working-tree changes to
`local_web/page.py`, `local_web/shortlist.py`, and `test_enoch_local_web.py` that
were present during the review. The source checkout was not modified.

The existing skills already matched after adapting the agent name; the new
addition is `src/oneagent/skills/shop`. Imports, configuration paths, UI text,
skill registration, and application lifecycle hooks now use OneAgent. Existing
OneAgent identity and presentation behavior is preserved.

The Telegram provider is bundled under `libraries/telegram` and loaded through
the existing `genesis.toml` local dependency mechanism. It is also declared in
the inheritable body. This is necessary because the external Telegram reference
pin does not include the shop card renderer. Wheel-only deployments must install
the bundled provider separately.

## Review fixes

- Thumbnail requests reject private, loopback, reserved, and link-local IPs.
  DNS answers are checked before a connection, and the connection uses the
  validated IP while retaining the original hostname for HTTPS verification.
  Redirects receive the same checks. Environment proxies are not used for
  thumbnail downloads.
- Browser messages have distinct request IDs and a bounded status store.
  The page polls request completion, displays returned errors, and handles
  repeated identical questions without confusing them with older replies.
  Missing chat configuration and malformed requests are rejected immediately.
- Shortlist creation and startup reconstruction only accept completed tasks.
  Old shortlists tied to unsuccessful tasks are removed during reconstruction.
- The browser entry point checks current daemon ownership before dispatch.
  Disabled web configuration produces no page links. IPv6 loopback and ports
  assigned by the operating system produce links to the actual listener.
- Responses set a no-referrer policy so token-bearing page links are not sent
  as referrers when opening merchant links.

## Configuration

The default listener is `http://127.0.0.1:36624`. Change `local_web.port` in
private `.oneagent/config.yaml` if Enoch already uses that port on the same Mac.
Tokens, saved shortlists, cached images, and conversation data remain in ignored
private state. No credentials or personal shopping data were copied from Enoch.

Restart the running OneAgent process to load the feature, then follow the
[setup guide](shop-skill.md). Shopify UCP must be available under the account
running the bot; an existing healthy UCP profile can be reused.

## Validation

- Full regression suite: 926 tests run, 8 skipped, no failures.
- Focused shop, skill, application, and Telegram suite: 298 tests, one skip.
- Headless Chrome: product tabs, selected-product context, repeated questions,
  and sanitized error display passed using a temporary profile and mock data.
- Browser JavaScript syntax check and `git diff --check` passed.
- Confirmed the CLI lists `shop` and loads the bundled Telegram provider.

Validation uses temporary state and mocked chat/catalog data. It does not place
orders, run a live UCP search, send Telegram messages, or restart the user's bot.
