#!/usr/bin/env python3
"""
WindowBox - Calendar-aware image slideshow display.

Reads playlist.txt and displays images from the images/ subdirectory
according to scheduling rules (day of week, day of month, time of day).

Supports static .jpg/.png and animated .gif/.png (APNG).

Controls:
  Escape  - exit fullscreen
  f       - enter fullscreen
  q       - quit
"""

import sys
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

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
PLAYLIST_FILE = BASE_DIR / "playlist.txt"

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

    print(f"Warning: unrecognised day spec '{spec}', will never match.")
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

    print(f"Warning: unrecognised timespan '{ts}', defaulting to all day.")
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
                    print(f"Warning: playlist line {lineno} has fewer than 4 fields, skipping.")
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
                    print(f"Warning: playlist line {lineno} parse error ({exc}), skipping.")
    except FileNotFoundError:
        print(f"Playlist not found: {filepath}")
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
            print(f"Warning: image not found: {fp}")
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
    """Scale img to fit screen while preserving aspect ratio."""
    iw, ih = img.size
    scale = min(screen_w / iw, screen_h / ih)
    return img.resize((max(1, int(iw * scale)), max(1, int(ih * scale))), Image.LANCZOS)


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
        self.root.update()
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda _: self.root.attributes("-fullscreen", False))
        self.root.bind("f", lambda _: self.root.attributes("-fullscreen", True))
        self.root.bind("q", lambda _: self.root.destroy())

        self.label = tk.Label(self.root, bg="black", bd=0)
        self.label.place(relx=0.5, rely=0.5, anchor="center")

        self._anim_job = None
        self._switch_job = None
        self._frames = []
        self._delays = []
        self._frame_idx = 0
        self._entries = []
        self._entry_idx = 0

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
        """Reload the playlist and start cycling; retry later if nothing active."""
        self._cancel_jobs()
        playlist = parse_playlist(PLAYLIST_FILE)
        self._entries = active_entries(playlist, datetime.datetime.now(), IMAGES_DIR)

        if not self._entries:
            self._show_message("No images scheduled")
            self._switch_job = self.root.after(self.IDLE_CHECK_MS, self._load_and_show)
            return

        self._entry_idx = 0
        self._show_entry()

    def _show_entry(self):
        """Display the entry at _entry_idx."""
        self._cancel_jobs()
        entry = self._entries[self._entry_idx]
        duration_ms = int(entry["duration"] * 1000)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        try:
            self._frames, self._delays = load_frames(entry["filepath"], sw, sh)
        except Exception as exc:
            print(f"Error loading {entry['filepath']}: {exc}")
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
        """Move to the next active entry, re-filtering by current time."""
        self._cancel_jobs()
        now = datetime.datetime.now()
        # Drop entries whose time window has now expired
        self._entries = [
            e for e in self._entries
            if time_in_span(now, e["start_min"], e["end_min"])
        ]
        if not self._entries:
            self._load_and_show()
            return
        self._entry_idx = (self._entry_idx + 1) % len(self._entries)
        self._show_entry()

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

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

    root = tk.Tk()
    WindowBox(root)
    signal.signal(signal.SIGINT, lambda *_: root.destroy())
    try:
        root.mainloop()
    except KeyboardInterrupt:
        root.destroy()


if __name__ == "__main__":
    main()
