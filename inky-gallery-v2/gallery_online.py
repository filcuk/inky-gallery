import gc

import network

import gallery_common as g
import gallery_github as gh
import inky_helper as ih

graphics = None
WIDTH = None
HEIGHT = None

_cfg = g.get_config()
UPDATE_INTERVAL = int(getattr(_cfg, "SLIDESHOW_INTERVAL_MINUTES", 60))

_files = []
_idx = -1
_status = ""
_sync_note = ""

gc.collect()


def _wifi_ok():
    wlan = network.WLAN(network.STA_IF)
    return wlan.status() == 3


def update():
    global _files, _idx, _status, _sync_note
    gc.collect()
    cfg = g.get_config()

    # Use fast SD mount so we can show a message quickly if init is timing out.
    if not g.ensure_sd(fast=True):
        detail = g.sd_mount_error() or ""
        _sync_note = "SD: %s" % g.friendly_sd_message(detail)
        _files = []
        _status = "SD card not available"
        return

    # Bring up Wi-Fi only when online sync is needed.
    if (not _wifi_ok()) and getattr(cfg, "GITHUB_PAT", "") and gh.should_sync(cfg):
        ssid = getattr(cfg, "WIFI_SSID", "") or ""
        pwd = getattr(cfg, "WIFI_PASSWORD", "") or ""
        if ssid and pwd:
            ih.network_connect(ssid, pwd)

    if _wifi_ok() and getattr(cfg, "GITHUB_PAT", "") and gh.should_sync(cfg):
        err = gh.sync_from_github(cfg)
        _sync_note = "" if err is None else err
    elif not getattr(cfg, "GITHUB_PAT", ""):
        _sync_note = "Set GITHUB_PAT in gallery_config.py"

    g.ensure_dir(cfg.GALLERY_SD_FOLDER)
    _files = g.list_jpegs(cfg.GALLERY_SD_FOLDER)
    if not _files:
        lines = ["Online gallery", _sync_note or _status or "No JPEGs after sync"]
        _status = lines[-1]
        return
    st = g.load_slideshow_state("online")
    last_path = st.get("last_path")
    if last_path and last_path in _files:
        _idx = (_files.index(last_path) + 1) % len(_files)
    else:
        _idx = 0
    g.save_slideshow_state("online", {"last_path": _files[_idx]})
    _status = ""


def draw():
    global _files, _sync_note, _status
    if not _files:
        lines = ["Online gallery", _sync_note or _status or "No images"]
        g.draw_status(graphics, WIDTH, HEIGHT, lines)
        return
    path = _files[_idx]
    if not g.draw_jpeg(graphics, WIDTH, HEIGHT, path):
        _files = []
        _sync_note = _sync_note or "SD read failed (readblocks)"
        _status = "Will retry mount next cycle"
