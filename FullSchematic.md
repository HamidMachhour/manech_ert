## Project: 16-Electrode Multi-Multiplexed ERT System

This document provides the complete structural blueprint, hardware wiring map, pin allocations, and core automation execution logic for the Electrical Resistivity Tomography (ERT) system. This layout uses **exactly** the components I have on hand, entirely bypassing the need for a separate ESP32 or secondary current-sensor ICs like the INA219.

---

## 📦 System Component Inventory

The setup is fully optimized around the following four active hardware units:
1. **Host Automation Controller:** Orange Pi Zero (512MB RAM, running Armbian / Linux headless).
2. **Digital I/O Expander Matrix:** 1 × MCP23017 (16-Bit digital I/O port expander communicating over I2C).
3. **Switching Rail Matrix:** 1 × 16-Channel Mechanical Relay Module Board (Optocoupler isolated, active-low or active-high triggering).
4. **High-Resolution Instrumentation ADC:** 1 × ADS1115 (16-Bit Delta-Sigma Analog-to-Digital Converter with built-in Programmable Gain Amplifier, communicating over I2C).
5. **Physical Subsurface Array:** 16 × Steel Grounding Stakes (Aligned linearly, typically spaced at a constant interval, e.g., $a = 2\\ {meters}$).

---

## 📐 Master Wiring & Interconnection Architecture

Every digital integrated circuit (IC) in this design interfaces in parallel over a shared, high-speed **I2C Serial Communication Bus** driven natively by the Orange Pi Zero.

### 1. Digital Power & I2C Control Infrastructure
The Orange Pi Zero supplies the reference power rails and commands both the expander and the data acquisition converter simultaneously.

```text
Orange Pi Zero Header Pins
┌────────────────────────┐
│ [Pin 2]  5V Power ─────┼────────────────────────► To 16-Channel Relay Board VCC
│ [Pin 4]  3.3V Power ───┼───────────┬────────────► To IC VCC (MCP23017 Pin 9 & ADS1115 Pin 1)
│ [Pin 6]  GND ──────────┼───┬───────┼────────────► Common System Ground Reference Rail (GND)
│ [Pin 3]  I2C_SDA ──────┼───┼───┬───┼───┬────────► Shared I2C Data Rail (Serial Data Line)
│ [Pin 5]  I2C_SCL ──────┼───┼───┼───┴───┼───► Shared I2C Clock Rail (Serial Clock Line)
└────────────────────────┘   │   │           │   │
                             ▼   ▼           ▼   ▼
                        ┌─────────┐     ┌─────────┐
                        │ ADS1115 │     │MCP23017 │
                        └─────────┘     └─────────┘

```

#### I2C Hardware Addressing Verification

To ensure the Linux kernel hooks the devices cleanly on Bus `1` without structural address collision, verify the hardware address configurations:

* **ADS1115 Address:** Connect the `ADDR` pin directly to **GND**. This forces the chip to listen exclusively on binary I2C address `0x48`.
* **MCP23017 Address:** Connect the three hardware address selector pins (`A0`, `A1`, `A2`) directly to **GND**. This locks the expander onto binary I2C address `0x20`.

---

### 2. Analog Frontend & Power Shunt Measuring Subsystem

Instead of an external standalone integrated circuit for current monitoring, the injection current ($I$) is measured analytically. A high-power precision **Shunt Resistor** ($R_{\text{shunt}} = 10\\ \Omega$, 5W to 10W rated) is wired directly in-series between the High-Voltage DC Power supply and the switching trunk line.

```text
High-Voltage DC (+) ────► [ 10 Ohm Shunt Resistor ] ────► Master Power Injection Trunk Line A
                               │                 │
                               ▼                 ▼
                        [ ADS1115 A2 ]    [ ADS1115 A3 ]  <-- Differential Current Measure

High-Voltage DC (-) ────────────────────────────────────► Master Power Injection Trunk Line B


Master Potential Measurement Trunk Line M ──────────────► [ ADS1115 A0 ] <-- Differential Ground
Master Potential Measurement Trunk Line N ──────────────► [ ADS1115 A1 ]     Voltage Measure (V)

```

