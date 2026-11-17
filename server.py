"""Fictional robotics monitoring simulator; never controls physical equipment."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get("ROBOTICS_DB", ROOT / "robotics.sqlite3"))
FILES = {"/", "/index.html", "/styles.css", "/app.js"}
ASSETS = {"M1", "M2", "M3"}


def now():
    return datetime.now(timezone.utc)


def iso(value=None):
    return (value or now()).isoformat(timespec="seconds")


@contextmanager
def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_event(db, asset, kind, severity, message):
    cur = db.execute("INSERT INTO events(asset,kind,severity,message,status,created_at) VALUES(?,?,?,?,?,?)",
                     (asset, kind, severity, message, "Open", iso()))
    return cur.lastrowid


def initialize():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS assets (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, location TEXT NOT NULL,
          temperature REAL, vibration REAL, current REAL,
          sensor_state TEXT NOT NULL, last_seen TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, asset TEXT NOT NULL,
          kind TEXT NOT NULL, severity TEXT NOT NULL, message TEXT NOT NULL,
          status TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS actions (
          id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL REFERENCES events(id),
          operator TEXT NOT NULL, note TEXT NOT NULL, at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS maintenance (
          id INTEGER PRIMARY KEY AUTOINCREMENT, asset TEXT NOT NULL,
          work TEXT NOT NULL, completed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        if db.execute("SELECT COUNT(*) FROM assets").fetchone()[0]:
            return
        stamp = iso()
        db.executemany("INSERT INTO assets VALUES (?,?,?,?,?,?,?,?)", [
            ("M1", "Conveyor drive", "Line A · Infeed", 52.0, 3.1, 4.0, "Connected", stamp),
            ("M2", "Conveyor drive", "Line A · Transfer", 79.0, 8.5, 6.9, "Connected", stamp),
            ("M3", "Robotic axis", "Cell B · Pick & place", 61.0, None, 5.2, "Sensor offline", stamp),
        ])
        db.execute("INSERT INTO settings VALUES ('network_online','true')")
        create_event(db, "M2", "Review trend", "Review", "Elevated illustrative temperature/vibration trend; engineering limits not validated.")
        create_event(db, "M3", "Sensor offline", "Data gap", "Vibration sensor is offline. Do not infer equipment condition from missing data.")
        db.executemany("INSERT INTO maintenance(asset,work,completed_at) VALUES(?,?,?)", [
            ("M1", "Visual belt and bearing inspection recorded by maintenance.", iso(now()-timedelta(days=10))),
            ("M2", "Drive bearing lubricated; trend review recommended.", iso(now()-timedelta(days=4))),
            ("M3", "End-effector alignment check completed.", iso(now()-timedelta(days=14))),
        ])


def asset_state(row, network_online):
    item = dict(row)
    age = (now() - datetime.fromisoformat(item["last_seen"])).total_seconds()
    if not network_online or age > 120:
        item["display_state"] = "Stale data"
    elif item["sensor_state"] != "Connected" or item["vibration"] is None:
        item["display_state"] = "Sensor offline"
    elif item["id"] == "M2" and (item["temperature"] >= 75 or item["vibration"] >= 8):
        item["display_state"] = "Review trend"
    else:
        item["display_state"] = "Reporting"
    item["age_seconds"] = round(age)
    return item


def guidance(asset, db, network_online):
    row = db.execute("SELECT * FROM assets WHERE id=?", (asset,)).fetchone()
    latest = db.execute("SELECT work,completed_at FROM maintenance WHERE asset=? ORDER BY completed_at DESC LIMIT 1", (asset,)).fetchone()
    if not row:
        return None
    state = asset_state(row, network_online)["display_state"]
    if state == "Stale data":
        checks = ["Confirm the edge gateway and network path", "Check timestamp and buffered data", "Use approved local procedures; escalate if live state is required"]
    elif state == "Sensor offline":
        checks = ["Confirm sensor power and cabling", "Inspect controller input diagnostics", "Avoid diagnosing vibration until telemetry is restored"]
    elif state == "Review trend":
        checks = ["Compare current readings with validated equipment-specific limits", "Review recent maintenance and operating load", "Ask a maintenance engineer to inspect before making a control decision"]
    else:
        checks = ["Review trend against engineering baseline", "Continue routine inspection", "Escalate any operator-observed abnormal behavior"]
    return {"asset": asset, "display_state": state, "checks": checks,
            "maintenance": dict(latest) if latest else None,
            "disclaimer": "Rule-based guidance only. Never overrides PLC safety logic, interlocks or operator procedures."}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        print("Robotics demo:", fmt % args)

    def send_json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 8192:
            raise ValueError("Invalid request size")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ValueError("Expected an object")
        return data

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/state":
            with connect() as db:
                online = db.execute("SELECT value FROM settings WHERE key='network_online'").fetchone()[0] == "true"
                assets = [asset_state(row, online) for row in db.execute("SELECT * FROM assets ORDER BY id")]
                events = [dict(row) for row in db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 25")]
                actions = [dict(row) for row in db.execute("SELECT * FROM actions ORDER BY id DESC LIMIT 15")]
                maintenance = [dict(row) for row in db.execute("SELECT * FROM maintenance ORDER BY completed_at DESC LIMIT 10")]
            metrics = {"reporting": sum(a["display_state"] == "Reporting" for a in assets),
                       "open_events": sum(e["status"] == "Open" for e in events),
                       "data_gaps": sum(a["display_state"] in {"Stale data", "Sensor offline"} for a in assets),
                       "acknowledged": sum(e["status"] == "Acknowledged" for e in events)}
            return self.send_json({"assets": assets, "events": events, "actions": actions,
                                   "maintenance": maintenance, "network_online": online, "metrics": metrics,
                                   "updated_at": iso()})
        match = re.fullmatch(r"/api/assets/(M[123])/guidance", path)
        if match:
            with connect() as db:
                online = db.execute("SELECT value FROM settings WHERE key='network_online'").fetchone()[0] == "true"
                return self.send_json(guidance(match[1], db, online))
        if path.startswith("/api/"):
            return self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        if path not in FILES:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self.read_json()
            if path == "/api/simulate":
                scenario = str(data.get("scenario", ""))
                if scenario not in {"nominal", "elevated_m2", "sensor_offline", "network_gap", "restore_network"}:
                    raise ValueError("Choose a supported simulation scenario")
                with connect() as db:
                    stamp = iso()
                    if scenario == "network_gap":
                        db.execute("UPDATE settings SET value='false' WHERE key='network_online'")
                        create_event(db, "Gateway", "Network interruption", "Data gap", "Live telemetry unavailable; last readings must be treated as stale.")
                    elif scenario == "restore_network":
                        db.execute("UPDATE settings SET value='true' WHERE key='network_online'")
                        db.execute("UPDATE assets SET last_seen=? WHERE sensor_state='Connected'", (stamp,))
                        create_event(db, "Gateway", "Connection restored", "Info", "Telemetry link restored. Validate buffered data and timestamps.")
                    else:
                        online = db.execute("SELECT value FROM settings WHERE key='network_online'").fetchone()[0] == "true"
                        if not online:
                            return self.send_json({"error": "Restore the simulated network before sending readings"}, HTTPStatus.CONFLICT)
                        if scenario == "nominal":
                            db.execute("UPDATE assets SET temperature=52.4,vibration=3.2,current=4.1,sensor_state='Connected',last_seen=? WHERE id='M1'", (stamp,))
                            db.execute("UPDATE assets SET temperature=64.0,vibration=5.1,current=5.8,sensor_state='Connected',last_seen=? WHERE id='M2'", (stamp,))
                            db.execute("UPDATE assets SET temperature=61.0,vibration=4.0,current=5.2,sensor_state='Connected',last_seen=? WHERE id='M3'", (stamp,))
                            create_event(db, "Line A", "New snapshot", "Info", "Fresh illustrative readings received; no safety determination made.")
                        elif scenario == "elevated_m2":
                            db.execute("UPDATE assets SET temperature=79.0,vibration=8.5,current=6.9,sensor_state='Connected',last_seen=? WHERE id='M2'", (stamp,))
                            create_event(db, "M2", "Review trend", "Review", "Illustrative readings differ from nominal demo pattern. Request engineer review.")
                        else:
                            db.execute("UPDATE assets SET vibration=NULL,sensor_state='Sensor offline',last_seen=? WHERE id='M3'", (stamp,))
                            create_event(db, "M3", "Sensor offline", "Data gap", "Vibration data missing. Condition cannot be inferred from absent telemetry.")
                return self.send_json({"ok": True, "scenario": scenario})
            match = re.fullmatch(r"/api/events/(\d+)/ack", path)
            if match:
                operator = str(data.get("operator", "")).strip()[:80]
                note = str(data.get("note", "")).strip()[:500]
                if len(operator) < 2 or len(note) < 10:
                    raise ValueError("Operator name and a note of at least 10 characters are required")
                with connect() as db:
                    event = db.execute("SELECT status FROM events WHERE id=?", (int(match[1]),)).fetchone()
                    if not event:
                        return self.send_json({"error": "Event not found"}, HTTPStatus.NOT_FOUND)
                    if event["status"] != "Open":
                        return self.send_json({"error": "Event was already acknowledged"}, HTTPStatus.CONFLICT)
                    db.execute("UPDATE events SET status='Acknowledged' WHERE id=?", (int(match[1]),))
                    db.execute("INSERT INTO actions(event_id,operator,note,at) VALUES(?,?,?,?)",
                               (int(match[1]), operator, note, iso()))
                return self.send_json({"ok": True, "event_id": int(match[1])})
            if path == "/api/assistant":
                text = str(data.get("question", ""))[:400]
                match = re.search(r"\bM[123]\b", text.upper())
                if not match:
                    return self.send_json({"answer": "Ask about M1, M2 or M3. I can suggest checks from recorded telemetry and maintenance history; I cannot control equipment."})
                asset = match[0]
                with connect() as db:
                    online = db.execute("SELECT value FROM settings WHERE key='network_online'").fetchone()[0] == "true"
                    result = guidance(asset, db, online)
                return self.send_json({"answer": f"{asset}: {result['display_state']}. Suggested checks: " + "; ".join(result["checks"]) + ". Human escalation and validated site procedures take precedence.", "guidance": result})
            return self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)


if __name__ == "__main__":
    initialize()
    port = int(os.environ.get("PORT", "8768"))
    host = "0.0.0.0" if "PORT" in os.environ else "127.0.0.1"
    print(f"Robotics demo listening on http://{host}:{port}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
