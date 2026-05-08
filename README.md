# Inky Gallery

Custom gallery for **Pimoroni Inky Frame**, aimed at 7.3 with **Raspberry Pi Pico 1/2 W**.

Official Inky Frame guide: **[Getting started with Inky Frame](https://learn.pimoroni.com/article/getting-started-with-inky-frame)**.

## Repository structure

- **`inky-gallery-v1/`**: earlier offline-only experiment
- **`inky-gallery-v2/`**: launcher with gallery offline/online modes
- **`inky-frame-original/`**: reference copy of stock launcher-style files

## Flashing firmware with Raspberry Pi Imager

1. **Download image**  
   Pimoroni MicroPython: [pimoroni/inky-frame](https://github.com/pimoroni/inky-frame/releases/latest)
   - Choose *'with-filesystem'* if you want bundled launcher and examples

2. **Bootloader mode**  
   With the USB cable disconnected, **hold the BOOT button**, then connect the USB. The board should appear as a USB drive
   - *If the drive doesn't show up on Windows but shows up in Device Manager, you may need to open Disk Management and assign it a drive letter*

3. **Flash the UF2**
  Drag-and-drop the .uf2 file onto the mounted drive, it will restart automatically

## Erasing flash ("nuke") on Pico / Pico 2 W

Wipe in case of corrupt filesystem, stuck `main.py`, or any odd behaviour.  
**[Pico Universal Flash Nuke](https://github.com/Gadgetoid/pico-universal-flash-nuke)** detects flash size and erases it; intended to work across **RP2040 and RP2350** with a single UF2.  
  
1. **Download the nuke**: [releases](https://github.com/Gadgetoid/pico-universal-flash-nuke/releases/latest)
1. **Enter BOOTSEL**, copy the nuke UF2 onto the drive, wait for it to finish and the board to reconnect
1. **Flash MicroPython** and restore your files

## Uploading files to Pico

1. Install [Thonny](https://thonny.org/)
2. Launch and select board at the bottom right corner
3. Press 'Stop' to attach/restart backend

## SD card

### SD: timeout waiting for v2 card
- Reformat the card
- Try using a different card
- Try using a 32GB or smaller card
- Try using a more recent make card

### `[Errno 19] ENODEV`
**`[Errno 19] ENODEV`** means MicroPython cannot see the SD hardware: reseat the card, format as **FAT**, try another card (see [Pimoroni’s SD notes](https://learn.pimoroni.com/article/getting-started-with-inky-frame)).  
`inky-gallery-v2` also **mounts the SD before Wi‑Fi starts** to avoid init-order problems on some **Pico 2 W** boards.