* **Injection Current Calculation ($I$):** The ADS1115 samples channels `A2` and `A3` differentially to isolate the tiny voltage drop across the shunt. Current is calculated in software via Ohm's Law: $I = V_{\text{drop}} / R_{\text{shunt}}$.
* **Subsurface Voltage Return ($V$):** Channels `A0` and `A1` are sampled differentially to read the true residual voltage returning from the subterranean electrical field.

---

### 3. The 16-Channel Common Bus Selector Matrix

The MCP23017 routes its digital output pins directly across the input trigger lines (`IN1` to `IN16`) of the relay board. The **Common (COM)** terminals of all 16 relays are tied together to build the master trunk, while the **Normally Open (NO)** pins link directly out to the field stakes.

```text
       ┌────────────────────────── MCP23017 Output Register Mapping ────────────────┐
       │   GPA0   GPA1   GPA2   GPA3   GPA4   GPA5   GPA6   GPA7                     │
       │    │      │      │      │      │      │      │      │                      │
       ▼    ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼                      ▼
           IN1    IN2    IN3    IN4    IN5    IN6    IN7    IN8  (To Relays 1-8)
       │                                                                            │
       │   GPB0   GPB1   GPB2   GPB3   GPB4   GPB5   GPB6   GPB7                     │
       │    │      │      │      │      │      │      │      │                      │
       ▼    ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼                      ▼
           IN9    IN10   IN11   IN12   IN13   IN14   IN15   IN16 (To Relays 9-16)
       └────────────────────────────────────────────────────────────────────────────┘

                               SHARED MASTER COMMON TRUNK BUS
                        (Trunk Lines A, B, M, N Time-Multiplexed)
                                             │
               ┌─────────────────────────────┴─────────────────────────────┐
               ▼                             ▼                             ▼
      [Relay 1 Common]              [Relay 2 Common]              [Relay 16 Common]
        (Normally Open)               (Normally Open)               (Normally Open)
               │                             │                             │
               ▼                             ▼                             ▼
        Electrode Stake 1             Electrode Stake 2             Electrode Stake 16
         (Node 0 Meters)               (Node 2 Meters)               (Node 30 Meters)

```

---

## ⚡ Core Operational Sequence (Time-Multiplexing Logic)

Because a single-layer common bus layout shares its signal tracks, closing relays simultaneously for distinct inputs would lead to short circuits. To bypass this hardware limit, the Python script coordinates a **three-phase time-multiplexed cycle** for each individual quadrupole step in the survey profile:

1. **Phase 1: Energization & Current Sensing:** The script commands the MCP23017 to seal **only** the two targeted current relays (e.g., Relays 1 and 4 acting as $A$ and $B$). The high-voltage grid initializes, and the ADS1115 instantly samples channels `A2/A3` to compute the total injection amperage ($I$).
2. **Phase 2: Power Isolation & Voltage Reading:** The script instantly cuts power, opening the $A$ and $B$ relays. A microsecond delay passes to assure physical detachment. Next, the script closes **only** the two targeted voltage relays (e.g., Relays 2 and 3 acting as $M$ and $N$). The ADS1115 samples channels `A0/A1` to capture the subterranean return potential ($V$). **Because $A$ and $B$ are open during this phase, high voltage can never feed back into and destroy the input channels.**
3. **Phase 3: Matrix Zeroization:** All relays are cleared back to an absolute zero state (`0x00`), draining any remaining capacitance before launching the next step in the geometric array profile.

---

## 🐍 Unified Automation & Ingestion Script

Execute this Python script directly on the Orange Pi Zero. It automates the relay crossbar, drives the data acquisition sequences, calculates apparent resistivity, and transmits the resulting data payload straight across the local network to the MySQL server on the LAPTOP  workstation.

