import gc
import os
import random
import time

from gallery_log import log
from machine import Pin, SPI

import jpegdec
import sdcard

_sd_mounted = False
_jpeg = None
_sd_last_error = None
_STATE_DIR = "/sd/.inky_gallery"
_STATE_FILE = _STATE_DIR + "/state.json"  # legacy-ish (per-app dict)
_PLAYLIST_FILE = _STATE_DIR + "/playlist.json"
_POSITION_FILE = _STATE_DIR + "/position.json"


class _Defaults:
    SLIDESHOW_INTERVAL_MINUTES = 60
    GALLERY_SD_FOLDER = "/sd/gallery"
    GITHUB_OWNER = ""
    GITHUB_REPO = ""
    GITHUB_PATH = ""
    GITHUB_BRANCH = "main"
    GITHUB_PAT = ""


def get_config():
    try:
        import gallery_config
        return gallery_config
    except ImportError:
        return _Defaults()


def sd_mount_error():
    """Last error message from ensure_sd(), or None."""
    return _sd_last_error


def friendly_sd_message(detail):
    """Short on-screen text for common mount failures."""
    if not detail:
        return "Insert SD card (FAT); reseat if needed"
    s = str(detail)
    if "ENODEV" in s or "Errno 19" in s:
        return "No SD detected — check card & contacts"
    return s[:72]


def invalidate_sd_mount():
    """After read/write failures (e.g. readblocks), drop /sd so ensure_sd() can remount."""
    global _sd_mounted
    if not _sd_mounted:
        return
    try:
        os.umount("/sd")
    except OSError:
        pass
    _sd_mounted = False


def reset_jpeg_decoder():
    global _jpeg
    _jpeg = None


def _make_sdcard(spi, cs):
    """Construct SDCard (match Pimoroni sd_test.py signature)."""
    return sdcard.SDCard(spi, cs)


def _spi_for_sd(baud):
    """Hardware SPI0 for Inky Frame SD (see pimoroni examples/sd_test.py).

    Do not pass firstbit=0 — on RP2350 builds that selects LSB and raises NotImplementedError.
    """
    cfg = get_config()
    spi_id = int(getattr(cfg, "SD_SPI_ID", 0))
    sck = Pin(int(getattr(cfg, "SD_SCK_PIN", 18)), Pin.OUT)
    mosi = Pin(int(getattr(cfg, "SD_MOSI_PIN", 19)), Pin.OUT)
    miso = Pin(int(getattr(cfg, "SD_MISO_PIN", 16)), Pin.OUT)
    if baud is None:
        return SPI(spi_id, sck=sck, mosi=mosi, miso=miso)
    return SPI(spi_id, baudrate=baud, sck=sck, mosi=mosi, miso=miso)


def ensure_sd(fast=False):
    """Mount the Inky Frame SD card at /sd. Returns True on success.

    fast=True performs a quick, minimal attempt intended for boot-time use so the UI
    doesn't appear to hang if the card is missing or slow to init.
    """
    global _sd_mounted, _sd_last_error
    if _sd_mounted:
        return True
    try:
        os.listdir("/sd")
        _sd_mounted = True
        return True
    except OSError:
        pass

    gc.collect()
    time.sleep_ms(30)
    _sd_last_error = None
    # Some Pico 2 W/Inky Frame builds will fail SD init if Wi-Fi is active first.
    try:
        import network
        try:
            wlan = network.WLAN(network.STA_IF)
            try:
                wlan.disconnect()
            except Exception:
                pass
            try:
                wlan.active(False)
            except Exception:
                pass
        except Exception:
            pass
    except ImportError:
        pass
    # Keep CS high before init; some cards/controllers are picky about startup state.
    cfg = get_config()
    cs = Pin(int(getattr(cfg, "SD_CS_PIN", 22)), Pin.OUT, value=1)
    time.sleep_ms(5)
    if fast:
        # One quick shot; keep it close to upstream.
        attempts = (None,)
    else:
        # Try upstream-default first, then a few conservative SPI baudrates.
        attempts = (None, 400000, 200000, 1000000)
    for spi_baud in attempts:
        sd_spi = None
        try:
            sd_spi = _spi_for_sd(spi_baud)
            sd = _make_sdcard(sd_spi, cs)
            os.mount(sd, "/sd")
            _sd_mounted = True
            return True
        except Exception as e:
            _sd_last_error = str(e)
            log("SD mount failed:", "spi=", spi_baud, type(e).__name__, e)
            try:
                if sd_spi is not None:
                    sd_spi.deinit()
            except OSError:
                pass
            time.sleep_ms(25)
    return False


