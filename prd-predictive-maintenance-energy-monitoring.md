# Product Requirements Document
### Dual-Function Edge AI Demo Kit: Predictive Maintenance + Energy Monitoring

**Status:** Draft &nbsp;|&nbsp; **Owner:** Fadhli Hanif &nbsp;|&nbsp; **Last updated:** current working draft

---

## 1. Overview

This document defines the requirements for a demo kit combining two functions on edge-AI hardware: **predictive maintenance** (sound and temperature-based anomaly detection on a machine) and **energy monitoring** (power metering for a machine or building circuit). Both functions report to a single unified web dashboard. The kit is intended to ship as a self-contained unit in a single hardcase for demonstration purposes.

## 2. Problem Statement

- Machine faults (bearing wear, motor degradation) are often caught only after failure, causing unplanned downtime that is costlier than early detection would be.
- Energy consumption is typically only visible as a monthly bill, with no visibility into which equipment or time periods drive costs, or whether consumption patterns are abnormal.
- These two problems are usually solved with separate, disconnected systems, increasing cost and complexity for an end customer to adopt both.

## 3. Goals & Objectives

| Goal | Description |
|---|---|
| Demonstrate feasibility | Show that sound, temperature, and power anomaly detection can run on low-cost edge hardware and report to one dashboard |
| Validate architecture | Prove the two-board-plus-meter architecture works end-to-end before committing to a production design |
| Enable a stakeholder demo | Produce a working, portable, self-contained kit that can be demonstrated without dependency on venue infrastructure |
| Establish a production path | Identify what would need to change (sensors, models, hardening) to take this from demo to product |

## 4. Target Users / Stakeholders

- **Internal stakeholders / management** — evaluating whether to invest further in this product direction
- **Prospective customers** (factory/facility operators) — evaluating whether the capability is relevant to their machines/buildings
- **Engineering team** — building and maintaining the firmware, backend, and dashboard

## 5. Scope

### 5.1 In Scope

| Area | Included |
|---|---|
| Predictive maintenance | Sound anomaly detection (trained autoencoder, already validated); temperature anomaly detection (onboard thermistor + threshold/rate-of-rise rule) |
| Energy monitoring | Power anomaly detection via Acrel ADL400N meter (voltage, current, power, PF) polled over Modbus RTU/RS485 by a Raspberry Pi; threshold-based anomaly rule |
| Integration | MQTT-based data pipeline from both boards and the Pi into a shared NestJS/PostgreSQL backend |
| Dashboard | Single Vue 3 web app showing live status for both functions |
| Physical form factor | Both boards, the Pi, and supporting hardware packaged in one hardcase, self-contained power |

### 5.2 Out of Scope (this phase)

| Area | Excluded, with reason |
|---|---|
| Trained ML model for energy anomaly detection | No existing dataset; requires baseline data collection time not available in this phase |
| Harmonic/FFT-based power analysis | Meter already reports fundamental parameters; harmonic analysis adds complexity without demo-stage benefit |
| Building-level multi-circuit monitoring (NILM/disaggregation) | Single machine/circuit scope is sufficient to validate the architecture |
| Self-contained travel router/offline network | Deferred; demo can rely on existing Wi-Fi for this phase |
| Ambient-noise robustness improvements to the audio pipeline | Already functional; avoid destabilizing a working component under time pressure |
| Industrial-grade temperature transmitter (e.g. PR 5333A + RTD probe) | Onboard thermistor is sufficient for demo; noted as a production upgrade path |

## 6. Functional Requirements

