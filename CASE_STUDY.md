# Case 04 — Smart Robotics Monitoring & Operator Assistance

## Operational problem

Operators at a fictional manufacturing facility visually monitor conveyors and a pick-and-place unit. They respond to faults and record maintenance in notebooks or spreadsheets. Maintenance engineers and supervisors lack a trustworthy timeline of readings, data gaps, actions and recurring faults. Automation/IT owns controller connectivity, edge software and network reliability.

The case brief's M1/M2/M3 readings are examples only. M2's 79°C and 8.5 mm/s may warrant engineering review, but no validated motor limits, operating load or sensor calibration are provided. M3 has no vibration data, so the system cannot infer its vibration condition.

## Three reliability / efficiency KPIs

| KPI | Definition | Why it matters |
| --- | --- | --- |
| Time to operator acknowledgment | Minutes from a validated event to the first recorded human acknowledgment | Measures response speed without confusing a notification with a completed repair. |
| Telemetry coverage | Expected sensor intervals with valid, timely readings / all expected intervals | Exposes missing sensors and network gaps; prevents false confidence from stale values. |
| Unplanned downtime | Minutes production is stopped unexpectedly per asset per month | Connects monitoring and maintenance actions to the operating outcome. |

Baselines and targets require site data; this simulation does not claim performance improvement.

## Technical discovery questions

1. What are each motor/axis model, nameplate ratings, allowable operating conditions and validated warning/shutdown limits?
2. Which PLC, drives, sensors and edge gateways exist, and how are they calibrated and synchronized in time?
3. Which interfaces and protocols are available (for example, OPC UA, Modbus or MQTT), and which are read-only?
4. What data frequency, buffering, retention and network outage behavior are required?
5. Which historical faults, maintenance work orders and operator observations are available for evaluation?
6. What interlocks, emergency-stop procedures and change-control rules govern any physical intervention?
7. Who may acknowledge, escalate or close an event, and what evidence must be recorded?

## Future technical path and safety boundary

`Equipment sensors → PLC/controller → read-only edge collector → validation/timestamping → telemetry store → monitoring API/UI → operator acknowledgment and escalation.`

Controller and edge code would read sensor tags, timestamp and validate units, buffer during outages, then publish to an authenticated ingestion API. The cloud side would retain raw values and quality flags, calculate trends against **engineering-approved** limits, create events and join maintenance history. The UI would mark missing or stale data prominently. A rules/AI assistant could search approved manuals and work orders for suggested checks with source citations; only trained operators and engineers decide what to do physically.

AI must not override PLC interlocks, issue actuator commands, declare equipment safe from missing data or hide a fault because a model predicts a false alarm. During network interruption, the app should show stale status and rely on local validated safety controls. Production integration needs OT network review, least-privilege credentials, signed firmware, cyber security assessment and hardware-in-the-loop testing.

## UI mockup and prompt decisions

The working `index.html` is the monitoring mockup. It combines asset states, readings, open events, suggested checks, maintenance notes, operator acknowledgment and a simulation panel. Initial prompt to Codex: “Build a robotics monitoring screen using the exact illustrative M1/M2/M3 case readings. Show sensor offline and operator action history. Avoid presenting unvalidated thresholds as safety limits.” Refinement: add network-gap simulation, stale-data handling, explicit human escalation and no actuation endpoint.

The dark industrial navigation and light telemetry canvas separate equipment identity from review actions. The screen says “simulation” and “illustrative” in visible locations so a reviewer cannot mistake it for a real plant controller.

## Hardware / embedded experience and simulation plan

Ravi Kumar Rao's supplied resume covers AI/ML, web projects and a RAG chatbot; it does **not** establish a personal physical robotics or embedded-hardware project. This repository therefore does not claim one. The proposed next step is a bench simulation using a virtual PLC or microcontroller simulator, synthetic temperature/vibration/current streams, a read-only MQTT or OPC UA collector, injected sensor disconnects and network interruptions, and an operator test script. Physical integration would require mentor supervision, device specifications and site-approved safety procedures.

## UAT scenarios

| Scenario | Steps | Safe expected outcome |
| --- | --- | --- |
| Disconnected sensor | Run “M3 sensor gap,” then inspect M3 and ask the assistant. | Vibration shows “No data”; event records the gap; assistant avoids inferring vibration or safety state and suggests connection checks. |
| Network interruption | Run “Network interruption” while old numeric values remain on screen. | All assets are marked stale; no old value is presented as live; restoration prompts timestamp/buffer validation. |
| Unexpected M2 trend / false alarm | Run “M2 review trend,” acknowledge it with a note, then inspect the history. | Event asks for engineer review against validated equipment-specific limits; acknowledgment is recorded but does not clear a physical fault or command an actuator. |

The prototype uses Python `ThreadingHTTPServer`, SQLite and browser JavaScript. It was generated with OpenAI Codex at Ravi Kumar Rao's request. It is simulation evidence and an architecture proposal, not evidence of hardware built or personally coded by the candidate.