def ensure_dir(path):
    if not ensure_sd():
        return
    try:
        os.mkdir(path)
    except OSError:
        pass


def _ensure_state_dir():
    if not ensure_sd():
        return False
    try:
        os.mkdir(_STATE_DIR)
    except OSError:
        pass
    return True


def _load_json(path, default):
    try:
        import ujson as json
    except ImportError:
        import json
    try:
        with open(path, "r") as f:
            raw = f.read()
        if not raw:
            return default
        data = json.loads(raw)
        return data
    except OSError:
        return default
    except Exception as e:
        log("_load_json:", path, type(e).__name__, e)
        return default


def _save_json(path, data):
    try:
        import ujson as json
    except ImportError:
        import json
    try:
        with open(path, "w") as f:
            f.write(json.dumps(data))
            f.flush()
        return True
    except Exception as e:
        log("_save_json:", path, type(e).__name__, e)
        return False


def load_slideshow_state(app_key):
    """Best-effort load of slideshow state from SD. Returns dict."""
    if not _ensure_state_dir():
        return {}
    data = _load_json(_STATE_FILE, {})
    if type(data) is not dict:
        data = {}
    out = data.get(str(app_key), {})
    return out if type(out) is dict else {}


def save_slideshow_state(app_key, state):
    """Best-effort save of slideshow state to SD. Does not raise."""
    if not _ensure_state_dir():
        return False
    data = _load_json(_STATE_FILE, {})
    if type(data) is not dict:
        data = {}
    data[str(app_key)] = state if type(state) is dict else {}
    return _save_json(_STATE_FILE, data)


def load_playlist(folder):
    """Load playlist from SD. Returns list of absolute image paths."""
    if not _ensure_state_dir():
        return []
    data = _load_json(_PLAYLIST_FILE, {})
    if type(data) is dict:
        items = data.get("items", [])
    elif type(data) is list:
        # Backward/hand-edited format: plain list
        items = data
    else:
        items = []
    if type(items) is not list:
        return []
    out = []
    folder = (folder or "").rstrip("/")
    for p in items:
        if not p:
            continue
        s = str(p)
        if folder and not s.startswith(folder + "/"):
            # ignore entries from other folders
            continue
        out.append(s)
    return out


def save_playlist(folder, items):
    if not _ensure_state_dir():
        return False
    folder = (folder or "").rstrip("/")
    payload = {
        "folder": folder,
        "created": int(time.time()) if time.time() >= 1e9 else 0,
        "items": [str(x) for x in (items or []) if x],
    }
    return _save_json(_PLAYLIST_FILE, payload)


def generate_playlist(folder):
    """Create a new randomly ordered playlist.json based on current SD files."""
    if not ensure_sd(fast=True):
        # Fast mount can fail on slow/flaky cards; fall back to full mount attempts.
        if not ensure_sd():
            return []
    files = list_jpegs(folder)
    if not files:
        save_playlist(folder, [])
        return []
    try:
        # MicroPython random can be deterministic on cold boot; seed best-effort.
        random.seed(time.ticks_ms())
    except Exception:
        pass
    # Fisher-Yates shuffle (avoids random.shuffle impl differences)
    n = len(files)
    for i in range(n - 1, 0, -1):
        j = random.randrange(i + 1)
        files[i], files[j] = files[j], files[i]
    save_playlist(folder, files)
    return files


def ensure_playlist(folder):
    """Return playlist items; generate if missing/empty."""
    items = load_playlist(folder)
    if not items:
        return generate_playlist(folder)
    # Prune entries that no longer exist on disk.
    pruned = []
    changed = False
    for p in items:
        try:
            os.stat(p)
            pruned.append(p)
        except OSError:
            changed = True
    if changed:
        save_playlist(folder, pruned)
    return pruned


def load_position():
    """Load current slideshow position. Returns dict with idx/path."""
    if not _ensure_state_dir():
        return {"idx": -1, "path": ""}
    data = _load_json(_POSITION_FILE, {})
    if type(data) is not dict:
        return {"idx": -1, "path": ""}
    idx = data.get("idx", -1)
    path = data.get("path", "")
    try:
        idx = int(idx)
    except Exception:
        idx = -1
    return {"idx": idx, "path": str(path) if path else ""}


def save_position(idx, path):
    if not _ensure_state_dir():
        return False
    try:
        idx = int(idx)
    except Exception:
        idx = -1
    return _save_json(_POSITION_FILE, {"idx": idx, "path": str(path) if path else ""})


