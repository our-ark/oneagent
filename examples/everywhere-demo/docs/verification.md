# Verification

Verified locally on September 12, 2026:

- Strict TypeScript and Vite production build passed. CopilotKit's UI dependencies produce a large-bundle warning; the build completes successfully.
- Six Node tests passed: conversation persistence, message-bound context, product ownership and revocation, exact/idempotent approval, checkout expiry/stock/budget checks, cancellation and preference corrections.
- Two Chrome browser tests passed: the complete phone → DAYFORM → STRIDE → DAYFORM checkout → phone receipt journey, plus revocation and explicit budget disclosure.
- The native Electron test passed: a desktop window opened the phone's session, read its existing conversation, and sent a reply visible on the phone surface.
- The same test verified message submission through the LAN address, and no horizontal overflow in the 390px phone/dashboard layouts. A physical handset was not connected during testing.
- Browser tests reported no uncaught page errors in the complete shopping journey.
- The production assets and phone/desktop routes build successfully. Live Claude requests were not exercised because no provider key was supplied.

Screenshots from the working tests:

- [DAYFORM and approved receipt](screenshots/dayform.png)
- [Phone companion](screenshots/phone.png)
- [STRIDE storefront](screenshots/stride.png)
- [Native Electron desktop](screenshots/desktop.png)

The tests create their own personal sessions and do not reset an existing presentation session. Run `npm run test:e2e` with the server running to repeat all three browser/native tests. The first Electron launch may download its platform runtime.

## Demo video

Created a 132.53-second, 1920 × 1080, 30 fps MP4 recording of the working workflow. The video includes synthesized narration, on-screen captions, downloadable English subtitles, a transcript, and nine chapter links. Output: `public/demo/oneagent-everywhere.mp4` (10.4 MB).

Verified actual browser playback, seeking, video dimensions, duration, and the nine chapter controls. The entire MP4 decoded without errors; narration samples were checked in every scene. No uncaught browser errors were reported during capture or player verification. The desktop footage shows the browser-rendered workspace also used by Electron.

[Watch the video](http://127.0.0.1:3107/demo/index.html) · [Generation instructions](../scripts/video/README.md)
