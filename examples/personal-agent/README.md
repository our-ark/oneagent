# Personal Agent example

This example brings the five personal-agent scenarios into OneAgent: research, scheduling and communication, shopping, coordination between agents, and ongoing personal tasks. It includes a profile, action policy, decision inbox, recommendation brief builder for Spotify/WeChat/Amazon, and a purchase review screen. The interface originated in the Dreamphones personal-agent H5 prototype and keeps user data in browser local storage. It does not read external accounts, change recommendation algorithms, send messages automatically, or pay for orders.

## Run locally

Requires Node 20+. From this directory run `npm install`, set `OPENAI_API_KEY` in the server environment, then run `npm run server` and `npm run dev` in separate terminals. Open the Vite URL. The CopilotKit sidebar receives the current profile, policy, decisions, platform preferences, and checkout cards as context. Its model can advise but cannot execute purchases. Keep the API key on the server; never add it to the Vite frontend or commit it.

## Discord

Create a Discord application, set its Interactions Endpoint URL to a public HTTPS proxy for `/api/discord/interactions`, and configure `DISCORD_PUBLIC_KEY` from the application's General Information page. Register two application commands: `setprefs` with string options `want` (required) and `avoid` (optional); `recommend` with required string option `platform` whose choices are `spotify`, `wechat`, `amazon`. Discord verifies the endpoint with a PING. Responses are ephemeral and preferences are scoped to the Discord user ID, stored in `PERSONAL_AGENT_DATA`. This is a separate store from the browser prototype; account linking is not implemented. Do not expose the local server publicly without authentication and operational hardening.

## Boundaries

The five workflows create local advice and approval records. A checkout card opens a merchant product page only after the user approves; the merchant handles final payment. External platform integrations require separate OAuth authorization and platform API support. Discord credentials and a reachable endpoint are needed to activate the bot.
