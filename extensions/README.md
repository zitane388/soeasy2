# Extensions Workspace

This directory is for browser extensions used by the project.

Recommended layout:

- `extensions/soeasy-capture/src/` : source code (commit)
- `extensions/soeasy-capture/dist/` : build output (do not commit)
- `extensions/soeasy-capture/node_modules/` : dependencies (do not commit)

Notes:

- Keep extension source under version control.
- Do not commit private keys, webstore credentials, or env secrets.
- Load unpacked extension from `src/` (or `dist/` if your build requires it).

Current canonical extension:

- `extensions/soeasy-capture/src`
