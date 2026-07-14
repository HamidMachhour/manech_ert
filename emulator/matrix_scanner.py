import os
import mysql.connector
import argparse
import time
import random
import sys
import numpy as np

try:
    from smbus2 import SMBus
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False


class MCP23017RelayController:
    # MCP23017 registers
    IODIRA = 0x00
    IODIRB = 0x01
    OLATA = 0x14
    OLATB = 0x15

    def __init__(self, bus_number=1, address=0x20, active_high=True):
        if not SMBUS_AVAILABLE:
            raise RuntimeError("smbus2 is required for MCP23017 relay control")

        self.address = address
        self.active_high = active_high
        self.bus = SMBus(bus_number)
        self._init_chip()

    def _init_chip(self):
        # Configure all 16 pins as outputs
        self.bus.write_byte_data(self.address, self.IODIRA, 0x00)
        self.bus.write_byte_data(self.address, self.IODIRB, 0x00)
        self.deactivate_all()

    def write_register(self, register, value):
        self.bus.write_byte_data(self.address, register, value & 0xFF)

    def set_port_a(self, value):
        self.write_register(self.OLATA, value)

    def set_port_b(self, value):
        self.write_register(self.OLATB, value)

    def set_relays(self, relay_indices):
        port_a = 0
        port_b = 0

        for relay in relay_indices:
            if relay < 1 or relay > 16:
                continue
            index = relay - 1
            if index < 8:
                port_a |= 1 << index
            else:
                port_b |= 1 << (index - 8)

        if not self.active_high:
            port_a ^= 0xFF
            port_b ^= 0xFF

        self.set_port_a(port_a)
        self.set_port_b(port_b)

    def deactivate_all(self):
        off_value = 0x00 if self.active_high else 0xFF
        self.set_port_a(off_value)
        self.set_port_b(off_value)

    def close(self):
        try:
            self.deactivate_all()
        except Exception:
            pass
        finally:
            self.bus.close()


def get_db_connection():
    """
    Establishes a connection to the MySQL database.
    In a real production environment, these would be loaded from environment variables.
    """
    try:
        return mysql.connector.connect(
            host="127.0.0.1",
            user="ert_user",
            password="12341234",
            database="ert_station"
        )
    except mysql.connector.Error as err:
        print(f"Database Connection Error: {err}")
        sys.exit(1)
 
def check_kill_signal():
    """
    Checks the shared memory abort flag file.
    """
    shm_path = '/dev/shm/scan_aborted'
    if not os.path.exists(shm_path):
        return False

    try:
        with open(shm_path, 'r') as f:
            contents = f.read().strip()
            return contents == '1'
    except Exception:
        # If the file cannot be read for any reason, treat as no abort signal
        return False

def simulate_earth_physics(xa, xb, xm, xn):
    """
    Simulates subsurface resistivity based on pseudo-location and depth.
    """
    # Calculate approximate pseudo-location and pseudo-depth of the current reading
    center_x = (xa + xb + xm + xn) / 4.0
    pseudo_depth = abs(xb - xa) * 0.195  # Standard geometric depth approximation
    
    # Base background soil resistivity (Dry upper layer)
    base_resistivity = 150.0 
    
    # Simulate a high-conductivity water-saturated aquifer starting at 2 meters deep
    if pseudo_depth > 2.0:
        return 15.0 + np.random.normal(0, 0.5) # Low resistivity for water table
        
    # Simulate an isolated wet clay anomaly at a specific horizontal point
    if 5.0 < center_x < 10.0 and 0.5 < pseudo_depth < 1.5:
        return 8.0 + np.random.normal(0, 0.2)
        
    # Return standard soil with minor natural field noise
    return base_resistivity + np.random.normal(0, 2.0)

def simulate_measurement(spacing):
    """
    Simulates a voltage drop and current injection based on synthetic earth physics.
    """
    # Get the target apparent resistivity from the physics model
    # Note: In the current emulator, we don't have the electrode indices here, 
    # so we'll pass them from the run_scanner loop.
    # For now, we'll return a base value and let run_scanner handle the physics.
    return 100.0, 1.0, 100.0

