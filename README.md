# starship-salah

A [Starship](https://starship.rs) prompt block that labels the clock with the current prayer period.

```
󰀵 user ~   v3.9.6  󰖕 Asr 16:36  ❯
```

| Period | Shown from → until |
|---|---|
| 󰓎 Tahajjud | last third of the night → Fajr (Isha can still be prayed) |
| 󰖜 Fajr | Fajr → sunrise |
| 󰖙 Shuruq | sunrise → Dhuhr (muted block: not a prayer time) |
| 󰖨 Dhuhr / Jumu'ah | Dhuhr → Asr (Jumu'ah on Fridays) |
| 󰖕 Asr | Asr → Maghrib |
| 󰖛 Maghrib | Maghrib → Isha |
| 󰖔 Isha | Isha → middle of the night |
| 󰖔 Isha (late) | middle of the night → last third (muted block) |

The night runs from Maghrib to Fajr. In the last 20 minutes before the next salah (or before sunrise, when
Fajr ends) the block shows a countdown instead, for example `󰖕 Asr in 15m 16:21`.

The prompt only redraws when you press Enter or a command finishes, so the countdown is as of the last prompt.

## How it works

`prayer_times.py` gets daily times from the [Aladhan API](https://aladhan.com/prayer-times-api) and caches
yesterday, today and tomorrow in `~/.cache/prayer-times/`. The prompt reads only the cache, so it never waits on
the network. A missing day is fetched in the background; until then the block shows a plain clock.

Starship runs two custom modules. Each prints nothing outside its own periods, so one block shows at a time:

- `salah`: the normal block
- `muted`: Shuruq and late Isha

## Requirements

- Starship
- Python 3 (standard library only)
- `curl`
- A font with Nerd Font icons (Ghostty includes them)

## Install

1. Link the script to where the Starship config expects it:

   ```sh
   mkdir -p ~/.config/starship
   ln -s "$PWD/prayer_times.py" ~/.config/starship/prayer_times.py
   ```

2. Copy the two `[custom.*]` sections from `starship.toml` into `~/.config/starship.toml`.

3. In the top-level `format` of `~/.config/starship.toml`, put `${custom.salah}${custom.muted}` where `$time` was.
   The block formats include their own separators, so remove the separators around `$time` too.

4. Fill the cache once: `python3 prayer_times.py fetch`

## Settings

Edit the constants at the top of `prayer_times.py`:

| Setting | Default |
|---|---|
| `LATITUDE`, `LONGITUDE`, `TIMEZONE` | Mississauga, ON (`America/Toronto`) |
| `METHOD` | `2` (ISNA). See Aladhan's [method list](https://aladhan.com/calculation-methods) |
| `SCHOOL` | `1` (Hanafi Asr). `0` is the standard (Shafi'i, Maliki, Hanbali) Asr |
| `TIME_FORMAT` | `%H:%M` |
| `COUNTDOWN_MINUTES` | `20` |

After you change the location or method, delete `~/.cache/prayer-times/` so the times are fetched again.

## License

[MIT](LICENSE)
