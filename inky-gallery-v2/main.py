import gc
import time

import inky_helper as ih
import network
import random
from inky_frame import BLACK, BLUE, GREEN, WHITE
from machine import reset
from picographics import PicoGraphics

# Match your hardware / firmware (7.3" colour = Spectra).
from picographics import DISPLAY_INKY_FRAME_7 as DISPLAY
# from picographics import DISPLAY_INKY_FRAME_SPECTRA_7 as DISPLAY  # Newer 2025 revision

# Give USB time to initialise
time.sleep(0.5)

graphics = PicoGraphics(DISPLAY)
WIDTH, HEIGHT = graphics.get_bounds()
graphics.set_font("bitmap8")

network_online = False
name_provided = False
launcher_quotes = []

def launcher():
    ih.led_warn.off()

    if HEIGHT == 448:
        y_offset = 20
    elif HEIGHT == 480:
        y_offset = 35
    else:
        y_offset = 0

    # Draw the menu
    ## Background
    graphics.set_pen(WHITE)
    graphics.clear()

    ## Title
    graphics.set_pen(BLACK)
    graphics.rectangle(0, 0, WIDTH, 50)
    graphics.set_pen(WHITE)
    title = "Inky Gallery"
    title_len = graphics.measure_text(title, 4) // 2
    graphics.text(title, (WIDTH // 2 - title_len), 10, WIDTH, 4)

    ## Welcome message
    if name_provided:
        graphics.set_pen(BLACK)
        if launcher_quotes:
            quote = launcher_quotes[random.randrange(len(launcher_quotes))]
            welcome = "Welcome, " + NAME + "! " + quote
        else:
            welcome = "Welcome, " + NAME + "!"
        
        welcome_len = graphics.measure_text(welcome, 2) // 2
        graphics.text(welcome, (WIDTH // 2 - welcome_len), 60 + 10, 600, 2)

    ## First item
    graphics.set_pen(GREEN)
    graphics.rectangle(30, HEIGHT - (340 + y_offset), WIDTH - 100, 50)
    graphics.set_pen(1)
    graphics.text("A. Offline (SD card)", 35, HEIGHT - (325 + y_offset), 600, 3)

    ## Second item
    bx = 30
    by = HEIGHT - (280 + y_offset)
    bw = WIDTH - 100
    bh = 50
    if network_online:
        graphics.set_pen(BLUE)
        graphics.rectangle(bx, by, bw, bh)
        graphics.set_pen(1)
        graphics.text("B. Online (GitHub sync)", 35, HEIGHT - (265 + y_offset), 600, 3)
    else:
        graphics.set_pen(graphics.create_pen(220, 220, 220))
        graphics.rectangle(bx, by, bw, bh)
        graphics.set_pen(1)
        graphics.text("B. Online (GitHub sync) [UNAVAILABLE]", 35, HEIGHT - (265 + y_offset), 600, 3)

    ## Note
    graphics.set_pen(BLACK)
    note = "Hold A + E then press Reset to return here"
    note_len = graphics.measure_text(note, 2) // 2
    graphics.text(note, (WIDTH // 2 - note_len), HEIGHT - 30, 600, 2)

    ih.led_warn.on()
    graphics.update()
    ih.led_warn.off()

    # Now we've drawn the menu to the screen, we wait here for the user to select an app.
    # Then once an app is selected, we set that as the current app and reset the device and load into it.

    while True:
        if ih.inky_frame.button_a.read():
            ih.inky_frame.button_a.led_on()
            ih.update_state("gallery_offline")
            time.sleep(0.5)
            reset()
        if ih.inky_frame.button_b.read():
            if not network_online:
                time.sleep(0.3)
                continue
            ih.inky_frame.button_b.led_on()
            ih.update_state("gallery_online")
            time.sleep(0.5)
            reset()


ih.clear_button_leds()
ih.led_warn.off()

# Load WiFi credentials and attempt to connect
try:
    from gallery_config import WIFI_PASSWORD, WIFI_SSID

    ih.network_connect(WIFI_SSID, WIFI_PASSWORD)
    network_online = network.WLAN(network.STA_IF).status() == 3
except ImportError:
    print("Add WiFi credentials to gallery_config.py")

# Load name, if provided
try:
    from gallery_config import NAME

    name_provided = NAME is not None and NAME != ""
except ImportError:
    print("Add name to gallery_config.py")

# Load quotes, if provided
try:
    from gallery_config import QUOTES

    if isinstance(QUOTES, (list, tuple)) and len(QUOTES) > 0:
        launcher_quotes = [str(s) for s in QUOTES if s]
except ImportError:
    pass

if ih.inky_frame.button_a.read() and ih.inky_frame.button_e.read():
    launcher()

ih.clear_button_leds()

if ih.file_exists("state.json"):
    ih.load_state()
    ih.launch_app(ih.state["run"])
    ih.app.graphics = graphics
    ih.app.WIDTH = WIDTH
    ih.app.HEIGHT = HEIGHT
else:
    launcher()

gc.collect()

while True:
    ih.app.update()
    ih.led_warn.on()
    ih.app.draw()
    ih.led_warn.off()
    ih.sleep(ih.app.UPDATE_INTERVAL)