def run_scanner(scan_id, spacing):
    db = get_db_connection()
    cursor = db.cursor()

    print(f"Starting scan {scan_id} with spacing {spacing}m...")

    # Verify scan exists to avoid Foreign Key errors
    cursor.execute("SELECT id FROM scans WHERE id = %s", (scan_id,))
    if not cursor.fetchone():
        print(f"Error: Scan ID {scan_id} not found in database. Exiting.")
        cursor.close()
        db.close()
        return

    # Simulate 16 electrodes
    electrodes = range(1, 17) # For testing, we use 4 electrodes to keep the output manageable
    batch_data = []
    BATCH_SIZE = 50
    
    try:
        relay_controller = None
        if SMBUS_AVAILABLE:
            try:
                relay_controller = MCP23017RelayController(bus_number=1, address=0x20, active_high=True)
            except Exception as e:
                print(f"Warning: Failed to initialize MCP23017 relay controller: {e}")
                relay_controller = None

        # Nested loop simulating the switching matrix
        # A, B: Current electrodes | M, N: Potential electrodes
        for a in range(1, 6): # Spacing multipliers: 1x, 2x, 3x, 4x, 5x spacing
            for i in range(1, 17):
                # Calculate the 4 exact stake positions for a Wenner sequence
                stake_a = i
                stake_m = i + a
                stake_n = i + 2 * a
                stake_b = i + 3 * a
                
                # If the outermost stake exceeds your 16 physical electrodes, stop this line line sweep
                if stake_b > 16:
                    break

                # Activate the relays for this electrode set
                if relay_controller is not None:
                    active_relays = [stake_a, stake_b]
                    relay_controller.set_relays(active_relays)

                # --- CRITICAL FAIL-SAFE CHECK ---
                if check_kill_signal():
                    print("!!! EMERGENCY ABORT SIGNAL DETECTED !!!")
                    if batch_data:
                        cursor.executemany("INSERT INTO matrix_points ...", batch_data)
                        db.commit()
                    cursor.execute("UPDATE scans SET status = 'aborted' WHERE id = %s", (scan_id,))
                    db.commit()
                    return

                # Simulate hardware relay latency bounce
                time.sleep(0.1)

                # Convert hardware electrode pin numbers to true spatial metrics (meters)
                xa = stake_a * spacing
                xb = stake_b * spacing
                xm = stake_m * spacing
                xn = stake_n * spacing
                
                # Pass coordinates to your physics simulator engine
                rho = simulate_earth_physics(xa, xb, xm, xn)

                # Derive consistent V and I values
                current = 1.0 + random.uniform(-0.005, 0.005)
                voltage = rho * current * 0.1 

                # Append to active batch
                batch_data.append((scan_id, stake_a, stake_b, stake_m, stake_n, voltage, current, rho))
                
                if len(batch_data) >= BATCH_SIZE:
                    cursor.executemany("""
                        INSERT INTO matrix_points (scan_id, stake_a, stake_b, stake_m, stake_n, measured_voltage, injected_current, calculated_apparent_resistivity)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, batch_data)
                    db.commit()
                    batch_data = []
                    print(f"Wenner Bound Committed: A:{stake_a} M:{stake_m} N:{stake_n} B:{stake_b} | Rho: {rho:.2f}")

        # Final commit for any remaining data in the batch
        if batch_data:
            cursor.executemany("""
                INSERT INTO matrix_points (scan_id, stake_a, stake_b, stake_m, stake_n, measured_voltage, injected_current, calculated_apparent_resistivity)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, batch_data)
            db.commit()

        # Mark scan as completed if loop finishes naturally
        cursor.execute("UPDATE scans SET status = 'completed' WHERE id = %s", (scan_id,))
        db.commit()
        print("Scan completed successfully.")

    except Exception as e:
        print(f"Runtime Error: {e}")
        cursor.execute("UPDATE scans SET status = 'aborted' WHERE id = %s", (scan_id,))
        db.commit()
    finally:
        if 'relay_controller' in locals() and relay_controller is not None:
            relay_controller.close()
        cursor.close()
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ERT Hardware Emulator")
    parser.add_argument("--scan_id", type=int, required=True, help="ID of the scan to execute")
    parser.add_argument("--spacing", type=float, required=True, help="Electrode spacing in meters")
    
    args = parser.parse_args()
    run_scanner(args.scan_id, args.spacing)
