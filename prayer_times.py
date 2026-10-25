#!/usr/bin/env python3
"""Starship custom module: the current time, labelled with the current prayer period.

Usage: prayer_times.py salah   -> prints e.g. "󰖜 Fajr 06:31" (empty in muted periods)
       prayer_times.py muted   -> prints e.g. "󰖙 Shuruq 08:02" (empty otherwise)
       prayer_times.py fetch   -> download yesterday/today/tomorrow into the cache

Starship shows one of the two prompt blocks, so the muted periods (Shuruq, and
Isha after the middle of the night) get their own style. Isha stays valid until
Fajr, so seeing Tahajjud also means Isha can still be prayed. In the last
COUNTDOWN_MINUTES before the next salah (or sunrise, when Fajr ends) the block
shows a countdown instead, e.g. "󰖕 Asr in 15m 16:21".
Times come from api.aladhan.com and are cached per day, so the prompt never waits
on the network: a missing day is fetched in the background.
"""
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta

LATITUDE = 43.5890   # Mississauga, ON
LONGITUDE = -79.6441
TIMEZONE = "America/Toronto"
METHOD = 2           # ISNA
SCHOOL = 1           # Hanafi Asr
TIME_FORMAT = "%H:%M"
COUNTDOWN_MINUTES = 20  # show "Asr in 15m" this close to the next salah

CACHE_DIR = os.path.expanduser("~/.cache/prayer-times")

ICONS = {
    "Tahajjud": "\U000F04CE",  # star
    "Fajr": "\U000F059C",      # sunrise
    "Shuruq": "\U000F0599",    # sun
    "Dhuhr": "\U000F05A8",     # bright sun
    "Jumu'ah": "\U000F05A8",
    "Asr": "\U000F0595",       # partly cloudy
    "Maghrib": "\U000F059B",   # sunset
    "Isha": "\U000F0594",      # night
    "Isha (late)": "\U000F0594",
}

MUTED = {"Shuruq", "Isha (late)"}


def cache_path(day):
    return os.path.join(CACHE_DIR, f"{day.isoformat()}.json")


def fetch(day):
    url = (
        f"https://api.aladhan.com/v1/timings/{day.strftime('%d-%m-%Y')}"
        f"?latitude={LATITUDE}&longitude={LONGITUDE}&method={METHOD}"
        f"&school={SCHOOL}&timezonestring={TIMEZONE}"
    )
    result = subprocess.run(
        ["curl", "-sf", "--max-time", "10", url], capture_output=True, text=True
    )
    if result.returncode != 0:
        return
    timings = json.loads(result.stdout)["data"]["timings"]
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = cache_path(day) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(timings, f)
    os.replace(tmp, cache_path(day))


def fetch_missing(today):
    for offset in (-1, 0, 1):
        day = today + timedelta(days=offset)
        if not os.path.exists(cache_path(day)):
            fetch(day)
    # Drop cache files older than a week.
    for name in os.listdir(CACHE_DIR):
        try:
            if date.fromisoformat(name[:10]) < today - timedelta(days=7):
                os.remove(os.path.join(CACHE_DIR, name))
        except ValueError:
            pass


def load(day):
    """Return {prayer: datetime} for a day, or None if it is not cached yet."""
    try:
        with open(cache_path(day)) as f:
            timings = json.load(f)
    except (OSError, ValueError):
        return None
    times = {}
    for name in ("Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"):
        hour, minute = timings[name].split()[0].split(":")
        times[name] = datetime(day.year, day.month, day.day, int(hour), int(minute))
    return times


def night_period(now, maghrib, next_fajr):
    """Isha until the middle of the night, then late Isha, then Tahajjud in the
    last third. The night runs from Maghrib to Fajr."""
    night = next_fajr - maghrib
    if now >= next_fajr - night / 3:
        return "Tahajjud"
    if now >= maghrib + night / 2:
        return "Isha (late)"
    return "Isha"


def current_period(now):
    """Return (period, (next_name, next_time)). The next event is the next salah,
    or sunrise during Fajr; it is None when unknown."""
    today = now.date()
    t = load(today)
    if t is None:
        return None, None
    dhuhr = "Jumu'ah" if now.weekday() == 4 else "Dhuhr"

    if now < t["Fajr"]:
        yesterday = load(today - timedelta(days=1))
        if yesterday is None:
            return None, None
        return night_period(now, yesterday["Maghrib"], t["Fajr"]), ("Fajr", t["Fajr"])
    if now >= t["Isha"]:
        tomorrow = load(today + timedelta(days=1))
        if tomorrow is None:
            return "Isha", None
        return night_period(now, t["Maghrib"], tomorrow["Fajr"]), ("Fajr", tomorrow["Fajr"])
    if now >= t["Maghrib"]:
        return "Maghrib", ("Isha", t["Isha"])
    if now >= t["Asr"]:
        return "Asr", ("Maghrib", t["Maghrib"])
    if now >= t["Dhuhr"]:
        return dhuhr, ("Asr", t["Asr"])
    if now >= t["Sunrise"]:
        return "Shuruq", (dhuhr, t["Dhuhr"])
    return "Fajr", ("Shuruq", t["Sunrise"])


def label(now):
    """Return (text, muted) for the prompt block, or (None, False) without data."""
    period, upcoming = current_period(now)
    if period is None:
        return None, False
    if upcoming:
        name, at = upcoming
        minutes = -(-(at - now).total_seconds() // 60)  # round up
        if minutes <= COUNTDOWN_MINUTES:
            return f"{ICONS[name]} {name} in {int(minutes)}m", False
    return f"{ICONS[period]} {period}", period in MUTED


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "salah"
    now = datetime.now()

    if mode == "fetch":
        fetch_missing(now.date())
        return

    text, muted = label(now)
    needed = [now.date() + timedelta(days=o) for o in (-1, 0, 1)]
    if any(not os.path.exists(cache_path(d)) for d in needed):
        subprocess.Popen(
            [sys.executable, "-I", os.path.abspath(__file__), "fetch"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )

    clock = now.strftime(TIME_FORMAT)
    if mode == "muted":
        if muted:
            print(f"{text} {clock}")
    elif not muted:
        # No cached times yet: fall back to a plain clock.
        print(f"{text or chr(0xF017)} {clock}")


if __name__ == "__main__":
    main()
