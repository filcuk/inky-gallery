import gc
import os
import time

from gallery_log import log
from machine import Pin, SPI

import jpegdec
import sdcard

_sd_mounted = False
_jpeg = None
_sd_last_error = None
_STATE_DIR = "/sd/.inky_gallery"
_STATE_FILE = _STATE_DIR + "/state.json"


class _Defaults:
    SLIDESHOW_INTERVAL_MINUTES = 60
    GALLERY_SD_FOLDER = "/sd/gallery"
    GITHUB_OWNER = ""
    GITHUB_REPO = ""
    GITHUB_PATH = ""
    GITHUB_BRANCH = "main"
    GITHUB_PAT = ""
    GITHUB_SYNC_INTERVAL_MINUTES = 360


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


def _make_sdcard(spi, cs, card_baud=100000):
    """Construct SDCard; optional card_baud for initial SPI clock during CMD0/ACMD41."""
    try:
        return sdcard.SDCard(spi, cs, baudrate=card_baud)
    except TypeError:
        return sdcard.SDCard(spi, cs)


def _spi_for_sd(baud):
    """Hardware SPI0 for Inky Frame SD (see pimoroni examples/sd_test.py).

    Do not pass firstbit=0 — on RP2350 builds that selects LSB and raises NotImplementedError.
    """
    sck = Pin(18, Pin.OUT)
    mosi = Pin(19, Pin.OUT)
    miso = Pin(16, Pin.OUT)
    if baud is None:
        return SPI(0, sck=sck, mosi=mosi, miso=miso)
    return SPI(0, baudrate=baud, sck=sck, mosi=mosi, miso=miso)


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
    cs = Pin(22, Pin.OUT)
    # Short sequence only: 12 nested tries each waited for full SD timeout → very slow boot with no card.
    if fast:
        # One quick shot at a conservative init speed; avoids multi-minute stalls at boot.
        attempts = (
            (400000, 100000),
        )
    else:
        attempts = (
            (None, 100000),
            (200000, 100000),
            (400000, 200000),
            (None, 400000),
            (1000000, 400000),
        )
    for spi_baud, card_baud in attempts:
        sd_spi = None
        try:
            sd_spi = _spi_for_sd(spi_baud)
            sd = _make_sdcard(sd_spi, cs, card_baud)
            os.mount(sd, "/sd")
            _sd_mounted = True
            return True
        except Exception as e:
            _sd_last_error = str(e)
            log("SD mount failed:", "spi=", spi_baud, "card=", card_baud, type(e).__name__, e)
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


def load_slideshow_state(app_key):
    """Best-effort load of slideshow state from SD. Returns dict."""
    if not _ensure_state_dir():
        return {}
    try:
        import ujson as json
    except ImportError:
        import json
    try:
        with open(_STATE_FILE, "r") as f:
            raw = f.read()
        data = json.loads(raw) if raw else {}
        if type(data) is not dict:
            data = {}
    except OSError:
        data = {}
    except Exception as e:
        log("load_slideshow_state:", type(e).__name__, e)
        data = {}
    out = data.get(str(app_key), {})
    return out if type(out) is dict else {}


def save_slideshow_state(app_key, state):
    """Best-effort save of slideshow state to SD. Does not raise."""
    if not _ensure_state_dir():
        return False
    try:
        import ujson as json
    except ImportError:
        import json
    try:
        try:
            with open(_STATE_FILE, "r") as f:
                raw = f.read()
            data = json.loads(raw) if raw else {}
            if type(data) is not dict:
                data = {}
        except OSError:
            data = {}
        data[str(app_key)] = state if type(state) is dict else {}
        with open(_STATE_FILE, "w") as f:
            f.write(json.dumps(data))
            f.flush()
        return True
    except Exception as e:
        log("save_slideshow_state:", type(e).__name__, e)
        return False


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
