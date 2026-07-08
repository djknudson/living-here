# Living Here

A Home Assistant setup ("Living Here") whose first station is **fishbucket** — an
aquarium monitor for a backyard freshwater tub (goldfish). Prototype/testing.

## What runs where

```
  ESP32 (ESPHome)                          Pi 4 "fishbucket" (Camera Module 3)
  ├─ DS18B20 water temp → GPIO4 (D4)       └─ rpicam-vid → go2rtc → RTSP/WebRTC
  └─ TDS probe → GPIO34 (D34), 5V(VIN)            │
        │  Wi-Fi "<ssid>", encrypted API           │  RTSP
        └──────────────┐            ┌────────────┘
                       ▼            ▼
                Home Assistant (HAOS on Intel N97 — the hub)
                ├─ ESPHome integration → Water Temperature, Water TDS
                ├─ Generic Camera      → camera.fishbucket_camera
                └─ "Living Here" dashboard
```

## Machines
| Host | IP | What | Access |
|------|-----|------|--------|
| `homeassistant` | 10.0.10.90 | HAOS 2026.7.1 (N97, 16 GB) | `ssh homeassistant`, web `:8123` |
| `fishbucket` | 10.0.10.38 | Pi 4, Debian 13, Camera Module 3 | `ssh fishbucket` |
| `fishbucket-sensors` | DHCP (.67) | ESP32 (ESPHome), temp + TDS | HA native API + OTA |

## Repo layout
```
living-here/
├── CLAUDE.md                     # orientation for AI coding sessions
├── README.md                     # this file
├── docs/
│   ├── design/                   # design spec
│   └── research/                 # 2026 hardware research brief
├── fishbucket/                   # the aquarium station
│   ├── esp32/                    # ESPHome firmware (+ git-ignored secrets)
│   └── pi/                       # go2rtc camera streaming config + service
└── homeassistant/                # HA hub config
    ├── README.md                 # HA setup + gotchas
    └── dashboards/               # Living Here dashboard (YAML mode)
```

## Common tasks
- **Change ESP32 firmware:** edit `fishbucket/esp32/fishbucket-sensors.yaml`, then
  `cd fishbucket/esp32 && esphome run fishbucket-sensors.yaml --device fishbucket-sensors.local`
  (wireless OTA — no USB after the first flash).
- **Camera:** `ssh fishbucket 'sudo systemctl restart go2rtc'`; test at <http://10.0.10.38:1984>.
- **Dashboard:** edit `homeassistant/dashboards/living-here.yaml`, `scp` to
  `homeassistant:/config/dashboards/`, reload the browser tab.

See `CLAUDE.md` for deeper detail and gotchas.
