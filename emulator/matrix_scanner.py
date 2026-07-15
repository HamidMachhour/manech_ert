import os
import sqlite3
import argparse
import time
import random
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

try:
    from ert_matrix_controller import ErtMatrixController
except ImportError:
    ErtMatrixController = None

def get_db_connection():
    """
    Establishes a connection to an SQLite database file.
    """
    db_path = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'database', 'database.sqlite'))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        connection = sqlite3.connect(db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection
    except sqlite3.Error as err:
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
        return 15.0 + random.gauss(0, 0.5) # Low resistivity for water table
        
    # Simulate an isolated wet clay anomaly at a specific horizontal point
    if 5.0 < center_x < 10.0 and 0.5 < pseudo_depth < 1.5:
        return 8.0 + random.gauss(0, 0.2)
        
    # Return standard soil with minor natural field noise
    return base_resistivity + random.gauss(0, 2.0)


def run_scanner(scan_id, spacing):
    db = get_db_connection()
    cursor = db.cursor()

    print(f"Starting scan {scan_id} with spacing {spacing}m...")

    # Verify scan exists to avoid Foreign Key errors
    cursor.execute("SELECT id FROM scans WHERE id = ?", (scan_id,))
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
        matrix_controller = None
        if ErtMatrixController is not None:
            try:
                matrix_controller = ErtMatrixController(i2c_bus_id=0, mcp_address=0x20)
            except Exception as e:
                print(f"Warning: Failed to initialize ERT matrix controller: {e}")
                matrix_controller = None

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

                # Activate the injection quad for this electrode set
                if matrix_controller is not None:
                    matrix_controller.activate_injection_quad(stake_a, stake_b)
                else:
                    print(f"[SIM] Activating injection relays for electrodes {stake_a} and {stake_b}")

                # --- CRITICAL FAIL-SAFE CHECK ---
                if check_kill_signal():
                    print("!!! EMERGENCY ABORT SIGNAL DETECTED !!!")
                    if batch_data:
                        cursor.executemany(
                            """
                            INSERT INTO matrix_points (scan_id, stake_a, stake_b, stake_m, stake_n, measured_voltage, injected_current, calculated_apparent_resistivity)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            batch_data
                        )
                        db.commit()
                    cursor.execute("UPDATE scans SET status = 'aborted' WHERE id = ?", (scan_id,))
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
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, batch_data)
                    db.commit()
                    batch_data = []
                    print(f"Wenner Bound Committed: A:{stake_a} M:{stake_m} N:{stake_n} B:{stake_b} | Rho: {rho:.2f}")

        # Final commit for any remaining data in the batch
        if batch_data:
            cursor.executemany("""
                INSERT INTO matrix_points (scan_id, stake_a, stake_b, stake_m, stake_n, measured_voltage, injected_current, calculated_apparent_resistivity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, batch_data)
            db.commit()

        # Mark scan as completed if loop finishes naturally
        cursor.execute("UPDATE scans SET status = 'completed' WHERE id = ?", (scan_id,))
        db.commit()
        print("Scan completed successfully.")

    except Exception as e:
        print(f"Runtime Error: {e}")
        cursor.execute("UPDATE scans SET status = 'aborted' WHERE id = ?", (scan_id,))
        db.commit()
    finally:
        if 'matrix_controller' in locals() and matrix_controller is not None:
            matrix_controller.close()
        cursor.close()
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ERT Hardware Emulator")
    parser.add_argument("--scan_id", type=int, required=True, help="ID of the scan to execute")
    parser.add_argument("--spacing", type=float, required=True, help="Electrode spacing in meters")
    
    args = parser.parse_args()
    run_scanner(args.scan_id, args.spacing)
