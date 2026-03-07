#!/usr/bin/env python3
"""
WindowBox - Calendar-aware image slideshow display.

Reads playlist.txt and displays images from the images/ subdirectory
according to scheduling rules (day of week, day of month, time of day).

Supports static .jpg/.png and animated .gif/.png (APNG).

Controls:
  q          - quit
  Ctrl+C     - quit (from SSH terminal)
"""

import sys
import glob
import logging
import signal
import datetime
import re
import tkinter as tk
from pathlib import Path

try:
    from PIL import Image, ImageTk
except ImportError:
    print("Pillow is required. Install with: pip install Pillow")
    sys.exit(1)

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("windowbox")

_media_handler = logging.FileHandler(Path(__file__).parent / "media.log")
_media_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
media_log = logging.getLogger("windowbox.media")
media_log.addHandler(_media_handler)
media_log.propagate = False

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
PLAYLIST_FILE = BASE_DIR / "playlist.txt"
PRIORITY_FILE = BASE_DIR / "priority.txt"

# Aspect correction for monitors that stretch their input signal.
# 1.0 = no correction (normal display).
# Example: monitor is physically 2560x1080 but Pi outputs 1920x1080 →
#   the monitor stretches by 2560/1920 = 4/3, so correct with 3/4.
# On a display rotated 90°, the monitor's horizontal stretch becomes vertical
#   in logical screen space, so the squish is applied to the height axis.
DISPLAY_SQUISH = 3/4
DISPLAY_SQUISH_AXIS = "height"  # "width" for landscape, "height" for 90°/270° rotation

