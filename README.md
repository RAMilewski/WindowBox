# Installing windowbox on Raspberry Pi OS (Trixie)

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
sudo apt install -y python3-tk python3-pil python3-pil.imagetk python3-full git wlr-randr
```

---

## 3. Clone the repository

```bash
git clone https://github.com/RAMilewski/WindowBox.git ~/windowbox
```

---

## 4. Install Python dependencies

Trixie restricts system-wide `pip` installs. Create a virtual environment that
shares the system packages (including the Pillow installed in step 2):

```bash
cd ~/windowbox
python3 -m venv --system-site-packages venv
```

---

## 5. Add images and edit the playlists

Copy your image files into the `images/` subdirectory:

```bash
cp /path/to/your/images/*.jpg ~/windowbox/images/
```

Edit the main playlist:

```bash
nano ~/windowbox/playlist.txt
```

**Priority playlist** (`priority.txt`) — optional. Items here are shown
between each regular playlist item, cycling through all eligible entries.
If no priority items are eligible the regular playlist continues
uninterrupted. The format is identical to `playlist.txt`:

```bash
nano ~/windowbox/priority.txt
```

---

## 6. Deploy a pre-built configuration

If you have a configuration folder (containing `playlist.txt`, `priority.txt`,
`windowbox.cfg`, and an `images/` subdirectory), use `deploy.sh` to install it:

```bash
~/windowbox/deploy.sh <config-folder>
```

The folder path is relative to the `windowbox` directory. For example:

```bash
~/windowbox/deploy.sh SatMKT
```

This copies all four items into `~/windowbox`, then signals windowbox to reload
its playlists immediately. If windowbox is not running it prints a reminder to
start it with `startbox.sh`.

Make the script executable first if needed:

```bash
chmod +x ~/windowbox/deploy.sh
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

## 7. Run it

From a terminal on the Pi desktop:

```bash
cd ~/windowbox
./startbox.sh
```

Make the scripts executable first if needed:

```bash
chmod +x ~/windowbox/startbox.sh ~/windowbox/killbox.sh ~/windowbox/reload.sh ~/windowbox/deploy.sh
```

**To run detached** (survives closing the terminal):

```bash
~/windowbox/startbox.sh -b
```

Output is logged to `~/windowbox/windowbox.log`. Playlist and media activity (which image is showing, file changes) is logged separately to `~/windowbox/media.log`. To watch them live:

```bash
tail -f ~/windowbox/windowbox.log
tail -f ~/windowbox/media.log
```

From an SSH session (to display on the Pi screen):

```bash
cd ~/windowbox
source venv/bin/activate
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 python3 windowbox.py
```

**To stop:** press `q` at the Pi keyboard, `Ctrl+C` in the terminal, or:

```bash
~/windowbox/killbox.sh
```

---

## 8. Reload playlists without restarting

After editing `playlist.txt` or `priority.txt`, or adding new images,
run the reload script — no restart needed:

```bash
~/windowbox/reload.sh
```

Make it executable first if needed:

```bash
chmod +x ~/windowbox/reload.sh
```

This pulls the latest changes from GitHub and signals windowbox to reload
both playlists immediately.

To reload without pulling from GitHub (e.g. after editing files directly
on the Pi):

```bash
pkill -USR1 -f windowbox.py
```

---

## 9. Auto-reload on a schedule

To pull updates from GitHub and reload windowbox automatically once an hour,
add a cron job:

```bash
crontab -e
```

Add this line:

```
0 * * * * /home/ram/windowbox/reload.sh
```

> Replace `/home/ram` with your actual home directory.

Verify it was saved:

```bash
crontab -l
```

---

## 10. Auto-start on boot

To launch windowbox automatically when the Pi boots into its desktop,
create an XDG autostart entry:

```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/windowbox.desktop
```

Paste this content:

```ini
[Desktop Entry]
Type=Application
Name=windowbox
Exec=/home/ram/windowbox/startbox.sh
X-GNOME-Autostart-enabled=true
```

> Replace `/home/ram` with your actual home directory (check with `echo $HOME`).

Reboot to activate:

```bash
sudo reboot
```

---

## Display configuration

All display settings live in `windowbox.cfg` in the project directory.
`startbox.sh` reads this file on every launch (including at boot) and applies
the rotation via `wlr-randr` before starting windowbox. The rotation is also
reapplied when windowbox exits, since the compositor resets it when XWayland closes.

```bash
nano ~/windowbox/windowbox.cfg
```

| Field | Description |
|---|---|
| `output` | wlr-randr output name — run `wlr-randr` to find yours (e.g. `HDMI-A-1`) |
| `rotation` | Display rotation: `normal`, `90`, `180`, `270` |
| `resolution` | Logical resolution after rotation (`WxH`) — for reference only |
| `squish` | Aspect correction factor (`1.0` = no correction) |
| `squish_axis` | Axis to squish: `width` (landscape) or `height` (90°/270°) |

To find your output name:

```bash
wlr-randr
```

Look for a line like `HDMI-A-1` or `DSI-1` and set `output` accordingly.

### Aspect ratio correction

Some monitors (such as LG HDR WFHD ultrawide panels) have a native resolution
of 2560×1080 but accept a 1920×1080 signal and stretch it horizontally to fill
the panel. This makes images look distorted.

`squish` corrects for this: `Pi_output_dimension ÷ panel_native_dimension`.
For the example above: `1920 ÷ 2560 = 0.75`.

When the display is rotated 90° or 270°, the stretch maps to the vertical axis
in logical screen space, so use `squish_axis = height`. For unrotated landscape
use `squish_axis = width`. Set `squish = 1.0` for a standard monitor.

Your original image files are never modified — correction is applied at display time.

After editing `windowbox.cfg`, restart windowbox for the display settings to take effect:

```bash
~/windowbox/killbox.sh
~/windowbox/startbox.sh -b
```

---

## Tips

- Press `q` at the Pi keyboard to quit, or run `~/windowbox/killbox.sh` from any terminal.
- `~/windowbox/reload.sh` pulls from GitHub and reloads playlists without restarting.
- `~/windowbox/startbox.sh -b` runs windowbox detached from the terminal; general logs go to `windowbox.log`, media activity to `media.log`.
- `~/windowbox/deploy.sh <folder>` installs a pre-built configuration (playlists, images, and `windowbox.cfg`) from a named subfolder and reloads immediately.
- Edit `windowbox.cfg` to change display rotation or aspect correction — no code editing needed.
- `git stash` before `git pull` if you have local changes to playlist files; `git stash pop` to restore them after.
- Animated GIFs and APNGs are supported and loop for the duration of their playlist slot.
- If running headless (no desktop), tkinter requires a running X/Wayland display — windowbox will not work without one.
- Run `./make_pdf.sh` (on the Mac) to regenerate `README.pdf` from `README.md`.
