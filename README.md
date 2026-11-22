# Shiftline: Smart Robotics Monitoring and Operator Assistance

A software simulation for **S3K Internship 2026, Case Study 04: Robotics**. Shiftline lets an operator inspect equipment readings, spot missing or stale data, review events, acknowledge them, and read bounded troubleshooting guidance.

**[Read the case study](CASE_STUDY.md)** · **[Download the source ZIP](downloads/s3k-robotics-operator-assistant.zip)**

## Run locally

Requires Python 3.10 or newer. No external packages, API keys, or hardware are needed.

```powershell
python server.py
```

Open [http://127.0.0.1:8768/](http://127.0.0.1:8768/). SQLite is initialized automatically. Set `ROBOTICS_DB` before launch to change the database path.

## Explore the scenarios

| Scenario | What to observe |
| --- | --- |
| Initial equipment view | M1, M2, and M3 readings; M3 has no vibration value |
| M2 review trend | A simulated trend and the checks suggested for an operator |
| M3 sensor gap | Missing telemetry is surfaced instead of treated as a healthy value |
| Network interruption | The last readings remain visible but become stale |
| Event acknowledgment | Operator name, note, and timestamp are saved in history |

After trying the network interruption, restore the simulated connection. Ask the assistant about M1, M2, or M3 to see guidance based on saved state and fixed troubleshooting text.

The frontend is `index.html`, `styles.css`, and `app.js`. `server.py` serves the HTTP API and stores simulation state and acknowledgments in SQLite. [CASE_STUDY.md](CASE_STUDY.md) describes the problem, workflow, architecture, success metrics, and UAT plan.

## API at a glance

`GET /api/state` · `GET /api/assets/{id}/guidance` · `POST /api/simulate` · `POST /api/events/{id}/ack` · `POST /api/assistant`

## Safety and scope

The readings and scenarios are fictional; their values are **not validated safety thresholds**. The app has no PLC, sensor, actuator, production network, or safety certification. Acknowledging an event records a review; it does not clear a physical fault or send a machine command. The assistant cannot control hardware. This demo has no production user authentication.
## Component map

| Component | Responsibility |
|---|---|
| `index.html`, `styles.css`, `app.js` | Browser dashboard and operator interactions |
| `server.py` | Standard-library HTTP API and simulation logic |
| SQLite | Demo assets, events, acknowledgements, and settings |

The demo uses Python's standard library and needs no package installation. Its readings and guidance are simulated; it has no connection to physical equipment.
