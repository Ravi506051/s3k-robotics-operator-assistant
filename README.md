# Shiftline — Smart Robotics Monitoring & Operator Assistance

A fictional simulation for **S3K Case Study 04 / Robotics**. It shows equipment readings, data gaps, review events, operator acknowledgments, maintenance history and bounded troubleshooting guidance.

## Run locally

```powershell
python server.py
```

Open `http://127.0.0.1:8768/`. Python 3.10+ standard library is the only requirement. SQLite is initialized automatically. Set `ROBOTICS_DB` to change the database path.

## Try the scenarios

1. Inspect M1, M2 and M3. Their initial readings match the fictional case brief. M3's vibration reading is absent.
2. Run **M2 review trend** or **M3 sensor gap**. Open events and suggested checks.
3. Run **Network interruption**. Every last reading becomes stale, even if its numeric value remains visible. Restore the simulated network.
4. Acknowledge an event with an operator name and a note. Check the action history.
5. Ask the assistant about M1, M2 or M3. Its answer uses saved state and fixed troubleshooting text; it never controls hardware.

The readings are **illustrative, not validated safety thresholds**. This app is a software simulation only: it has no PLC, sensor, actuator, production network or safety certification. Acknowledgment does not clear a physical fault or issue a command. It has no production user authentication.

See [CASE_STUDY.md](CASE_STUDY.md) for discovery, KPIs, architecture, UAT and the hardware simulation plan.

## API

`GET /api/state`, `GET /api/assets/{id}/guidance`, `POST /api/simulate`, `POST /api/events/{id}/ack`, `POST /api/assistant`.
