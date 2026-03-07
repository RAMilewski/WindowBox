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

**Priority playlist** (`priority.txt`) — optional. Items here are shown
between each regular playlist item, cycling through all eligible entries.
If no priority items are eligible the regular playlist continues
uninterrupted. The format is identical to `playlist.txt`:

```bash
nano ~/WindowBox/priority.txt
```

---

## Playlist format

Each non-blank, non-comment line has four comma-separated fields:

```
duration, days, timespan, filename
```

### duration

Number of seconds to display the image. Decimals are allowed (`2.5`).
Animated GIFs and APNGs loop continuously for the full duration.

### days

Controls which days of the month the entry is shown.
Multiple specs can be combined with `|` (no spaces around the pipe).
Matching is case-insensitive.

| Spec | Meaning |
|---|---|
| `all` or `*` | Every day |
| `Mon` `Tue` `Wed` `Thu` `Fri` `Sat` `Sun` | Every occurrence of that weekday |
| `Monday` `Tuesday` … | Full weekday names also accepted |
| `1st Mon` or `first Mon` | First Monday of the month |
| `2nd Tue` or `second Tue` | Second Tuesday of the month |
| `3rd Wed` or `third Wed` | Third Wednesday |
| `4th Thu` or `fourth Thu` | Fourth Thursday |
| `5th Fri` or `fifth Fri` | Fifth Friday (only exists some months) |
| `last Sat` | Last Saturday of the month |
| `1` … `31` | Specific date number (e.g. `1` = the 1st of every month) |

Both the numeric form (`2nd`) and the word form (`second`) are accepted.
Examples of combined specs:

```
Mon|Wed|Fri          weekdays only
Sat|Sun              weekends only
1st Mon|3rd Mon      first and third Monday
```

### timespan

A 24-hour time range, or `all` for no time restriction:

```
all                  any time of day
09:00-17:00          9 am to 5 pm
22:00-06:00          spans midnight (late night to early morning)
```

### filename

The name of a file inside the `images/` subdirectory.
Supported formats: `.jpg`, `.png`, `.gif`, animated `.gif`, animated `.png` (APNG).

### Examples

```
# Show for 10 seconds, every day, all day
10, all, all, logo.png

# Show on weekday mornings only
30, Mon|Tue|Wed|Thu|Fri, 08:00-12:00, weekday_morning.jpg

# Show on the first Monday of each month
20, 1st Mon, all, monthly_update.png

# Show on the last Friday afternoon
15, last Fri, 13:00-17:00, friday_special.jpg

# Show on the 1st of every month
60, 1, all, monthly_banner.png

# Animated GIF shown every Saturday morning
10, Sat, 08:00-12:00, weekend.gif
```

---

## 6. Run it

From a terminal on the Pi desktop:

```bash
cd ~/WindowBox
./startbox.sh
```

Make the scripts executable first if needed:

```bash
chmod +x ~/WindowBox/startbox.sh ~/WindowBox/killbox.sh ~/WindowBox/reload.sh
```

**To run detached** (survives closing the terminal):

```bash
~/WindowBox/startbox.sh -b
```

Output is logged to `~/WindowBox/windowbox.log`. Playlist and media activity (which image is showing, file changes) is logged separately to `~/WindowBox/media.log`. To watch them live:

```bash
tail -f ~/WindowBox/windowbox.log
tail -f ~/WindowBox/media.log
```

From an SSH session (to display on the Pi screen):

```bash
cd ~/WindowBox
source venv/bin/activate
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 python3 windowbox.py
```

**To stop:** press `q` at the Pi keyboard, `Ctrl+C` in the terminal, or:

```bash
~/WindowBox/killbox.sh
```

---

## 7. Reload playlists without restarting

After editing `playlist.txt` or `priority.txt`, or adding new images,
run the reload script — no restart needed:

```bash
~/WindowBox/reload.sh
```

Make it executable first if needed:

```bash
chmod +x ~/WindowBox/reload.sh
```

This pulls the latest changes from GitHub and signals WindowBox to reload
both playlists immediately.

To reload without pulling from GitHub (e.g. after editing files directly
on the Pi):

```bash
pkill -USR1 -f windowbox.py
```

---

## 8. Auto-reload on a schedule

To pull updates from GitHub and reload WindowBox automatically once an hour,
add a cron job:

```bash
crontab -e
```

Add this line:

```
0 * * * * /home/ram/WindowBox/reload.sh
```

> Replace `/home/ram` with your actual home directory.

Verify it was saved:

```bash
crontab -l
```

---

## 9. Auto-start on boot

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

## Display aspect ratio correction

Some monitors (such as LG HDR WFHD ultrawide panels) have a native resolution
of 2560x1080 but report themselves to the system as 1920x1080, then stretch
the incoming signal horizontally to fill the panel. This makes standard images
look distorted.

WindowBox can pre-squish images to compensate. Edit `windowbox.py` and set
the two constants near the top of the file:

```python
DISPLAY_SQUISH = 3/4            # Pi output width ÷ panel native width
DISPLAY_SQUISH_AXIS = "height"  # "width" for landscape, "height" for 90°/270° rotation
```

The correction factor is always `Pi output ÷ panel native` — in this case
`1920 ÷ 2560 = 3/4`.

If the display is rotated 90° or 270° via `wlr-randr`, the monitor's
horizontal stretch maps to the vertical axis in logical screen space, so use
`"height"`. For an unrotated landscape display use `"width"`.

The default value of `1.0` disables the correction (normal display).
Your original image files are not modified — the correction is applied at
display time. Set it back to `1.0` if you move to a standard monitor.

After editing, reload WindowBox:

```bash
~/WindowBox/reload.sh
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

- Press `q` at the Pi keyboard to quit, or run `~/WindowBox/killbox.sh` from any terminal.
- `~/WindowBox/reload.sh` pulls from GitHub and reloads playlists without restarting.
- `~/WindowBox/startbox.sh -b` runs WindowBox detached from the terminal; general logs go to `windowbox.log`, media activity to `media.log`.
- `git stash` before `git pull` if you have local changes to playlist files; `git stash pop` to restore them after.
- Animated GIFs and APNGs are supported and loop for the duration of their playlist slot.
- If running headless (no desktop), tkinter requires a running X/Wayland display — WindowBox will not work without one.
