# Home Assistant — Living Here hub

Home Assistant OS on an Intel N97 mini PC (16 GB). Host `homeassistant`
(10.0.10.90), web UI on `:8123`, HAOS Core 2026.7.1 (amd64).

## Access
- `ssh homeassistant` → root shell in the **Terminal & SSH** add-on (`core_ssh`),
  key-only, port 22, start-on-boot. Lands in `/config` with the `ha` CLI.
- Web UI: <http://10.0.10.90:8123> (user `<ha-user>`).

## What's configured here
| Piece | Detail |
|---|---|
| **Terminal & SSH** add-on | key-only SSH; our public key in its `authorized_keys` |
| **ESPHome** integration (built-in) | auto-discovered the ESP32 node `fishbucket-sensors`; encryption key from `fishbucket/esp32/secrets.yaml` |
| **Generic Camera** integration | `camera.fishbucket_camera` ← `rtsp://10.0.10.38:8554/aquarium` (the Pi's go2rtc) |
| **Living Here** dashboard | YAML mode, `dashboards/living-here.yaml` |

## Entities (from the ESP32 + Pi)
- `sensor.fishbucket_sensors_water_temperature`
- `sensor.fishbucket_sensors_water_tds`
- `sensor.fishbucket_sensors_tds_sensor_voltage` (diagnostic)
- `number.fishbucket_sensors_tds_calibration_k` (config)
- `camera.fishbucket_camera`

## Dashboard (YAML mode)
`dashboards/living-here.yaml` here is the source of truth; the live copy is
`/config/dashboards/living-here.yaml` on the HA box. Registered via this block
appended to `/config/configuration.yaml`:

```yaml
lovelace:
  dashboards:
    living-here:
      mode: yaml
      title: Living Here
      icon: mdi:fishbowl-outline
      show_in_sidebar: true
      filename: dashboards/living-here.yaml
```

### Deploy / update the dashboard
```bash
# from repo root
scp homeassistant/dashboards/living-here.yaml homeassistant:/config/dashboards/living-here.yaml
# editing an existing YAML dashboard's content: just reload the browser tab.
# adding a NEW dashboard (configuration.yaml change): ssh homeassistant 'ha core check && ha core restart'
```
Always `ha core check` before `ha core restart` — a malformed config blocks startup.

## Gotchas seen during setup
- **Empty add-on store on first boot.** A fresh HAOS came up with the Supervisor's
  add-on index empty (Repairs clean, `su info` healthy). Fix was `ha supervisor repair`
  (or `... restart`) — plain "Check for updates" only git-pulls the repos, it doesn't
  rebuild the index.
- Temperature shows in **°F** because the HA instance uses the imperial unit system
  (ESPHome sends °C; HA converts).
