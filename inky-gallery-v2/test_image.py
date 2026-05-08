"""
Test image mode: show one JPEG from internal flash.

Put the file on the Pico filesystem (e.g. Thonny → Save as /test/jwst1.jpg).
Use a non-progressive JPG at or below screen size. For SD instead, use a path
like /sd/gallery/photo.jpg (no need to change code if you only fix TEST_IMAGE_PATH).
"""

import gc
import os

import gallery_common as common 
from gallery_log import log

graphics = None
WIDTH = None
HEIGHT = None

# Path on device flash (not /sd — that is the SD card)
TEST_IMAGE_PATH = "/test/jwst1.jpg"

_done = False
_status = ""

gc.collect()


def update():
    global _status
    gc.collect()
    _status = ""
    try:
        os.stat(TEST_IMAGE_PATH)
    except OSError:
        _status = "Not found: " + TEST_IMAGE_PATH


def draw():
    global _done
    if _done:
        return
    if _status:
        log("Test image: ", _status)
        common.draw_status(graphics, WIDTH, HEIGHT, ["Test image", _status])
    else:
        log("Test image: drawing")
        common.draw_jpeg(graphics, WIDTH, HEIGHT, TEST_IMAGE_PATH)
    _done = True
