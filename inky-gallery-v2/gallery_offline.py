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

gc.collect()


def update():
    global _files, _idx, _status
    gc.collect()
    cfg = g.get_config()
    # Use fast SD mount so the UI doesn't appear hung on SD init timeouts.
    if not g.ensure_sd(fast=True):
        _status = "SD: " + g.friendly_sd_message(g.sd_mount_error() or "")
        _files = []
        return
    g.ensure_dir(cfg.GALLERY_SD_FOLDER)
    _files = g.list_jpegs(cfg.GALLERY_SD_FOLDER)
    if not _files:
        _status = "No images in " + cfg.GALLERY_SD_FOLDER
        return
    st = g.load_slideshow_state("offline")
    last_path = st.get("last_path")
    if last_path and last_path in _files:
        _idx = (_files.index(last_path) + 1) % len(_files)
    else:
        _idx = 0
    g.save_slideshow_state("offline", {"last_path": _files[_idx]})
    _status = ""


def draw():
    global _files, _status
    if not _files:
        g.draw_status(graphics, WIDTH, HEIGHT, ["Offline gallery", _status or "No images"])
        return
    path = _files[_idx]
    if not g.draw_jpeg(graphics, WIDTH, HEIGHT, path):
        _files = []
        _status = "SD read failed — retrying"
