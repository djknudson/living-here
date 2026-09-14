# Living Here: Home Assistant monitoring for a goldfish tub

An ESP32 sensor node, a Raspberry Pi camera and a Pi Zero e-ink panel on a goldfish tub, wired
into Home Assistant on a mini PC. I'm building it one station at a time, and
**fishbucket** is the first.

## Status

- **Live:** water temperature, TDS (dissolved solids), air temperature and air pressure
  report to Home Assistant every 10 seconds. The e-ink panel redraws every 5 minutes.
- **Camera:** the Pi 4 streaming setup works. The camera is switched off for now.
- **pH:** the firmware and the Home Assistant dashboard have pH support, but no probe has
  been wired in or calibrated. Ignore any pH value. The firmware notes power the pH board
  from 5 V; measure its signal output before connecting it to the ESP32, whose inputs are 3.3 V.
- **No alerts.** Nothing notifies anyone when a reading goes out of range.
- **Versions:** the firmware was last built with ESPHome 2026.6.3, and the hub ran Home
  Assistant OS 2026.7.1 when these notes were written.

## What runs where

```
  ESP32 (ESPHome)                          Pi 4 "fishbucket" (Camera Module 3)
  ├─ DS18B20 water temp → GPIO4 (D4)       └─ rpicam-vid → go2rtc → RTSP/WebRTC
  ├─ TDS probe → GPIO34 (D34), 3.3V               │
  └─ BMP280 air temp/pressure → I²C D21/D22       │
        │  Wi-Fi, encrypted ESPHome API            │  RTSP
        └──────────────┐            ┌────────────┘
                       ▼            ▼
                Home Assistant (HAOS on Intel N97 — the hub)
                ├─ ESPHome integration → water temp, TDS, air temp/pressure
                ├─ Generic Camera      → camera.fishbucket_camera
                ├─ "Living Here" dashboard
                └──REST API──> Pi Zero "sensordisplay" (2.13″ e-ink stats panel)
```

| Device | Job |
|--------|-----|
| ESP32 dev board running ESPHome | Takes the four readings; firmware updates go over Wi-Fi after the first USB flash |
| Raspberry Pi 4 + Camera Module 3 | Streams the tub through go2rtc using the Pi's hardware H.264 encoder |
| Intel N97 mini PC, Home Assistant OS | The hub: collects readings, pulls the camera stream, serves the dashboard |
| Raspberry Pi Zero W + 2.13″ e-ink HAT | Shows the four readings, pulled from Home Assistant's REST API |

## Repo layout

The Pi, Home Assistant and e-ink folders each have their own README with setup details.

```
living-here/
├── CLAUDE.md                     # working notes: machine access, wiring, fixes for problems I hit
├── README.md                     # this file
├── docs/
│   ├── design/                   # original July design spec (the code wins where they differ)
│   └── research/                 # July hardware research brief (same caveat)
├── fishbucket/                   # the goldfish-tub station
│   ├── esp32/                    # ESPHome firmware + secrets template
│   └── pi/                       # go2rtc camera streaming config + systemd service
├── homeassistant/                # hub setup notes
│   └── dashboards/               # the Living Here dashboard (YAML mode)
└── sensordisplay/                # Pi Zero e-ink panel: render script, systemd timer, installer
```

## Setting it up

1. **Sensor node.** Install ESPHome, copy `fishbucket/esp32/secrets.example.yaml` to
   `secrets.yaml` (git-ignored) and fill it in. The template shows the `openssl` command for
   the API key, the OTA password and the fallback-AP password. Flash once over USB with
   `esphome run fishbucket/esp32/fishbucket-sensors.yaml`; later flashes go over Wi-Fi.
2. **Home Assistant.** Add the ESPHome device when Home Assistant discovers it (it asks for
   the API encryption key from `secrets.yaml`), then load
   `homeassistant/dashboards/living-here.yaml`. Details in `homeassistant/README.md`.
3. **Camera.** Install go2rtc and its service on the Pi 4 following `fishbucket/pi/README.md`,
   then add `rtsp://<pi-address>:8554/aquarium` to Home Assistant as a Generic Camera.
4. **E-ink panel.** Copy `sensordisplay/` to the Pi Zero, run `setup.sh` there, and save a
   Home Assistant long-lived access token to `~/display/ha_token`. Details in
   `sensordisplay/README.md`.

The files carry my LAN addresses and Linux usernames. To run this on your network, change
the Home Assistant URL in `sensordisplay/dashboard.py`, the WebRTC address in
`fishbucket/pi/go2rtc.yaml`, and the `fishbucket` / `sensordisplay` users in the systemd
units and `sensordisplay/setup.sh`.

## Gotchas

- On the ESP32, the ADC2 pins stop reading once Wi-Fi is on, so the analog inputs use ADC1
  pins: GPIO34 for TDS and GPIO35 for the not-yet-wired pH probe.
- The e-ink panel once froze after a reboot because its systemd timer never re-armed. It now
  runs on a wall-clock `OnCalendar` schedule; the reason is written in
  `sensordisplay/sensordashboard.timer`.
- Home Assistant keys an ESPHome device to its MAC address, so a replacement ESP32 shows up
  as a new device. Current Home Assistant can migrate the old entities and history to a
  replacement with the same device name; `CLAUDE.md` records the manual fix I used before that.

## Open items

- Wire and calibrate the pH probe, after measuring its output voltage.
- Add alerts for readings that go out of range.

I write up what breaks in my builds and how I fix it at [davidjknudson.com](https://www.davidjknudson.com).
