---
name: brand-guidelines
description: The ENGLISH_LEARNING app's brand guidelines (動物風 / Animal v2) and how to render a one-page brand style sheet (logo wordmark, color palette with hex codes, type scale, components) for review. Use when the user asks to see, apply, or update the app's brand/visual identity, or types /brand-guidelines.
---

# brand-guidelines — ENGLISH_LEARNING (動物風 / Animal v2)

The single source of truth for the app's visual identity. Match `src/app.py`
(the `ANIMAL_CSS` block + the title markup) to these tokens.

## Color palette
| Token | Hex | Use |
|---|---|---|
| Cream BG | `#FFFBF2` | page background |
| Surface | `#FFFFFF` | cards, inputs, sidebar |
| **Honey ★** | `#F4C152` | primary accent: selected pills, primary buttons, focus |
| Honey Dark | `#E8AE3A` | hover/active, metric values, icons |
| Mint | `#9FD8A6` | section dots (h3), success accents |
| Pink Marker | `#FBD7E4` (text `#F49CB8`) | title marker underline |
| Text Brown | `#6B5644` | body & headings (NOT pure black) |
| Muted | `#B6A088` | captions, secondary text |
| Border | `#EFE1C8` | hairlines, dashed separators |

## Typography
- **Display / headings**: `Mochiy Pop One` (round, bubbly). H1 ~1.5rem, H2 ~1.2rem.
- **Body / UI**: `Zen Maru Gothic` (rounded gothic), weights 400/500/700.
- **Title treatment**: brown text with a pink **marker underline**
  (`linear-gradient(transparent 60%, #FBD7E4 60%)`). No heavy outline/shadow —
  the puffy pink-outline look was rejected.

## Components
- **Primary button**: honey gradient `135deg,#F8CE63,#F4C152`, brown text,
  border `#E8AE3A`, radius 18px, soft honey shadow.
- **Outline button** (e.g. 発音): white bg, `#B0863A` text, 2px honey border.
- **Pill / selected tab**: honey bg, brown text, radius 14px.
- **Badge** (part of speech): `#FCEFCF` bg, `#B0863A` text, radius 8px.
- **Icon button** (🎧 / －): 46×44 box, `#F5F5F5` bg, `#E0E0E0` border, radius 2px;
  － is red `#C0504D`.
- **Card**: white, 1px `#E8E8E8`, radius 10–14px, soft shadow.
- **Alerts**: success `#EFF7E6`/`#5C7A3A`, info `#FFF6E0`/`#A6792A`, radius 14px.

## Render the style sheet (preview)
```bash
bash .claude/skills/design-preview/render.sh \
     .claude/skills/brand-guidelines/brand-animal.html /tmp/brand.png 1040x980
```
Then `open /tmp/brand.png` (render.sh opens it automatically). Edit
`brand-animal.html` to evolve the brand, re-render, get approval, then update
`ANIMAL_CSS` in `src/app.py` to match and push (see `streamlit-verify` +
`feedback_english_learning_preview_before_push`).

## Notes
- This is the app's *own* brand, not Anthropic's.
- Don't use copyrighted characters (e.g. ちいかわ art) — palette/vibe only.
