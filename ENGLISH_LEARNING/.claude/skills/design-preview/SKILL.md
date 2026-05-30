---
name: design-preview
description: Preview ENGLISH_LEARNING UI/design changes before pushing. Build a static HTML mockup that replicates the theme palette and components, render it to PNG with headless Chrome, and open it for the user to approve. Use this whenever a change is visual (colors, layout, fonts, button styles) — Streamlit's own screenshots are unreliable.
---

# design-preview

Show the user what a UI/design change will look like **before** pushing it,
because Streamlit headless screenshots only capture the loading skeleton.

## Workflow
1. **Copy the template** to a scratch file:
   ```bash
   cp .claude/skills/design-preview/template.html /tmp/mock.html
   ```
2. **Edit `/tmp/mock.html`** to reflect the proposed change. The template's
   `<head>` comment lists the current theme tokens (zen / animal) and the shared
   small-component styles — match `src/app.py` so the mock is faithful. For an
   A/B/C/D choice, lay the variants out side by side in one file.
3. **Render + open**:
   ```bash
   bash .claude/skills/design-preview/render.sh /tmp/mock.html /tmp/preview.png 1000x820
   ```
   It writes the PNG and `open`s it. Also `Read` the PNG yourself first to
   sanity-check fonts/colors loaded before showing the user.
4. **Get approval, then push.** (See memory `feedback_english_learning_preview_before_push`.)

## render.sh
```
render.sh HTML [OUT.png] [WIDTHxHEIGHT]   # defaults: /tmp/preview.png, 1000x820
```
Uses `--force-device-scale-factor=2` for a crisp @2x image and waits 1s for web
fonts. Falls back to Chromium if Google Chrome isn't installed.

## Notes
- Keep mock PNGs in `/tmp` (don't commit them).
- This mock is for **look** only. It cannot reproduce Streamlit-internal /
  `components.html` iframe behavior (height/clipping, sidebar toggle icons,
  parent-navigation limits) — verify those on the live app and say so.
- After approval, run `streamlit-verify` on the real edit before pushing.
