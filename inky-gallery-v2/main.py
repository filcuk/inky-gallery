import gc
import time

from gallery_log import log
import inky_helper as ih
import gallery_common as common
import random
from inky_frame import BLACK, WHITE, GREEN, BLUE, RED, YELLOW, ORANGE, TAUPE
from picographics import PicoGraphics

# Match your hardware
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

def _btn_read(btn):
    try:
        return btn.read()
    except Exception as e:
        log("button read:", type(e).__name__, e)
        time.sleep_ms(20)
        return False


def launcher():
    ih.led_warn.off()
    ih.clear_button_leds()
    
    if HEIGHT == 448:
        y_offset = 20
    elif HEIGHT == 480:
        y_offset = 35
    else:
        y_offset = 0

    # Draw the menu
    log("Launcher: drawing menu")
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

    ## A: Slideshow (online)
    bx = 30
    by = HEIGHT - (340 + y_offset)
    bw = WIDTH - 60
    bh = 50
    if network_online:
        graphics.set_pen(BLUE)
        graphics.rectangle(bx, by, bw, bh)
        graphics.set_pen(WHITE)
        graphics.text("A. Slideshow (online)", 60, HEIGHT - (325 + y_offset), 600, 3)
    else:
        graphics.set_pen(graphics.create_pen(220, 220, 220))
        graphics.rectangle(bx, by, bw, bh)
        graphics.set_pen(WHITE)
        graphics.text("A. Slideshow (online) [UNAVAILABLE]", 35, HEIGHT - (325 + y_offset), 600, 3)

    ## B: Slideshow (offline)
    graphics.set_pen(GREEN)
    graphics.rectangle(30, HEIGHT - (280 + y_offset), WIDTH - 60, 50)
    graphics.set_pen(WHITE)
    graphics.text("B. Slideshow (offline)", 60, HEIGHT - (265 + y_offset), 600, 3)

    ## C: Randomise
    graphics.set_pen(ORANGE)
    graphics.rectangle(30, HEIGHT - (220 + y_offset), WIDTH - 60, 50)
    graphics.set_pen(WHITE)
    graphics.text("C. Randomise", 60, HEIGHT - (205 + y_offset), 600, 3)

    ## D: Test image
    graphics.set_pen(graphics.create_pen(200, 200, 200))
    graphics.rectangle(30, HEIGHT - (160 + y_offset), WIDTH - 60, 50)
    graphics.set_pen(BLACK)
    graphics.text("D. Test Image", 60, HEIGHT - (145 + y_offset), 600, 3)

    # graphics.set_pen(graphics.create_pen(200, 200, 200))
    # graphics.rectangle(30, HEIGHT - (160 + y_offset), WIDTH - 60, 50)
    # graphics.set_pen(BLACK)
    # graphics.text("D. Test WIFI & SD card", 60, HEIGHT - (145 + y_offset), 600, 3)

    # graphics.set_pen(graphics.create_pen(200, 200, 200))
    # graphics.rectangle(30, HEIGHT - (100 + y_offset), WIDTH - 60, 50)
    # graphics.set_pen(BLACK)
    # graphics.text("E. Test image", 60, HEIGHT - (85 + y_offset), 600, 3)

    ## Note
    graphics.set_pen(BLACK)
    note = "Hold A + E then press Reset to return here"
    note_len = graphics.measure_text(note, 2) // 2
    graphics.text(note, (WIDTH // 2 - note_len), HEIGHT - 30, 600, 2)

    log("Launcher: updating display")
    ih.led_warn.on()
    try:
        graphics.update()
    except Exception as e:
        log("launcher: error ", type(e).__name__, e)
    ih.led_warn.off()

    log("Launcher: collecting garbage")
    gc.collect()

    # Activate LEDs
    ih.inky_frame.button_a.led_on()
    ih.inky_frame.button_b.led_on()
    ih.inky_frame.button_c.led_on()
    ih.inky_frame.button_d.led_on()
    if not network_online:
        ih.inky_frame.button_a.led_off()

    # Now we've drawn the menu to the screen, we wait here for the user to select an app.
    # Then once an app is selected, we set that as the current app and reset the device and load into it.
    log("Launcher: ready, listening for input")
    while True:
        if _btn_read(ih.inky_frame.button_a):
            log("Launcher: button A pressed")
            if not network_online:
                time.sleep(0.3)
                ih.inky_frame.button_a.led_off()
            else:
                ih.inky_frame.button_a.led_off()
                ih.update_state("gallery_online")
                ih.clear_button_leds()
                ih.start_button_led_throb(ih.inky_frame.button_a)
                return "gallery_online"
        if _btn_read(ih.inky_frame.button_b):
            log("Launcher: button B pressed")
            ih.inky_frame.button_b.led_off()
            ih.update_state("gallery_offline")
            ih.clear_button_leds()
            ih.start_button_led_throb(ih.inky_frame.button_b)
            return "gallery_offline"
        if _btn_read(ih.inky_frame.button_c):
            log("Launcher: button C pressed")
            # Randomise playlist in-place, stay on menu (no redraw).
            try:
                cfg = common.get_config()
                folder = getattr(cfg, "GALLERY_SD_FOLDER", "/sd/gallery")
                if common.ensure_sd(fast=True) or common.ensure_sd():
                    items = common.generate_playlist(folder)
                    common.save_position(-1, "")
                    try:
                        n = len(items) if items else 0
                        log("Randomise: shuffled", n, "image(s)")
                        if n:
                            preview = items[:5]
                            for i, p in enumerate(preview):
                                log("Randomise:", i, p)
                            if n > 5:
                                log("Randomise: ...")
                    except Exception:
                        pass
                else:
                    log("Randomise: SD unavailable:", common.sd_mount_error() or "")
            except Exception as e:
                log("Randomise:", type(e).__name__, e)

            # Throb a few times then return to waiting.
            try:
                ih.clear_button_leds()
                for _i in range(6):
                    ih.inky_frame.button_c.led_on()
                    time.sleep_ms(120)
                    ih.inky_frame.button_c.led_off()
                    time.sleep_ms(120)
            except Exception:
                pass
            ih.clear_button_leds()
            ih.inky_frame.button_a.led_on()
            ih.inky_frame.button_b.led_on()
            ih.inky_frame.button_c.led_on()
            ih.inky_frame.button_d.led_on()
            if not network_online:
                ih.inky_frame.button_a.led_off()
            continue
        if _btn_read(ih.inky_frame.button_d):
            log("Launcher: button D pressed")
            ih.inky_frame.button_d.led_off()
            ih.update_state("test_image")
            ih.clear_button_leds()
            ih.start_button_led_throb(ih.inky_frame.button_d)
            return "test_image"


log("Main: starting launcher")
ih.clear_button_leds()
ih.led_warn.off()

## Mount SD before Wi-Fi: on some Pico 2 W builds the card fails with ENODEV if Wi-Fi is brought up first.
## Use a fast/one-shot attempt so boot UI doesn't stall for minutes if SD init is slow.
try:
    log("SD pre-mount: fast attempt")
    if common.ensure_sd(fast=True):
        log("SD pre-mount: success")
except Exception as e:
    log("SD pre-mount: error ", e)

# Load WiFi credentials (do not connect here; connect only in online app)
try:
    from gallery_config import WIFI_PASSWORD, WIFI_SSID
    network_online = bool(WIFI_SSID) and bool(WIFI_PASSWORD)
    log("WiFi: config present" if network_online else "WiFi: config empty")
except ImportError:
    log("WiFi: undefined")
except Exception as e:
    log("WiFi: error ", e)
    network_online = False

# Load name, if provided
try:
    from gallery_config import NAME

    name_provided = NAME is not None and NAME != ""
    if not name_provided:
        log("Name: ", "empty")
except ImportError:
    log("Name: undefined")

# Load quotes, if provided
try:
    from gallery_config import QUOTES

    if isinstance(QUOTES, (list, tuple)) and len(QUOTES) > 0:
        launcher_quotes = [str(s) for s in QUOTES if s]
    else:
        log("Quotes: empty")
except ImportError:
    log("Quotes: undefined")

if _btn_read(ih.inky_frame.button_a) and _btn_read(ih.inky_frame.button_e):
    log("Input: A + E detected")
    app_name = launcher()
else:
    app_name = None

if app_name is not None:
    # Menu selection (no reboot): launch immediately.
    pass
elif ih.file_exists(ih.STATE_PATH):
    # Loads the JSON and launches the app
    log("State: loading state")
    ih.load_state()
    log("State: loaded")
    app_name = ih.state.get("run")
else:
    log("State: not found; starting launcher")
    app_name = launcher()

# Defensive: if we're about to run an offline-style app, ensure Wi-Fi is off.
try:
    if app_name != "gallery_online":
        ih.network_disconnect()
except Exception:
    pass

# Always start apps with button LEDs off.
try:
    ih.clear_button_leds()
except Exception:
    pass

# Don't re-write state.json here; launcher selection already wrote it.
# This allows PERMANENT_SELECTION=False to behave like "run once" on next boot.
ih.launch_app(app_name, persist=False)
log("State: app launched")

# Pass the graphics object from the launcher to the app
ih.app.graphics = graphics
ih.app.WIDTH = WIDTH
ih.app.HEIGHT = HEIGHT

# Get some memory back, we really need it!
log("Main: collecting garbage")
gc.collect()

# The main loop executes the update and draw function from the imported app,
# and then goes to sleep ZzzzZZz

# file = ih.file_exists("state.json")
# print(file)

while True:
    log("Main loop: start")
    ih.app.update()
    ih.led_warn.on()
    ih.app.draw()
    ih.led_warn.off()
    
    try:
        ih.stop_button_led_throb()
        ih.clear_button_leds()
    except Exception:
        pass
    
    try:
        mins = int(getattr(ih.app, "UPDATE_INTERVAL", 0))
    except Exception:
        mins = 0
    log("Main loop: sleep;", mins, "minute(s) until next wake")
    # Always turn off Wi-Fi (and its LED) before sleeping.
    try:
        ih.network_disconnect()
    except Exception:
        pass
    
    try:
        interval = int(getattr(ih.app, "UPDATE_INTERVAL", 60))
    except Exception:
        interval = 60
    ih.sleep(interval)
