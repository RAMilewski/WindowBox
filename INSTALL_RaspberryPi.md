# Installing WindowBox on Raspberry Pi OS

## 1. Update the system

```bash
sudo apt update && sudo apt upgrade -y
```

## 2. Install system dependencies

```bash
sudo apt install -y python3-tk python3-pip git
```

`python3-tk` provides the tkinter display library. It is not installed by default.

## 3. Copy the WindowBox files to the Pi

**Option A — from a USB drive or network share:**
```bash
cp -r /path/to/WindowBox ~/WindowBox
```

**Option B — clone from a git repo (if you've pushed it there):**
```bash
git clone <your-repo-url> ~/WindowBox
```

**Option C — copy over SSH from your Mac:**
```bash
# Run this on your Mac, not the Pi
scp -r /Users/RAM/Documents/SPARK/WindowBox pi@raspberrypi.local:~/WindowBox
```

## 4. Install Python dependencies

Raspberry Pi OS Bookworm (2023+) restricts system-wide `pip` installs. Use a virtual environment:

```bash
cd ~/WindowBox
python3 -m venv venv
source venv/bin/activate
pip install Pillow
```

On older Pi OS versions (Bullseye and earlier) you can skip the venv:
```bash
pip3 install Pillow
```

## 5. Add images and edit the playlist

```bash
cp your-images/*.jpg ~/WindowBox/images/
nano ~/WindowBox/playlist.txt
```

Uncomment and edit the example lines. A minimal working entry:
```
10, all, all, your-image.jpg
```

## 6. Run it

If you are **at the Pi desktop** (or via VNC/RDP):
```bash
cd ~/WindowBox
source venv/bin/activate   # if using venv
python3 windowbox.py
```

If you are **connected over SSH** and want to display on the Pi screen:

*Bookworm and earlier (X11):*
```bash
DISPLAY=:0 python3 windowbox.py
```

*Trixie and later (Wayland):*
```bash
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 python3 windowbox.py
```

---

## Auto-start on boot (desktop session)

To launch WindowBox automatically when the Pi boots into its desktop:

```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/windowbox.desktop
```

Paste this content (adjust the path if you used a venv):

```ini
[Desktop Entry]
Type=Application
Name=WindowBox
Exec=/bin/bash -c "cd /home/pi/WindowBox && source venv/bin/activate && python3 windowbox.py"
X-GNOME-Autostart-enabled=true
```

> Replace `/home/pi` with your actual home directory if your username is not `pi` (check with `echo $HOME`).

Save and reboot:
```bash
sudo reboot
```

---

## Notes for Trixie-based Pi OS (Debian 13)

Pi OS Trixie uses **Wayland/labwc** by default instead of X11. WindowBox runs fine via XWayland, but there are two things to be aware of:

**Fullscreen under Wayland**

Tkinter's fullscreen mode can behave inconsistently under some Wayland compositors. If the window doesn't go truly fullscreen on launch, press `f` to force it, or add `-zoomed` as a fallback by editing `windowbox.py` line 37:

```python
self.root.attributes("-fullscreen", True)
self.root.attributes("-zoomed", True)   # add this line
```

**Autostart path**

labwc does not use the LXDE autostart folder, but the XDG autostart method (`~/.config/autostart/windowbox.desktop`) used in the section above still works on Pi OS Trixie — no changes needed.

---

## Tips

- **Fullscreen is the default.** Press `q` to quit when at the Pi keyboard, or `Ctrl+C` from an SSH terminal. To kill it from a second terminal: `pkill -f windowbox.py`
- **Animated GIFs and APNGs** require Pillow ≥ 9.4.0 — the `pip install Pillow` command above installs a compatible version.
- **Display rotation on Trixie:** `display_rotate` in `/boot/firmware/config.txt` does not work with the KMS driver. Use `wlr-randr` instead (see below).
- If running **headless** (no desktop at all), set up a desktop session or use a framebuffer-based viewer instead — tkinter requires a running X/Wayland display.

---

## Display rotation on Trixie (KMS/Wayland)

`display_rotate` in `/boot/firmware/config.txt` has no effect on Pi OS Trixie because the KMS graphics driver is used. Rotate the display via `wlr-randr` instead.

**Install wlr-randr:**
```bash
sudo apt install wlr-randr
```

**Find your output name:**
```bash
wlr-randr
```
Look for a line like `HDMI-A-1` or `DSI-1`.

**Rotate it:**
```bash
wlr-randr --output HDMI-A-1 --transform 90
```
Transform values: `normal`, `90`, `180`, `270`

**Make it permanent** by adding the command to labwc's autostart:
```bash
mkdir -p ~/.config/labwc
echo 'wlr-randr --output HDMI-A-1 --transform 90' >> ~/.config/labwc/autostart
```

Replace `HDMI-A-1` with your actual output name and `90` with your desired rotation.
