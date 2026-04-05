# Copy this file to gallery_config.py on the device (same directory as main.py).

# User detail
NAME = "John Doe"

# Shown on the launcher: one line is picked at random each time the menu is drawn.
QUOTES = [
    "The best camera is the one you have with you.",
    "Every picture tells a story.",
    "Life is a journey, not a destination.",
]

# WiFi credentials
WIFI_SSID = "your-wifi-ssid"
WIFI_PASSWORD = "your-wifi-password"

# Minutes between slideshow advances (stock launcher calls ih.sleep with this).
SLIDESHOW_INTERVAL_MINUTES = 60

# Where JPEGs live on the SD card (created automatically when possible).
GALLERY_SD_FOLDER = "/sd/gallery"

# --- Online sync (gallery_online only) ---

GITHUB_OWNER = "your-github-username"
GITHUB_REPO = "your-image-repo"
# Folder inside the repo (no leading slash). Use "" for repository root.
GITHUB_PATH = "images"
GITHUB_BRANCH = "main"

# Classic PAT or fine-grained token with Contents: Read on this repo.
GITHUB_PAT = ""

# How often to re-list and download from GitHub (wall clock, best effort using time.time()).
GITHUB_SYNC_INTERVAL_MINUTES = 360
