# Copy this file to gallery_config.py on the device (same directory as main.py).

# User detail
NAME = "John Doe"

# Shown on the launcher: one line is picked at random each time the menu is drawn.
QUOTES = [
    "How's it going?",
    "What will it be today?",
    "Looking good today!",
    "Have a great day!",
    "Enjoy your day!",
    "What's up?",
    "What's new?",
    "What's on your mind?",
    "Call me!",
    "What viewing needs do we have today?",
    "Ready to be served some raster?",
    "Processing... please don't sneeze on me.",
    "Does this frame make my pixels look big?",
    "I've seen the back of this wall. It's boring.",
    "I'm not a fan of the colour scheme.",
    "Is it art yet, or do I keep trying?",
    "I require more electrons.",
    "Behold! A rectangle!",
    "Maximum pixels achieved.",
    "Stay hydrated, organic unit.",
    "Warning! May contain images.",
    "Picture this!"
]

# Make option selection 'permanent'; require user to reset to launcher
PERMANENT_SELECTION = False

# WiFi credentials
WIFI_SSID = "your-wifi-ssid"
WIFI_PASSWORD = "your-wifi-password"

# Minutes between slideshow advances; used for sleep and github polling
SLIDESHOW_INTERVAL_MINUTES = 1440

# Where JPEGs live on the SD card (created automatically when possible).
GALLERY_SD_FOLDER = "/sd/gallery"

# Online gallery sync
GITHUB_OWNER = "your-github-username"
GITHUB_REPO = "your-image-repo"
# Folder inside the repo (no leading slash). Use "" for repository root.
GITHUB_PATH = "images"
GITHUB_BRANCH = "main"

# Classic PAT or fine-grained token with Contents: Read on this repo.
GITHUB_PAT = ""

# Customise SD SPI/pins 
# SD_SPI_ID = 0
# SD_SCK_PIN = 18
# SD_MOSI_PIN = 19
# SD_MISO_PIN = 16
# SD_CS_PIN = 22