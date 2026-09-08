# Predictive Maintenance & Energy Monitoring
### A beginner's step-by-step development guide — written to explain not just what to do, but why, at every step

---

## Chapter 1 — What Are We Actually Building?

You're building a small device (well, two boards plus a power meter) that watches over a machine and its electricity use, and warns you before something goes wrong. It has two separate jobs:

- **Predictive maintenance** — listening to a machine's sound and feeling its temperature, to catch a fault (like a worn bearing) before it becomes a breakdown.
- **Energy monitoring** — watching how much electricity a machine or building circuit uses, to catch unusual power draw and understand costs.

Both jobs send their data to one shared dashboard (a webpage) so a person can see the machine's full health picture in one place — sound, temperature, and power — instead of checking three separate gadgets.

> **Think of it like a doctor's check-up for a machine:** listening with a stethoscope (sound), checking temperature (thermometer), and checking blood pressure (electrical "vital signs"). Combining all three tells you much more than any one alone.

---

## Chapter 2 — Words You'll See a Lot (Plain Explanations)

| Term | What it means |
|---|---|
| **Sensor** | A small device that measures something physical (sound, heat, electric current) and turns it into an electrical signal a computer can read. |
| **ADC (Analog-to-Digital Converter)** | A built-in part of the board that converts a sensor's continuous electrical signal into a number the microcontroller can work with. |
| **Anomaly detection** | Teaching a computer what "normal" looks like, so it can flag anything that doesn't match — without you having to define every possible fault in advance. |
| **Edge AI** | Running the AI model directly on the small board itself, instead of sending raw data to the cloud to be processed. Faster, cheaper, and more private. |
| **Threshold** | The simplest kind of anomaly check: "if this number goes above X, flag it." No AI needed — just a fixed limit. |
| **RS485** | A type of wiring standard for sending data over longer distances reliably (used a lot in industrial equipment). Two wires, differential signal, less prone to interference. |
| **Modbus RTU** | A simple, very common language that industrial devices (like power meters) use to talk over RS485. One device asks a question ("what's your current reading?"), the other answers. |
| **MQTT** | A lightweight messaging system for small devices to publish short messages (like a sensor reading) to a shared channel (called a "topic"), which other systems can subscribe to and receive. |
| **Gateway** | A device that sits between your sensors/meters and the internet/cloud, collecting data and forwarding it onward. |
| **Dashboard** | The webpage where all the collected data is displayed visually — charts, numbers, alerts — for a human to read. |

---

## Chapter 3 — Your Hardware, Explained

| Item | What it does in plain terms |
|---|---|
| **PSoC 6 AI Eval Kit** | A small development board with a built-in microphone. It already listens to a machine and has learned what "normal" sound is, so it can flag odd sounds. |
| **CY8CPROTO-062-4343W** | A second, similar development board. It also has a built-in microphone AND a built-in temperature sensor, so it can do both sound and temperature checks for predictive maintenance. |
| **Acrel ADL400N power meter** | A professional device that clips onto electrical wires (using a CT clamp — like a clip-on ammeter) and measures voltage, current, and power accurately, without needing to cut any wires. |
| **Raspberry Pi** | A small, affordable computer (much simpler to program than the development boards) that will talk to the power meter and forward its readings onward. |
| **MQTT broker (software)** | A small program (running on the Pi or a server) that acts like a post office — collecting messages from all your devices and handing them to whoever's listening. |

---

## Chapter 4 — Building Block 1: Sound-Based Predictive Maintenance (Already Done)

This part is already working, so this chapter is just explaining what happened, so you understand the system you're building on top of.

- A microphone on the AI Eval Kit records sound continuously.
- The board turns that sound into a kind of "fingerprint" (a spectrogram) using math (an FFT).
- A small AI model (trained ahead of time on recordings of a normal fan) checks whether the current sound fingerprint looks normal or not.
- If it looks abnormal, the board flags it — all of this happens on the board itself, in real time, without needing the internet.

> **Why this matters for what comes next:** the same basic pattern (sensor → processing → AI or threshold check → flag) repeats in every other part of this project. Once you understand this one, the rest are variations on the same idea.

---

## Chapter 5 — Building Block 2: Adding Temperature Sensing

The CY8CPROTO board has a temperature sensor already built in (called a thermistor) — you don't need to buy or wire anything extra. A thermistor is a resistor whose resistance changes with temperature, so by measuring that resistance, you can calculate the temperature.