``` Python

#!/usr/bin/env python3
import time
import smbus2
import mysql.connector
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# --- SYSTEM SETTINGS & PARAMETERS ---
EXPANDER_ADDR = 0x20  # MCP23017 I2C Address
R_SHUNT = 10.0        # Value of physical precision shunt resistor in Ohms
ELECTRODE_SPACING = 2.0  # Spacing between ground stakes in meters
LAPTOP_IP = "10.42.0.1"  # Hotspot gateway IP of the LAPTOP  Workstation

# --- HARDWARE INTERFACE INITIALIZATION ---
i2c_bus = busio.I2C(board.SCL, board.SDA)
adc = ADS.ADS1115(i2c_bus)
adc.gain = 1  # Full-scale range adjusted to +/- 4.096V

bus = smbus2.SMBus(1)

bus.write_byte_data(EXPANDER_ADDR, 0x00, 0x00)  # IODIRA (Port A to Output)
bus.write_byte_data(EXPANDER_ADDR, 0x01, 0x00)  # IODIRB (Port B to Output)

def clear_matrix():
    # Forces all 16 relays into an absolute isolated open state
    bus.write_byte_data(EXPANDER_ADDR, 0x12, 0x00)  # GPIOA
    bus.write_byte_data(EXPANDER_ADDR, 0x13, 0x00)  # GPIOB

def switch_relay_pair(pin_x, pin_y):
    # Generates a 16-bit mask to close exactly two target relays
    mask = (1 << (pin_x - 1)) | (1 << (pin_y - 1))
    byte_A = mask & 0xFF
    byte_B = (mask >> 8) & 0xFF
    bus.write_byte_data(EXPANDER_ADDR, 0x12, byte_A)
    bus.write_byte_data(EXPANDER_ADDR, 0x13, byte_B)

def run_survey():
    try:
        db = mysql.connector.connect(
            host=LAPTOP_IP,
            user="manech_user",
            password="YourStrongSecurePassword",
            database="manech_ert_db"
        )
        cursor = db.cursor()
        
        cursor.execute("""
            INSERT INTO survey_profiles (profile_name, electrode_spacing_meters, total_electrodes) 
            VALUES ('wenner_profile_01', %s, 16)
        """, (ELECTRODE_SPACING,))
        profile_id = cursor.lastrowid
        db.commit()
        print(f"Connected to Database. Active Survey ID: {profile_id}")
        
        wenner_sequence = [
            {"step": 1, "a": 1, "b": 4, "m": 2, "n": 3},
            {"step": 2, "a": 2, "b": 5, "m": 3, "n": 4},
            {"step": 3, "a": 3, "b": 6, "m": 4, "n": 5},
            {"step": 4, "a": 4, "b": 7, "m": 5, "n": 6},
            # Sequence automatically proceeds through remaining nodes...
        ]
        
        for q in wenner_sequence:
            print(f"Step {q['step']} -> A:{q['a']} B:{q['b']} | M:{q['m']} N:{q['n']}")
            
            # PHASE 1: ENERGIZATION
            switch_relay_pair(q['a'], q['b'])
            time.sleep(0.4)
            
            v_shunt_drop = AnalogIn(adc, ADS.P2, ADS.P3).voltage
            i_injected = v_shunt_drop / R_SHUNT
            
            # PHASE 2: VOLTAGE MEASUREMENT
            clear_matrix()
            time.sleep(0.05)
            
            switch_relay_pair(q['m'], q['n'])
            time.sleep(0.2)
            
            v_subsurface = AnalogIn(adc, ADS.P0, ADS.P1).voltage
            
            # PHASE 3: COMPUTATION
            clear_matrix()
            
            if i_injected > 0:
                resistance = v_subsurface / i_injected
                k_factor = 2 * 3.14159265 * ELECTRODE_SPACING
                rho_apparent = resistance * k_factor
                
                sql = """
                    INSERT INTO ert_measurements 
                    (survey_profile_id, sequence_index, electrode_a, electrode_b, electrode_m, electrode_n, voltage_volts, current_amps, apparent_resistivity_ohmm) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (profile_id, q['step'], q['a'], q['b'], q['m'], q['n'], v_subsurface, i_injected, rho_apparent)
                cursor.execute(sql, values)
                db.commit()
                print(f" -> Saved: {rho_apparent:.2f} Ohm-m")
            else:
                print(f" -> Step {q['step']} Skipped: No injection current.")
                
            time.sleep(0.1)
            
        cursor.close()
        db.close()
        print("ERT Scan Sequence Completed.")

    except mysql.connector.Error as err:
        print(f"Database network failure: {err}")
    finally:
        clear_matrix()

if __name__ == '__main__':
    run_survey()

```