def insert_into_playlist(items, insert_after_idx, new_paths):
    """Insert any missing paths immediately after insert_after_idx. Returns (new_items, first_inserted_path_or_none)."""
    if not items:
        items = []
    seen = set(items)
    to_add = []
    for p in new_paths or []:
        s = str(p) if p else ""
        if not s or s in seen:
            continue
        to_add.append(s)
        seen.add(s)
    if not to_add:
        return items, None
    if insert_after_idx is None:
        insert_after_idx = -1
    try:
        insert_after_idx = int(insert_after_idx)
    except Exception:
        insert_after_idx = -1
    insert_at = max(0, min(len(items), insert_after_idx + 1))
    out = items[:insert_at] + to_add + items[insert_at:]
    return out, to_add[0]


def slideshow_next(folder, jump_to_path=None, insert_next_paths=None, direction="next"):
    """Common slideshow step used by offline/online.

    - Ensures playlist exists (generates if missing)
    - Resumes from last saved position (by path) if possible
    - Optionally inserts new paths as 'next up' and jumps to the first inserted
    """
    if not ensure_sd(fast=True):
        # Fast mount is for UI responsiveness; fall back to full attempts before erroring.
        if not ensure_sd():
            return None, "SD: " + friendly_sd_message(sd_mount_error() or "")

    folder = (folder or "").rstrip("/")
    ensure_dir(folder)
    items = ensure_playlist(folder)
    if not items:
        return None, "No images in " + folder

    pos = load_position()
    cur_path = pos.get("path") or ""
    if cur_path and cur_path in items:
        cur_idx = items.index(cur_path)
    else:
        cur_idx = -1

    # Online mode can inject newly downloaded files right after current.
    if insert_next_paths:
        items, first_inserted = insert_into_playlist(items, cur_idx, insert_next_paths)
        save_playlist(folder, items)
        if first_inserted:
            jump_to_path = first_inserted

    if jump_to_path and jump_to_path in items:
        next_idx = items.index(jump_to_path)
    else:
        if direction == "prev":
            next_idx = (cur_idx - 1) % len(items)
        else:
            next_idx = (cur_idx + 1) % len(items)

    next_path = items[next_idx]
    save_position(next_idx, next_path)
    return next_path, ""


def list_jpegs(folder):
    if not ensure_sd():
        return []
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    out = []
    for n in names:
        if n.startswith("."):
            continue
        low = n.lower()
        if low.endswith(".jpg") or low.endswith(".jpeg"):
            out.append(folder + "/" + n)
    out.sort()
    return out


def get_jpeg_decoder(graphics):
    global _jpeg
    if _jpeg is None:
        _jpeg = jpegdec.JPEG(graphics)
    return _jpeg


def draw_status(graphics, width, height, lines):
    if graphics is None or width is None or height is None:
        log("draw_status: missing graphics or size")
        return
    try:
        graphics.set_pen(1)
        graphics.clear()
        graphics.set_pen(0)
        y = 20
        for line in lines:
            s = str(line)
            if len(s) > 180:
                s = s[:180]
            graphics.text(s, 8, y, width - 16, 2)
            y += 22
            if y > height - 40:
                break
        graphics.update()
    except Exception as e:
        log("draw_status:", type(e).__name__, e)
    gc.collect()


def draw_jpeg(graphics, width, height, path):
    """Decode path to screen. Returns False if SD/JPEG read failed (mount invalidated)."""
    global _jpeg
    gc.collect()
    ok = True
    try:
        j = get_jpeg_decoder(graphics)
        graphics.set_pen(1)
        graphics.clear()
        j.open_file(path)
        j.decode(0, 0, jpegdec.JPEG_SCALE_FULL)
    except Exception as e:
        ok = False
        log("draw_jpeg:", type(e).__name__, e)
        invalidate_sd_mount()
        reset_jpeg_decoder()
        graphics.set_pen(1)
        graphics.clear()
        graphics.set_pen(0)
        graphics.rectangle(0, (height // 2) - 30, width, 64)
        graphics.set_pen(1)
        graphics.text("SD or JPEG read failed", 8, (height // 2) - 24, width - 16, 2)
        tail = (path or "")[-40:]
        if tail:
            graphics.text(tail, 8, (height // 2) - 4, width - 16, 2)
        em = str(e)
        if em:
            graphics.text(em[:68], 8, (height // 2) + 16, width - 16, 2)
    try:
        graphics.update()
    except Exception as e:
        ok = False
        log("draw_jpeg update:", type(e).__name__, e)
    gc.collect()
    return ok
