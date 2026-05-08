import gc
import time

from machine import reset

import gallery_common as g
from gallery_log import log
import inky_helper as ih

graphics = None
WIDTH = None
HEIGHT = None

UPDATE_INTERVAL = 1  # minutes (we reset immediately after drawing)

_status = ""
_done = False


def update():
    global _status
    gc.collect()
    cfg = g.get_config()
    folder = getattr(cfg, "GALLERY_SD_FOLDER", "/sd/gallery")

    if not g.ensure_sd(fast=True):
        if not g.ensure_sd():
            _status = "SD: " + g.friendly_sd_message(g.sd_mount_error() or "")
            return

    log("Randomise: generating playlist")
    items = g.generate_playlist(folder)
    g.save_position(-1, "")
    if items:
        _status = "Playlist shuffled (%d images)" % len(items)
    else:
        _status = "No images found in " + folder


def draw():
    global _done
    if _done:
        return
    g.draw_status(graphics, WIDTH, HEIGHT, ["Randomise", _status or "Done"])
    _done = True
    try:
        ih.clear_state()
    except Exception:
        pass
    time.sleep(1.0)
    reset()

