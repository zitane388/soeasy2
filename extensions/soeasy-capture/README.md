# soeasy-capture

Chrome extension workspace for HTML capture integration.

## Suggested structure

- `src/manifest.json`
- `src/background.js`
- `src/content.js`
- `src/popup.html`
- `src/popup.js`

If you already have existing extension code, place it under `src/`.

## Local load (Chrome)

1. Open `chrome://extensions`
2. Enable Developer mode
3. Click `Load unpacked`
4. Select `extensions/soeasy-capture/src`

## Integration contract (current project)

- URL suffix is passed by app:
  - `#program=SOEASY2&site=<site_key>&mode=<mode>&...`
- Extension should capture page HTML and deliver it to local receiver used by the app.
- Keep message shape stable once wired.

