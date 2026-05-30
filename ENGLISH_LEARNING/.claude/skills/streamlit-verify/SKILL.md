---
name: streamlit-verify
description: Verify the ENGLISH_LEARNING Streamlit app after editing src/app.py — syntax-check, boot it headless, confirm it serves HTTP 200 with no errors in the log, then clean up. Use this instead of re-typing the boot/curl/pkill steps by hand.
---

# streamlit-verify

One command to confirm an edit to the ENGLISH_LEARNING Streamlit app didn't break it.

## When to use
After editing `src/app.py` (or any module it imports), before committing/pushing.
This is the fast smoke test — it does NOT replace a real visual check of design
changes (Streamlit screenshots are unreliable; preview those with a static HTML
mockup instead).

## Run it
```bash
bash .claude/skills/streamlit-verify/verify.sh            # defaults: src/app.py, port 8567
bash .claude/skills/streamlit-verify/verify.sh src/app.py 8570
```

Exit code `0` = PASS, `1` = FAIL. It prints the HTTP code and any error lines
found in the Streamlit log.

## What it checks
1. **Syntax** — `ast.parse(src/app.py)` (catches the most common breakage).
2. **Boots** — launches `streamlit run` headless on the given port.
3. **Serves** — polls `http://localhost:PORT` until HTTP 200 (up to ~22s).
4. **No errors** — greps the captured log for `error|traceback|exception`
   (benign startup lines excluded).
5. **Cleans up** — stops the server (`kill` + `pkill -f "streamlit run app.py"`).

## Notes / gotchas
- Uses the **anaconda** interpreter/CLI (`/opt/anaconda3/bin/python`,
  `/opt/anaconda3/bin/streamlit`) — the system `python3` lacks the packages.
- A PASS means it loads and serves; it does NOT exercise Gemini calls or render
  every page. For runtime-behavior or design changes, still check the live app.
- See the memory note `reference_english_learning_streamlit_gotchas` for the
  iframe-sandbox / body-margin / native-button rules that cause most UI bugs here.
