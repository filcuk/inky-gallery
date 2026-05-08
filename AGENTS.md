# AGENTS.md — context for LLM-assisted work

This file orients automated assistants and human contributors to **inky-frame**: custom firmware behaviour for **Pimoroni Inky Frame** devices (target: **7.3″ colour / Spectra-class** panel on **Raspberry Pi Pico 2 W** running **MicroPython**).

---

## Product and constraints

- **Hardware**: Inky Frame with Wi-Fi (Pico 2 W class). User storage is typically a **microSD card** mounted in firmware (e.g. `/sd`).
- **Runtime**: **MicroPython** on Pimoroni’s Inky Frame build — not CPython. Prefer the **standard library subset** and modules shipped with that firmware (`network`, `machine`, `ujson`, `urequest`, etc.).
- **Display**: E-paper updates are slow; apps usually **sleep** between refreshes to save power. Image pipelines often use **`jpegdec`** and **non-progressive JPEGs** sized at or below the panel resolution.
- **Secrets**: Wi-Fi lives in `secrets.py` on the device (pattern from upstream). **GitHub PATs and any tokens must never be committed**; use a dedicated config module on-device and `.gitignore` as needed.

---

## Repository layout

| Path | Role |
|------|------|
| **`inky-frame-original/`** | Snapshot of the **stock launcher and example apps** (`main.py`, `inky_helper.py`, `lib/`, per-button apps). Use this to see **exact** menu layout, `state.json` flow, and app contracts without chasing submodule history. |
| **`inky-gallery-v1/`** | First gallery attempt: **offline-only** slideshow from SD (based on [PiInk](https://github.com/tlstommy/PiInk)), single `main.py`, timer-driven. |
| **`inky-gallery-v2/`** | **Deployable gallery bundle**: stock-style `main.py` + `inky_helper.py`, `gallery_offline.py` / `gallery_online.py`, `gallery_common.py`, `gallery_github.py`, and `gallery_config.example.py` (copy to **`gallery_config.py`** on the device; gitignored). Copy these files to the **MicroPython device root** together with `secrets.py`. |
| **`pimoroni/`** | **Git submodule**: [github.com/pimoroni/inky-frame](https://github.com/pimoroni/inky-frame) — upstream examples, `inkylauncher`, docs. Prefer **`inky-frame-original/`** for “what ships on device” comparisons unless you need the full upstream tree. |

Root **`README.md`** may only cover firmware flashing; treat **this file** as the project intent doc until the human author expands the README.

---

## Intended behaviour (v2 goals)

1. **Keep the default launcher UX** — same idea as stock: boot into launcher or last app, **hold A + E and press Reset** to return to launcher, menu driven by physical buttons.
2. **Replace default launcher options** with two modes:
   - **Offline gallery** — slideshow from images already on the SD card.
   - **Online gallery** — periodically **sync images from a GitHub repository** (authenticated with a **PAT**), write them to SD, then run the slideshow (or equivalent update/draw loop).
3. **Configuration** (at minimum: slideshow interval, PAT, GitHub repo identity/path) should live in a **separate `.py` module** so the main logic stays readable and secrets can stay out of version control if desired.

v2 uses the **GitHub REST Contents API** (`Accept: application/vnd.github+json` for directory listing, `application/vnd.github.v3.raw` per-file download) with a **Bearer PAT**. Large directories may hit API pagination (not handled yet in v2).

---

## Launcher and app contract (stock pattern)

The stock `main.py` + `inky_helper.py` flow (see `inky-frame-original/`):

- On boot, if **A + E** are held → run **`launcher()`** (draw menu, wait for button, call `ih.update_state("<app_module_name>")`, `reset()`).
- Otherwise, if **`state.json`** exists → `load_state()`, `launch_app(state['run'])` (`import` that module), then inject **`graphics`**, **`WIDTH`**, **`HEIGHT`** from the launcher.
- Main loop: `ih.app.update()` → optional warn LED → `ih.app.draw()` → `ih.sleep(ih.app.UPDATE_INTERVAL)` (interval in **minutes** in stock examples).

Each launcher “app” is typically a **top-level `.py` file** (e.g. `nasa_apod.py`) implementing at least:

- **`UPDATE_INTERVAL`** — minutes between loop iterations (used by `inky_helper.sleep`).
- **`update()`** — fetch or prepare content.
- **`draw()`** — render to the shared **`graphics`** object and call **`graphics.update()`** when appropriate.

When adding gallery apps, **either** follow this contract so they plug into the existing launcher **or** deliberately fork `main.py`/`inky_helper.py` in v2 and document the new contract here.

---

## References

- Upstream submodule: [github.com/pimoroni/inky-frame](https://github.com/pimoroni/inky-frame)
- **Inky Frame (MicroPython) — `inky_frame` module**: [docs/inky_frame.md](https://github.com/pimoroni/inky-frame/blob/main/docs/inky_frame.md) (buttons, LEDs, RTC/sleep, colours, JPEG caveats)
- **PicoGraphics**: [micropython/modules/picographics/README.md](https://github.com/pimoroni/pimoroni-pico/blob/main/micropython/modules/picographics/README.md) (displays, pens, text, shapes, JPEG/PNG)
- Firmware releases: [github.com/pimoroni/pimoroni-pico/releases](https://github.com/pimoroni/pimoroni-pico/releases)
- Prior art for offline SD gallery: [github.com/tlstommy/PiInk](https://github.com/tlstommy/PiInk) (v1 in this repo is derived from that idea)

---

## Conventions for agents

- **Scope**: Prefer changes under **`inky-gallery-v2/`** unless the task is explicitly to update snapshots, submodule pins, or root docs.
- **Match the device**: Uncomment or select the correct **`picographics`** `DISPLAY_*` constant for **7.3″** (stock snapshots may show `DISPLAY_INKY_FRAME_7`; colour/Spectra builds may use a `*_SPECTRA_*` symbol — align with the user’s flashed firmware).
- **Memory**: Call **`gc.collect()`** around heavy network or decode steps if mirroring upstream examples.
- **Do not commit** real PATs, Wi-Fi passwords, or `secrets.py` contents.

When behaviour or layout diverges from this file, **update AGENTS.md** in the same change so future sessions stay aligned.
