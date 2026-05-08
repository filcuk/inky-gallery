import gc

import gallery_common as g

graphics = None
WIDTH = None
HEIGHT = None

_cfg = g.get_config()
UPDATE_INTERVAL = int(getattr(_cfg, "SLIDESHOW_INTERVAL_MINUTES", 60))

_files = []
_idx = -1
_status = ""
_path = None

gc.collect()


def update():
    global _files, _idx, _status, _path, UPDATE_INTERVAL
    gc.collect()
    cfg = g.get_config()
    try:
        UPDATE_INTERVAL = int(getattr(cfg, "SLIDESHOW_INTERVAL_MINUTES", 60))
    except Exception:
        UPDATE_INTERVAL = 60
    try:
        from gallery_log import log
        log("Offline: interval", UPDATE_INTERVAL, "minute(s)")
    except Exception:
        pass
    _path, _status = g.slideshow_next(cfg.GALLERY_SD_FOLDER)
    _files = []  # legacy, no longer used
    _idx = -1


def draw():
    global _path, _status
    if not _path:
        g.draw_status(graphics, WIDTH, HEIGHT, ["Offline gallery", _status or "No images"])
        return
    if not g.draw_jpeg(graphics, WIDTH, HEIGHT, _path):
        _path = None
        _status = "SD read failed — retrying"