| Step | What you do | Why |
|---|---|---|
| 1 | In ModusToolbox (the board's programming software), set one pin to "power on" and another to "ground" around the thermistor | This forms a simple circuit called a voltage divider — it only needs power while you're taking a reading, saving energy |
| 2 | Set a third pin to read as an ADC (analog input) | This is where you measure the voltage that results from the divider circuit |
| 3 | Convert the voltage reading into a resistance value using a simple formula | The resistance is what actually reflects temperature — voltage is just how we measure it electrically |
| 4 | Convert resistance into an actual temperature (°C) using the thermistor's datasheet formula | This turns a raw electrical number into something a human/dashboard can understand |
| 5 | Compare the temperature to a fixed limit, and check how fast it's rising | This is your anomaly check — no AI training needed for this part, just simple rules |

---

## Chapter 6 — Building Block 3: Energy Monitoring

This part doesn't use either PSoC 6 board at all — it uses the Acrel power meter and a Raspberry Pi instead. This is actually simpler to build than it sounds, because the power meter does all the hard electrical measurement work for you.

### 6.1 How the meter measures power (recap)

A clamp (the CT clamp) wraps around the electrical wire without touching bare metal, and senses current by detecting the magnetic field around the wire. The meter also taps the voltage directly. From these two readings, it calculates power, and it does all of this on its own — you don't calculate anything yourself.

### 6.2 How the Raspberry Pi talks to the meter

| Step | What you do | Why |
|---|---|---|
| 1 | Connect a USB-to-RS485 adapter to the Raspberry Pi, and wire its A/B terminals to the meter's A/B terminals | RS485 is the "language" the meter physically speaks; the Pi doesn't have this built in, so the adapter translates USB ↔ RS485 |
| 2 | Install Python and the pymodbus library on the Raspberry Pi | pymodbus is a ready-made toolkit that already knows how to "speak" Modbus RTU, so you don't have to build that from scratch |
| 3 | Write a short Python script that asks the meter for specific values (voltage, current, power) every few seconds | This is the actual "reading" step — like asking the meter a question and waiting for its answer |
| 4 | Compare the power reading to a fixed limit you decide (a threshold) | This is your anomaly check for energy — same simple idea as the temperature check |
| 5 | Send the result to the MQTT broker so it reaches the same dashboard as the other two signals | This is what makes it feel like "one system" instead of three separate projects |

> **Safety note:** if any of this touches real building/mains electricity, always use the CT clamp for current and proper isolation for voltage — never make a direct bare-wire connection to live power.

---

## Chapter 7 — Bringing It All Together: The Software Side

By this point you have three separate sources of data: sound (AI Eval Kit), temperature (CY8CPROTO), and power (Raspberry Pi). This chapter connects them into one system.

| Step | What you do | Why |
|---|---|---|
| 1 | Install an MQTT broker (a small free program called Mosquitto) on the Raspberry Pi | This becomes the shared "post office" all three data sources send their readings to |
| 2 | Give each device a fixed name (device_id) and have it publish its readings under that name | So the system always knows which reading came from which device |
| 3 | Build a small backend program (using NestJS) that listens to the broker and saves readings into a database (PostgreSQL) | This keeps a history of readings, not just the current moment, so you can see trends |
| 4 | Build a webpage (using Vue 3) that shows live readings from all three sources side by side | This is the actual dashboard a person looks at |
| 5 | Add a simple red/green indicator for each function so it's obvious at a glance if something's wrong | Makes the demo/product easy to understand without reading raw numbers |

---

## Chapter 8 — Physical Assembly: Building the Demo Kit

- Mount both PSoC 6 boards and the Raspberry Pi inside the hardcase, leaving the meter and its CT clamp accessible for wiring to the target machine/circuit.
- Power everything from a single USB hub or power bank so there's just one thing to plug in.
- Connect all devices to the same Wi-Fi network so they can all reach the MQTT broker.
- Label the case clearly, and keep the boards' programming ports reachable in case you need to update firmware later without opening everything up.

---

## Chapter 9 — Testing Before You Show It to Anyone

- Check each signal on its own first: does the sound score change when you make an odd noise near the machine? Does the temperature reading rise when you warm the sensor with your hand?
- Then check the dashboard: do all three signals show up live, correctly labeled?
- Then unplug the Wi-Fi briefly and plug it back in — does the system recover on its own, or does something get stuck?
- Finally, run through the entire demo start to finish, twice, exactly as you'll present it.

---

## A Note on What's "Real AI" vs. "Just Rules" Here

It's worth being clear with yourself (and anyone you show this to) about which parts use trained AI and which use simple fixed rules:

| Signal | How it works |
|---|---|
| Sound (AI Eval Kit) | Real trained AI model (an autoencoder) — learned what normal sound looks like from real recordings |
| Temperature (CY8CPROTO) | Simple threshold/rate-of-rise rule — no training involved, just fixed limits you set |
| Energy (Raspberry Pi + meter) | Simple threshold rule for now — same as temperature; a trained model could be added later once you've collected enough normal-operation data |

> There's nothing wrong with using simple rules — they're honest, easy to explain, and often good enough. The key is being upfront about which is which, rather than implying everything is "AI-powered" when parts of it are simpler than that.
