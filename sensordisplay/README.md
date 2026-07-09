# sensordisplay — e-ink sensor panel

A **Raspberry Pi Zero W** (`sensordisplay`, 10.0.10.19, Raspbian trixie 32-bit / armv6)
with a **LAFVIN / Waveshare 2.13″ e-Paper HAT** (250×122 mono, controller SSD1680 =
Waveshare "V4"). It shows a tiny always-on dashboard of the four fishbucket sensors,
pulled from Home Assistant.

## What it shows
Inverted "FISHBUCKET" header + a 2×2 grid of Material-Design-Icon tiles:

| Water Temp (°F) | TDS (ppm) |
|---|---|
| **Air Temp (°F)** | **Pressure (inHg)** |

…plus a footer with the last-update time + a wifi glyph. Values are read from HA every
refresh; the e-ink does a full refresh **every 5 minutes** (systemd timer).

## How it works
```
HA REST API  ──(Bearer token)──>  dashboard.py (Pillow render)  ──SPI──>  2.13" e-Paper
```
- `dashboard.py` — fetches the 4 sensor states from HA, renders a 250×122 1-bit image
  with Pillow (DejaVu for text, the MDI webfont for icons), and pushes it to the panel
  via the Waveshare `epd2in13_V4` driver. Auto-fits value fonts so long values (e.g.
  `29.86 inHg`) stay clear of the panel's right edge.
- `sensordashboard.service` (oneshot) + `sensordashboard.timer` (every 5 min) — the
  refresh loop. E-ink must not full-refresh faster than ~3 min, so 5 min is the cadence.

## Key facts / trixie gotchas
- **Driver backend:** on Raspberry Pi OS trixie the Waveshare lib uses **gpiozero + lgpio
  + spidev** (the old RPi.GPIO sysfs path is gone). All from apt — no venv/pip needed.
- **Panel version:** try `epd2in13_V4` first (SSD1680); fall back V4→V3→V2. Ours is V4.
- **Icons:** Material Design Icons webfont rendered as glyphs with `ImageFont.truetype`
  (crisp pure-black — ideal for 1-bit e-ink). Pinned to `@mdi/font@7.4.47`. Codepoints
  used: thermometer-water `F1A80`, water-percent `F058E`, thermometer `F050F`,
  gauge `F029A`, fish `F023A`, update `F06B0`, wifi `F05A9`.
- **Physical right edge** clips a few px before 250 — values are capped to 78px width.
- **SPI** enabled via `raspi-config nonint do_spi 0` (config at `/boot/firmware/config.txt`),
  needs a reboot. If you ever hit `lgpio.error: 'GPIO busy'`, add `dtoverlay=spi0-0cs`.

## Install / redeploy
```bash
# copy this folder to the Pi, then on the Pi:
bash setup.sh
```
The script enables SPI, installs apt deps, fetches the Waveshare driver + MDI font,
installs `dashboard.py` and the systemd units, and enables the timer.

### The HA token (not in git)
`dashboard.py` reads a Home Assistant long-lived token from `~/display/ha_token`
(mode 0600). Create one in HA (**Profile → Security → Long-lived access tokens**) and
install it without it touching your shell history / this repo:
```bash
# with the "Copy" button clicked on HA's token dialog:
pbpaste | ssh sensordisplay 'umask 077; cat > ~/display/ha_token'
```

## Operate
```bash
sudo systemctl start sensordashboard.service   # refresh now
journalctl -u sensordashboard.service -n 20    # logs
systemctl list-timers sensordashboard.timer    # next refresh
python3 ~/display/dashboard.py sample          # render sample data (no HA)
```

## Files
- `dashboard.py` — render + fetch (deployed to `~/display/dashboard.py`)
- `sensordashboard.service` / `.timer` — deployed to `/etc/systemd/system/`
- `setup.sh` — installer
- (on the Pi only, git-ignored: `~/display/ha_token`, `waveshare_epd/`, the MDI font)