# Maps lowercase day names to Python weekday numbers (Mon=0 .. Sun=6)
DAY_NAMES = {
    "mon": 0, "monday": 0,
    "tue": 1, "tuesday": 1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thursday": 3,
    "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}

# Maps ordinal words/abbreviations to occurrence numbers (last = -1)
ORDINALS = {
    "1st": 1, "first": 1,
    "2nd": 2, "second": 2,
    "3rd": 3, "third": 3,
    "4th": 4, "fourth": 4,
    "5th": 5, "fifth": 5,
    "last": -1,
}


# ---------------------------------------------------------------------------
# Scheduling helpers
# ---------------------------------------------------------------------------

def _make_day_checker(spec):
    """Return a callable(date) -> bool for a single day token.

    Supported tokens (case-insensitive):
      all / * / every           every day
      Mon .. Sun                every matching weekday
      first Mon .. last Fri     nth occurrence of weekday in month
      1 .. 31                   specific day of month number
    """
    spec = spec.strip().lower()

    if spec in ("all", "every", "*"):
        return lambda d: True

    parts = spec.split()
    if len(parts) == 2:
        ord_str, day_str = parts
        if ord_str in ORDINALS and day_str in DAY_NAMES:
            nth = ORDINALS[ord_str]
            target_wd = DAY_NAMES[day_str]

            def ordinal_check(d, wday=target_wd, n=nth):
                if d.weekday() != wday:
                    return False
                if n == -1:
                    # "last": next week falls in a different month
                    return (d + datetime.timedelta(days=7)).month != d.month
                # nth occurrence: count same-weekday days from month start to d
                count = 0
                cur = d.replace(day=1)
                while cur <= d:
                    if cur.weekday() == wday:
                        count += 1
                    cur += datetime.timedelta(days=1)
                return count == n

            return ordinal_check

    if spec in DAY_NAMES:
        target = DAY_NAMES[spec]
        return lambda d, t=target: d.weekday() == t

    try:
        day_num = int(spec)
        return lambda d, n=day_num: d.day == n
    except ValueError:
        pass

    log.warning("Unrecognised day spec '%s', will never match.", spec)
    return lambda d: False


def days_match(days_field, date):
    """Return True if any |-separated token in days_field matches date."""
    for token in days_field.split("|"):
        if _make_day_checker(token)(date):
            return True
    return False


def parse_timespan(ts):
    """Parse 'HH:MM-HH:MM' into (start_minutes, end_minutes).

    Returns (0, 1440) for 'all', '*', or empty string.
    """
    ts = ts.strip().lower()
    if not ts or ts in ("all", "*"):
        return (0, 1440)

    m = re.fullmatch(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", ts)
    if m:
        sh, sm, eh, em = (int(x) for x in m.groups())
        return (sh * 60 + sm, eh * 60 + em)

    log.warning("Unrecognised timespan '%s', defaulting to all day.", ts)
    return (0, 1440)


def time_in_span(now, start_min, end_min):
    """Return True if now falls within [start_min, end_min] (minutes since midnight)."""
    cur = now.hour * 60 + now.minute
    if start_min <= end_min:
        return start_min <= cur <= end_min
    # Spans midnight
    return cur >= start_min or cur <= end_min


# ---------------------------------------------------------------------------
# Playlist parsing
# ---------------------------------------------------------------------------

def parse_playlist(filepath):
    """Parse playlist.txt; return list of entry dicts."""
    entries = []
    try:
        with open(filepath, "r") as fh:
            for lineno, raw in enumerate(fh, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 4:
                    log.warning("Playlist line %d has fewer than 4 fields, skipping.", lineno)
                    continue
                try:
                    duration = float(parts[0])
                    days = parts[1]
                    timespan = parts[2]
                    filename = ",".join(parts[3:]).strip()  # filename may contain commas
                    start_min, end_min = parse_timespan(timespan)
                    entries.append({
                        "duration": max(duration, 0.1),
                        "days": days,
                        "start_min": start_min,
                        "end_min": end_min,
                        "filename": filename,
                    })
                except ValueError as exc:
                    log.warning("Playlist line %d parse error (%s), skipping.", lineno, exc)
    except FileNotFoundError:
        log.warning("Playlist not found: %s", filepath)
    return entries


def active_entries(entries, now, images_dir):
    """Return entries whose day/time criteria match now and whose file exists."""
    today = now.date()
    result = []
    for e in entries:
        if not days_match(e["days"], today):
            continue
        if not time_in_span(now, e["start_min"], e["end_min"]):
            continue
        fp = images_dir / e["filename"]
        if not fp.exists():
            log.warning("Image not found: %s", fp)
            continue
        result.append({**e, "filepath": fp})
    return result


# ---------------------------------------------------------------------------
# Image loading
# ---------------------------------------------------------------------------

def load_frames(filepath, screen_w, screen_h):
    """Load an image file and return (frames, delays_ms).

    frames   – list of ImageTk.PhotoImage (1 element for static images)
    delays   – list of per-frame durations in ms
    """
    img = Image.open(filepath)
    suffix = filepath.suffix.lower()
    raw_frames = []
    delays = []

    if suffix in (".gif", ".png"):
        n = getattr(img, "n_frames", 1)
        if n > 1:
            for i in range(n):
                img.seek(i)
                raw_frames.append(img.copy().convert("RGBA"))
                delays.append(max(img.info.get("duration", 100), 20))
        else:
            raw_frames = [img.convert("RGBA")]
            delays = [None]  # static
    else:
        raw_frames = [img.convert("RGBA")]
        delays = [None]

    tk_frames = [ImageTk.PhotoImage(_fit(f, screen_w, screen_h)) for f in raw_frames]
    return tk_frames, delays


def _fit(img, screen_w, screen_h):
    """Scale img to fit screen while preserving aspect ratio.

    If DISPLAY_SQUISH != 1.0, the image is pre-squished along DISPLAY_SQUISH_AXIS
    to compensate for a monitor that stretches its input signal.
    Use "width" for landscape orientation, "height" for 90°/270° rotation.
    """
    iw, ih = img.size
    if DISPLAY_SQUISH_AXIS == "height":
        effective_h = screen_h / DISPLAY_SQUISH
        scale = min(screen_w / iw, effective_h / ih)
        fitted_w = max(1, int(iw * scale))
        fitted_h = max(1, int(ih * scale * DISPLAY_SQUISH))
    else:
        effective_w = screen_w / DISPLAY_SQUISH
        scale = min(effective_w / iw, screen_h / ih)
        fitted_w = max(1, int(iw * scale * DISPLAY_SQUISH))
        fitted_h = max(1, int(ih * scale))
    return img.resize((fitted_w, fitted_h), Image.LANCZOS)


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class WindowBox:
    # How often (ms) to re-check the playlist when nothing is scheduled
    IDLE_CHECK_MS = 30_000

    def __init__(self, root):
        self.root = root
        self.root.title("WindowBox")
        self.root.configure(bg="black")
        self.root.overrideredirect(True)
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{sw}x{sh}+0+0")
        self.root.bind("q", lambda _: self.root.destroy())

        self.label = tk.Label(self.root, bg="black", bd=0)
        self.label.place(relx=0.5, rely=0.5, anchor="center")

        self._cursor_visible = True
        self._poll_mouse()

        self._playlist_mtime = None
        self._priority_mtime = None
        self._anim_job = None
        self._switch_job = None
        self._frames = []
        self._delays = []
        self._frame_idx = 0
        self._entries = []
        self._entry_idx = 0
        self._priority_entries = []
        self._priority_idx = 0
        self._showing_priority = False

        self._load_and_show()

    # ------------------------------------------------------------------
    # Core display loop
    # ------------------------------------------------------------------

    def _cancel_jobs(self):
        for attr in ("_anim_job", "_switch_job"):
            job = getattr(self, attr)
            if job is not None:
                self.root.after_cancel(job)
                setattr(self, attr, None)

    def _load_and_show(self):
        """Reload both playlists and start cycling; retry later if nothing active."""
        self._cancel_jobs()
        now = datetime.datetime.now()

        pm = PLAYLIST_FILE.stat().st_mtime if PLAYLIST_FILE.exists() else None
        if self._playlist_mtime is not None and pm != self._playlist_mtime:
            media_log.info("playlist.txt changed")
        self._playlist_mtime = pm

        qm = PRIORITY_FILE.stat().st_mtime if PRIORITY_FILE.exists() else None
        if self._priority_mtime is not None and qm != self._priority_mtime:
            media_log.info("priority.txt changed")
        self._priority_mtime = qm

        playlist = parse_playlist(PLAYLIST_FILE)
        self._entries = active_entries(playlist, now, IMAGES_DIR)

        priority = parse_playlist(PRIORITY_FILE)
        self._priority_entries = active_entries(priority, now, IMAGES_DIR)
        self._priority_idx = 0
        self._showing_priority = False

        if not self._entries:
            log.info("No images scheduled, retrying in %ds", self.IDLE_CHECK_MS // 1000)
            self._show_message("No images scheduled")
            self._switch_job = self.root.after(self.IDLE_CHECK_MS, self._load_and_show)
            return

        self._entry_idx = 0
        self._show_entry()

    def _show_entry(self):
        """Display the playlist entry at _entry_idx."""
        self._cancel_jobs()
        self._showing_priority = False
        self._display_entry(self._entries[self._entry_idx])

    def _display_entry(self, entry):
        """Load and display a single entry dict."""
        duration_ms = int(entry["duration"] * 1000)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        source = "priority" if self._showing_priority else "playlist"
        media_log.info("Showing [%s] %s (%.0fs)", source, entry["filename"], entry["duration"])
        try:
            self._frames, self._delays = load_frames(entry["filepath"], sw, sh)
        except Exception as exc:
            log.error("Error loading %s: %s", entry["filepath"], exc)
            self._advance()
            return

        self._frame_idx = 0
        if len(self._frames) > 1:
            self._animate()
        else:
            self.label.configure(image=self._frames[0])

        self._switch_job = self.root.after(duration_ms, self._advance)

    def _animate(self):
        """Step one animation frame forward."""
        self.label.configure(image=self._frames[self._frame_idx])
        delay = self._delays[self._frame_idx]
        self._frame_idx = (self._frame_idx + 1) % len(self._frames)
        self._anim_job = self.root.after(delay, self._animate)

    def _advance(self):
        """After each playlist item, show the next eligible priority item (if any),
        then move on to the next playlist item."""
        self._cancel_jobs()
        now = datetime.datetime.now()

        # Re-filter playlist by current time
        self._entries = [
            e for e in self._entries
            if time_in_span(now, e["start_min"], e["end_min"])
        ]
        if not self._entries:
            self._load_and_show()
            return

        if not self._showing_priority:
            # Just finished a playlist item — insert a priority item if available
            self._priority_entries = [
                e for e in self._priority_entries
                if time_in_span(now, e["start_min"], e["end_min"])
            ]
            if self._priority_entries:
                self._priority_idx = self._priority_idx % len(self._priority_entries)
                entry = self._priority_entries[self._priority_idx]
                self._priority_idx = (self._priority_idx + 1) % len(self._priority_entries)
                self._showing_priority = True
                self._display_entry(entry)
                return

        # Advance to next playlist item
        self._entry_idx = (self._entry_idx + 1) % len(self._entries)
        self._show_entry()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _poll_mouse(self):
        """Show or hide the cursor depending on whether a mouse is connected."""
        has_mouse = bool(glob.glob("/dev/input/mouse*"))
        if has_mouse and not self._cursor_visible:
            self.root.configure(cursor="")
            self._cursor_visible = True
        elif not has_mouse and self._cursor_visible:
            self.root.configure(cursor="none")
            self._cursor_visible = False
        self.root.after(3000, self._poll_mouse)

    def _show_message(self, msg):
        self.label.configure(image="", text=msg, fg="gray", font=("Helvetica", 24))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _write_sample_playlist():
    with open(PLAYLIST_FILE, "w") as fh:
        fh.write(
            "# WindowBox Playlist\n"
            "# Format:  duration_seconds, days, timespan, filename\n"
            "#\n"
            "# duration  seconds the image is shown\n"
            "# days      all | Mon | first Tue | last Fri | Mon|Wed|Fri  (case-insensitive)\n"
            "# timespan  HH:MM-HH:MM (24-hour) or  all\n"
            "# filename  file in the images/ subdirectory\n"
            "#\n"
            "# Examples (uncomment and add matching image files to images/):\n"
            "# 10, all, all, sample.jpg\n"
            "# 30, Mon|Wed|Fri, 09:00-17:00, weekdays.png\n"
            "# 20, first Mon, 00:00-23:59, first_monday.gif\n"
            "# 15, last Fri, 17:00-20:00, friday_evening.jpg\n"
            "# 60, Sat|Sun, 08:00-12:00, weekend_morning.png\n"
        )
    print(f"Created sample playlist: {PLAYLIST_FILE}")


def main():
    IMAGES_DIR.mkdir(exist_ok=True)

    if not PLAYLIST_FILE.exists():
        _write_sample_playlist()
        print(f"Add image files to: {IMAGES_DIR}")
        print("Then edit playlist.txt and restart.")
        return

    log.info("WindowBox started")
    root = tk.Tk()
    app = WindowBox(root)

    _reload_flag = [False]

    def _on_usr1(*_):
        _reload_flag[0] = True

    def _poll_reload():
        if _reload_flag[0]:
            _reload_flag[0] = False
            log.info("Reload signal received")
            app._load_and_show()
        root.after(500, _poll_reload)

    signal.signal(signal.SIGINT, lambda *_: root.destroy())
    signal.signal(signal.SIGUSR1, _on_usr1)
    root.after(500, _poll_reload)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        root.destroy()
    log.info("WindowBox stopped")


if __name__ == "__main__":
    main()
