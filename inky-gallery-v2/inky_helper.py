import json
import math
import os
import time

from gallery_log import log

import inky_frame
import network
from machine import PWM, Pin, Timer
from pcf85063a import PCF85063A
from pimoroni_i2c import PimoroniI2C

# Pin setup for VSYS_HOLD needed to sleep and wake.
HOLD_VSYS_EN_PIN = 2
hold_vsys_en_pin = Pin(HOLD_VSYS_EN_PIN, Pin.OUT)

# intialise the pcf85063a real time clock chip
I2C_SDA_PIN = 4
I2C_SCL_PIN = 5
i2c = PimoroniI2C(I2C_SDA_PIN, I2C_SCL_PIN, 100000)
rtc = PCF85063A(i2c)

led_warn = Pin(6, Pin.OUT)

# set up for the network LED
network_led_pwm = PWM(Pin(7))
network_led_pwm.freq(1000)
network_led_pwm.duty_u16(0)


# set the brightness of the network led
def network_led(brightness):
    brightness = max(0, min(100, brightness))  # clamp to range
    # gamma correct the brightness (gamma 2.8)
    value = int(pow(brightness / 100.0, 2.8) * 65535.0 + 0.5)
    network_led_pwm.duty_u16(value)


network_led_timer = Timer(-1)
network_led_pulse_speed_hz = 1


def network_led_callback(_t):
    # updates the network led brightness based on a sinusoid seeded by the current time
    try:
        brightness = (math.sin(time.ticks_ms() * math.pi * 2 / (1000 / network_led_pulse_speed_hz)) * 40) + 60
        value = int(pow(brightness / 100.0, 2.8) * 65535.0 + 0.5)
        network_led_pwm.duty_u16(value)
    except Exception:
        pass


# set the network led into pulsing mode
def pulse_network_led(speed_hz=1):
    global network_led_timer, network_led_pulse_speed_hz
    network_led_pulse_speed_hz = speed_hz
    try:
        network_led_timer.deinit()
    except Exception:
        pass
    try:
        network_led_timer.init(period=50, mode=Timer.PERIODIC, callback=network_led_callback)
    except Exception as e:
        log("pulse_network_led:", e)


# turn off the network led and disable any pulsing animation that's running
def stop_network_led():
    global network_led_timer
    try:
        network_led_timer.deinit()
    except Exception:
        pass
    try:
        network_led_pwm.duty_u16(0)
    except Exception:
        pass


def network_disconnect():
    """Ensure Wi-Fi is off and the network LED is off."""
    stop_network_led()
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
    try:
        network_led_pwm.duty_u16(0)
    except Exception:
        pass


def sleep(t):
    # Time to have a little nap until the next update
    rtc.clear_timer_flag()
    rtc.set_timer(t, ttp=rtc.TIMER_TICK_1_OVER_60HZ)
    rtc.enable_timer_interrupt(True)

    # Set the HOLD VSYS pin to an input
    # this allows the device to go into sleep mode when on battery power.
    hold_vsys_en_pin.init(Pin.IN)

    # Regular time.sleep for those powering from USB
    time.sleep(60 * t)


# Turns off the button LEDs
def clear_button_leds():
    inky_frame.button_a.led_off()
    inky_frame.button_b.led_off()
    inky_frame.button_c.led_off()
    inky_frame.button_d.led_off()
    inky_frame.button_e.led_off()


def network_connect(SSID, PSK):
    """Bring up STA and connect. Returns True if wlan.status() == 3. Does not raise."""
    try:
        wlan = network.WLAN(network.STA_IF)
        try:
            wlan.active(True)
        except OSError as e:
            log("WiFi active failed:", e)
            return False

        max_wait = 10
        pulse_network_led()
        try:
            wlan.config(pm=0xA11140)  # Turn WiFi power saving off for some slow APs
        except OSError:
            pass
        try:
            wlan.connect(str(SSID), str(PSK))
        except OSError as e:
            stop_network_led()
            try:
                led_warn.on()
            except Exception:
                pass
            log("WiFi connect failed:", e)
            return False

        while max_wait > 0:
            try:
                st = wlan.status()
            except OSError:
                break
            if st < 0 or st >= 3:
                break
            max_wait -= 1
            log("waiting for connection...")
            try:
                time.sleep(1)
            except OSError as e:
                log("WiFi wait sleep:", e)
                break

        stop_network_led()
        try:
            network_led_pwm.duty_u16(30000)
        except Exception:
            pass

        try:
            ok = wlan.status() == 3
        except OSError:
            ok = False
        if not ok:
            stop_network_led()
            try:
                led_warn.on()
            except Exception:
                pass
            return False
        return True
    except Exception as e:
        log("WiFi unexpected:", type(e).__name__, e)
        stop_network_led()
        try:
            led_warn.on()
        except Exception:
            pass
        return False


state = {"run": None}
app = None
STATE_PATH = "/state.json"


def file_exists(filename):
    try:
        return (os.stat(filename)[0] & 0x4000) == 0
    except OSError:
        return False


def clear_state():
    if file_exists(STATE_PATH):
        os.remove(STATE_PATH)


def save_state(data):
    with open(STATE_PATH, "w") as f:
        f.write(json.dumps(data))
        f.flush()


def load_state():
    global state
    data = json.loads(open(STATE_PATH, "r").read())
    if type(data) is dict:
        state = data
    
    try:
        from gallery_config import PERMANENT_SELECTION

        if PERMANENT_SELECTION is not None and PERMANENT_SELECTION != "":
            permanent_selection = PERMANENT_SELECTION
        else:
            log("Unable to load PERMANENT_SELECTION from gallery_config.py; defaulting to 'True'")
            permanent_selection = True
    except ImportError:
        log("Unable to load PERMANENT_SELECTION from gallery_config.py; defaulting to 'True'")
        permanent_selection = True
    
    if not permanent_selection:
        clear_state()


def update_state(running):
    global state
    state["run"] = running
    save_state(state)


def launch_app(app_name, persist=True):
    global app
    app = __import__(app_name)
    log(app)
    if persist:
        update_state(app_name)
