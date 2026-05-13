import gc

import network

import gallery_common as g
import gallery_github as gh
import inky_helper as ih
import inky_frame

graphics = None
WIDTH = None
HEIGHT = None

_cfg = g.get_config()
UPDATE_INTERVAL = int(getattr(_cfg, "SLIDESHOW_INTERVAL_MINUTES", 60))

_files = []
_idx = -1
_status = ""
_sync_note = ""
_path = None

gc.collect()


def _wifi_ok():
    wlan = network.WLAN(network.STA_IF)
    return wlan.status() == 3


def update():
    global _files, _idx, _status, _sync_note, _path, UPDATE_INTERVAL
    gc.collect()
    cfg = g.get_config()
    try:
        UPDATE_INTERVAL = int(getattr(cfg, "SLIDESHOW_INTERVAL_MINUTES", 60))
    except Exception:
        UPDATE_INTERVAL = 60

    nav = None
    try:
        nav = ih.consume_nav_request()
    except Exception:
        nav = None
    if nav == "prev":
        try:
            ih.start_button_led_throb(inky_frame.button_a)
        except Exception:
            pass
    elif nav == "next":
        try:
            ih.start_button_led_throb(inky_frame.button_e)
        except Exception:
            pass

    # Ensure SD is mounted before Wi-Fi is started
    if not g.ensure_sd(fast=True):
        if not g.ensure_sd():
            detail = g.sd_mount_error() or ""
            _sync_note = "SD: %s" % g.friendly_sd_message(detail)
            _path = None
            _status = "SD card not available"
            return

    # Bring up Wi-Fi only when online sync is needed (online gallery syncs every slideshow cycle).
    if (not _wifi_ok()) and getattr(cfg, "GITHUB_PAT", ""):
        ssid = getattr(cfg, "WIFI_SSID", "") or ""
        pwd = getattr(cfg, "WIFI_PASSWORD", "") or ""
        if ssid and pwd:
            ih.network_connect(ssid, pwd)

    new_files = []
    pat = getattr(cfg, "GITHUB_PAT", "") or ""
    if _wifi_ok() and pat:
        new_files, err = gh.sync_from_github(cfg)
        _sync_note = "" if err is None else err
        hook = (getattr(cfg, "WEBHOOK_URL", "") or "").strip()
        if hook and _wifi_ok():
            # Lazy import so a broken/missing gallery_webhook never prevents the gallery from loading.
            try:
                import gallery_webhook

                gallery_webhook.notify_github_sync(
                    cfg,
                    success=(err is None),
                    downloaded=len(new_files),
                    error=err,
                )
            except Exception:
                pass
        # Power saving: once sync (and optional webhook) are complete, shut Wi-Fi back down.
        try:
            ih.network_disconnect()
        except Exception:
            pass
    elif not pat:
        _sync_note = "Set GITHUB_PAT in gallery_config.py"

    # Slideshow step. If we downloaded new files, insert them as "next up" and jump to them.
    _path, _status = g.slideshow_next(
        cfg.GALLERY_SD_FOLDER,
        insert_next_paths=new_files,
        direction=("prev" if nav == "prev" else "next"),
    )
    _files = []  # legacy, no longer used
    _idx = -1


def draw():
    global _path, _sync_note, _status
    if not _path:
        lines = ["Online gallery", _sync_note or _status or "No images"]
        g.draw_status(graphics, WIDTH, HEIGHT, lines)
        return
    if not g.draw_jpeg(graphics, WIDTH, HEIGHT, _path):
        _path = None
        _sync_note = _sync_note or "SD read failed (readblocks)"
        _status = "Will retry mount next cycle"
