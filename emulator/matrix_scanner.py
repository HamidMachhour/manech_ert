#!/usr/bin/env python3
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
        return False

def simulate_earth_physics(xa, xb, xm, xn):
    """
    Simulates subsurface resistivity based on pseudo-location and depth.
    Used ONLY when physical hardware is entirely absent.
    """
    center_x = (xa + xb + xm + xn) / 4.0
    pseudo_depth = abs(xb - xa) * 0.195  
    
    base_resistivity = 150.0 
    
    if pseudo_depth > 2.0:
        return 15.0 + random.gauss(0, 0.5) 
        
    if 5.0 < center_x < 10.0 and 0.5 < pseudo_depth < 1.5:
        return 8.0 + random.gauss(0, 0.2)
        
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

        # Nested loop running the Wenner profile sequence
        for a in range(1, 6): # Spacing multipliers: 1x, 2x, 3x, 4x, 5x spacing
            for i in range(1, 17):
                stake_a = i
                stake_m = i + a
                stake_n = i + 2 * a
                stake_b = i + 3 * a
                
                if stake_b > 16:
                    break

                # --- SÉQUENCEMENT PHYSIQUE DE L'INJECTION ET DE LA MESURE ---
                if matrix_controller is not None:
                    # 1. Activation de la ligne de puissance (A, B) et attente de stabilisation de la source
                    matrix_controller.activate_injection_quad(stake_a, stake_b)
                    time.sleep(0.1) 
                    
                    # 2. Ouverture des lignes de lecture du potentiel (M, N) et stabilisation des relais
                    matrix_controller.activate_measurement_quad(stake_m, stake_n)
                    time.sleep(0.1) 
                else:
                    print(f"[SIM] Activating injection relays for electrodes {stake_a} and {stake_b}")
                    print(f"[SIM] Activating measurement relays for electrodes {stake_m} and {stake_n}")
                    time.sleep(0.2)

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

                # --- LECTURE ET TRAITEMENT DES DONNÉES ---
                if matrix_controller is not None:
                    # Lecture directe depuis l'ADS1115
                    voltage_volts, current_ma = matrix_controller.read_adc()
                    
                    # Remplacement des valeurs None par 0.0 en cas d'erreur de communication I2C ponctuelle
                    if voltage_volts is None: voltage_volts = 0.0
                    if current_ma is None: current_ma = 0.0

                    voltage = voltage_volts
                    current = current_ma / 1000.0  # Conversion mA en Ampères pour la loi d'Ohm

                    # Formule Wenner : rho = 2 * pi * a * V / I
                    # Seuil minimal de sécurité pour éviter la division par zéro (bruit de fond à vide)
                    if abs(current) > 1e-6:
                        rho = (2 * 3.141592653589793 * spacing * voltage) / current
                    else:
                        rho = 0.0
                else:
                    # MODE HORS-LIGNE COMPLET : Utilisation de la simulation physique
                    xa = stake_a * spacing
                    xb = stake_b * spacing
                    xm = stake_m * spacing
                    xn = stake_n * spacing
                    
                    rho = simulate_earth_physics(xa, xb, xm, xn)
                    current = (1.0 + random.uniform(-0.005, 0.005)) * 0.1  # ~100mA simulés
                    voltage = (rho * current) / (2 * 3.141592653589793 * spacing)

                # Ajout de la ligne au lot en cours
                batch_data.append((scan_id, stake_a, stake_b, stake_m, stake_n, voltage, current, rho))
                
                if len(batch_data) >= BATCH_SIZE:
                    cursor.executemany("""
                        INSERT INTO matrix_points (scan_id, stake_a, stake_b, stake_m, stake_n, measured_voltage, injected_current, calculated_apparent_resistivity)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, batch_data)
                    db.commit()
                    batch_data = []
                    print(f"Wenner Bound Committed: A:{stake_a} M:{stake_m} N:{stake_n} B:{stake_b} | Rho: {rho:.2f} Ohm.m (I: {current*1000:.1f} mA, V: {voltage:.4f} V)")

        # Validation finale des points restants
        if batch_data:
            cursor.executemany("""
                INSERT INTO matrix_points (scan_id, stake_a, stake_b, stake_m, stake_n, measured_voltage, injected_current, calculated_apparent_resistivity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, batch_data)
            db.commit()

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
    parser = argparse.ArgumentParser(description="ERT Hardware Profiler")
    parser.add_argument("--scan_id", type=int, required=True, help="ID of the scan to execute")
    parser.add_argument("--spacing", type=float, required=True, help="Electrode spacing in meters")
    
    args = parser.parse_args()
    run_scanner(args.scan_id, args.spacing)