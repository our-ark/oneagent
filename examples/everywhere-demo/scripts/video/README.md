# Recreate the walkthrough video

The finished video is `public/demo/oneagent-everywhere.mp4`. Its player is at **http://127.0.0.1:3107/demo/index.html** while the demo server is running. English subtitles, a transcript, a poster, and chapter timings are in the same folder.

This is a recording of real interactions with the local demo. The framing and captions are provided by `stage.html`; the phone and store screens are live iframes of the application sharing a fresh personal session. Existing user sessions are not changed. Bob uses the deterministic demo workflow, orders are simulated, and the desktop segment shows the same web workspace used by Electron. Narration is generated using the installed macOS Samantha voice.

On macOS, with Google Chrome and the project dependencies installed:

```bash
# Terminal 1
npm run dev

# Terminal 2
node scripts/video/narrate.mjs
node scripts/video/record.mjs
python3 scripts/video/render.py
```

The renderer requires either `imageio-ffmpeg` in the Python environment or `FFMPEG=/absolute/path/to/ffmpeg`. FFmpeg needs libx264, atempo, and loudnorm support. The recorder uses Playwright's video encoder; if Playwright requests it, install it with `npx playwright install ffmpeg`.

`ONEAGENT_BASE_URL` overrides the server address, `PLAYWRIGHT_CHROME_PATH` overrides the Chrome executable, and `VIDEO_VOICE` overrides the installed macOS voice. Some sandboxed terminals cannot access the system speech service or launch Chrome; run the recording commands from a normal local terminal in that case.

Edit the narration, chapter labels, and target scene lengths in `scenes.json`. The recorder waits for actual UI replies and checkout results before proceeding. It captures calibration frames before and after the story; the renderer removes them and aligns narration with the recorded scene timestamps. Audio is normalized, mixed into stereo, and combined with H.264 video and AAC audio in a fast-start MP4.

Intermediate capture files are retained in `artifacts/video-work/` and ignored by Git. The final MP4 is standalone and can be shared without the server or project files.