| ID | Requirement |
|---|---|
| FR-1 | The system shall detect audio anomalies on the AI Eval Kit using a trained autoencoder model running on-device (TFLM), flagging deviation from learned normal machine sound |
| FR-2 | The system shall measure temperature via the CY8CPROTO's onboard thermistor and flag readings that exceed a configurable threshold or rise faster than a configurable rate |
| FR-3 | The system shall poll the Acrel ADL400N power meter over Modbus RTU (RS485) from a Raspberry Pi, retrieving voltage, current, active power, power factor, and frequency at a configurable interval |
| FR-4 | The system shall flag energy readings that exceed a configurable threshold |
| FR-5 | Each device (AI Eval Kit, CY8CPROTO, Raspberry Pi) shall publish its readings to a shared MQTT broker under a topic namespaced by a fixed device identifier |
| FR-6 | The backend shall ingest MQTT messages from all devices and persist them to PostgreSQL |
| FR-7 | The backend shall push live readings to the web dashboard via WebSocket |
| FR-8 | The dashboard shall display, in one view, live status for both predictive maintenance (sound + temperature) and energy monitoring (power), with a clear visual indicator (e.g. red/green) per function |
| FR-9 | The system shall allow on-site recalibration of anomaly thresholds for audio, temperature, and power without requiring a full firmware rebuild where feasible |

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Portability | The full kit shall operate from a single power source and connect to a standard Wi-Fi network without additional site infrastructure |
| Safety | Any wiring to the power meter shall use non-contact current sensing (CT clamp) and isolated voltage sensing; no direct resistive tap on live mains |
| Latency | Live dashboard updates shall reflect new sensor readings within a few seconds under normal network conditions |
| Reliability | The system shall recover automatically from a brief network interruption without manual intervention |
| Maintainability | Firmware update and recalibration procedures shall be documented so they can be performed by someone other than the original developer |
| Transparency | The dashboard or accompanying documentation shall clearly distinguish which anomaly checks are trained ML models versus fixed threshold rules |

## 8. System Architecture Overview

AI Eval Kit (audio) and CY8CPROTO (temperature) publish over Wi-Fi to an MQTT broker. A Raspberry Pi polls the Acrel ADL400N meter over RS485/Modbus RTU and publishes to the same broker. A NestJS backend subscribes to all topics, persists data to PostgreSQL, and pushes live updates to a Vue 3 dashboard over WebSocket. All components are physically packaged together in one hardcase.

## 9. Success Metrics

- Demo runs end-to-end without manual intervention, at least twice consecutively, before being shown externally
- All three signals (audio, temperature, power) visible and correctly attributed on the dashboard simultaneously
- Audio anomaly detection maintains its already-validated accuracy (id_02 model, 99.0% AUC) unchanged by this integration
- System recovers from a Wi-Fi disconnect/reconnect without requiring a restart

## 10. Milestones

| Milestone | Scope |
|---|---|
| M0 — Baseline | Audio anomaly detection validated (complete) |
| M1 — Predictive maintenance complete | Temperature sensing added and fused with audio on CY8CPROTO |
| M2 — Energy monitoring complete | Raspberry Pi polling the Acrel meter via Modbus, publishing readings |
| M3 — Integration complete | All devices reporting into one backend and dashboard |
| M4 — Demo kit assembled | Physical packaging, power, and network finalized in the hardcase |
| M5 — Demo-ready | Full rehearsal completed, honest framing of ML vs. rule-based components prepared |

## 11. Risks & Assumptions

| Risk / Assumption | Notes |
|---|---|
| Sensor/hardware lead time | Any component not already on hand introduces schedule risk; assumes hardware is ordered with buffer time |
| No existing energy dataset | Assumes threshold-based detection is acceptable for this phase; trained model is future work |
| Per-install recalibration required | Assumes thresholds will need manual tuning at each new deployment, including the demo site |
| Venue network dependency | Assumes reasonable Wi-Fi availability at demo time; self-contained networking is out of scope this phase |
| No real fault data | Validation relies on threshold tests and prior playback-based audio validation, not real mechanical/electrical failures |

## 12. Open Questions

- Should a trained ML model replace the threshold-based energy anomaly check in a future phase, and what data collection plan would that require?
- Is building-level (multi-circuit) energy monitoring a future requirement, and if so, on what timeline?
- Does the production version require the industrial-grade temperature transmitter path (e.g. PR 5333A + RTD probe) instead of the onboard thermistor?
- What is the target unit cost for a production version, and does that change any of the component choices made for this demo?
