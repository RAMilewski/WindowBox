# Installing WindowBox on Raspberry Pi OS (Trixie)

These instructions are for Raspberry Pi OS based on Debian 13 (Trixie),
using the Wayland/labwc desktop.

---

## 1. Update the system

```bash
sudo apt update && sudo apt upgrade -y
```

---

## 2. Install system dependencies

```bash
sudo apt install -y python3-tk python3-full git wlr-randr
```

---

## 3. Clone the repository

```bash
git clone https://github.com/RAMilewski/WindowBox.git ~/WindowBox
```

---

## 4. Install Python dependencies

Trixie restricts system-wide `pip` installs. Use a virtual environment:

```bash
cd ~/WindowBox
python3 -m venv venv
source venv/bin/activate
pip install Pillow
```

---

## 5. Add images and edit the playlists

Copy your image files into the `images/` subdirectory:

```bash
cp /path/to/your/images/*.jpg ~/WindowBox/images/
```

Edit the main playlist:

```bash
nano ~/WindowBox/playlist.txt
```

Uncomment and edit the example lines. A minimal working entry:

```
10, all, all, your-image.jpg
```

**Priority playlist** (`priority.txt`) — optional. Items here are shown
between each regular playlist item, cycling through all eligible entries.
If no priority items are eligible the regular playlist continues
uninterrupted. The format is identical to `playlist.txt`:

```bash
nano ~/WindowBox/priority.txt
```

---

## 6. Run it

From a terminal on the Pi desktop:

```bash
cd ~/WindowBox
./startbox.sh
```

Make the script executable first if needed:

```bash
chmod +x ~/WindowBox/startbox.sh
```

From an SSH session (to display on the Pi screen):

```bash
cd ~/WindowBox
source venv/bin/activate
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 python3 windowbox.py
```

**To stop:** press `Ctrl+C` in the terminal, or from another terminal:

```bash
pkill -f windowbox.py
```

---

## 7. Auto-start on boot

To launch WindowBox automatically when the Pi boots into its desktop,
create an XDG autostart entry:

```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/windowbox.desktop
```

Paste this content:

```ini
[Desktop Entry]
Type=Application
Name=WindowBox
Exec=/bin/bash -c "cd /home/ram/WindowBox && source venv/bin/activate && python3 windowbox.py"
X-GNOME-Autostart-enabled=true
```

> Replace `/home/ram` with your actual home directory (check with `echo $HOME`).

Reboot to activate:

```bash
sudo reboot
```

---

## Display rotation

`display_rotate` in `/boot/firmware/config.txt` has no effect on Trixie
because the KMS graphics driver is used. Use `wlr-randr` instead
(already installed in step 2).

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

Replace `HDMI-A-1` with your actual output name and `90` with your rotation.

---

## Tips

- Press `q` at the Pi keyboard to quit, or `Ctrl+C` in the terminal.
- `git pull` inside `~/WindowBox` to get the latest updates from GitHub.
- Animated GIFs and APNGs are supported and loop for the duration of their playlist slot.
- If running headless (no desktop), tkinter requires a running X/Wayland display — WindowBox will not work without one.
