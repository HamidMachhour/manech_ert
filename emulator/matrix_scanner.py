#!/usr/bin/env python3
import os
import sqlite3
import argparse
import time
import random
import sys
import math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

try:
    from ert_matrix_controller import ErtMatrixController
except ImportError:
    ErtMatrixController = None

def get_db_connection():
    db_path = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'database', 'database.sqlite'))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    try:
        connection = sqlite3.connect(db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection
    except sqlite3.Error as err:
        print(f"Erreur de connexion à la base de données : {err}")
        sys.exit(1)
 
def check_kill_signal():
    shm_path = '/dev/shm/scan_aborted'
    if not os.path.exists(shm_path):
        return False
    try:
        with open(shm_path, 'r') as f:
            return f.read().strip() == '1'
    except Exception:
        return False

def calculate_k_factor(i, l, k, j, spacing_a):
    """
    Calcule la constante géométrique K pour l'alignement alterné :
    A0-M0-N0-B0 - A1-M1-N1-B1 ...
    Positions absolues en unités de distance : A=4*idx, M=4*idx+1, N=4*idx+2, B=4*idx+3
    """
    pos_A = 4 * i
    pos_M = 4 * l + 1
    pos_N = 4 * k + 2
    pos_B = 4 * j + 3

    # Distances réelles en mètres
    r_AM = abs(pos_M - pos_A) * spacing_a
    r_BM = abs(pos_M - pos_B) * spacing_a
    r_AN = abs(pos_N - pos_A) * spacing_a
    r_BN = abs(pos_N - pos_B) * spacing_a

    try:
        terme_geometrique = (1.0 / r_AM) - (1.0 / r_BM) - (1.0 / r_AN) + (1.0 / r_BN)
        if abs(terme_geometrique) < 1e-9:
            return 0.0
        return (2 * math.pi) / abs(terme_geometrique)
    except ZeroDivisionError:
        return 0.0

def simulate_earth_physics(i, l, k, j, spacing_a):
    """Simulation de la résistivité pour les tests en mode déconnecté."""
    center_pos = (i + l + k + j) / 4.0
    pseudo_depth = abs(j - i) * 4 * spacing_a * 0.2
    base_resistivity = 150.0 
    
    if pseudo_depth > 0.15:
        return 25.0 + random.gauss(0, 0.5) 
    if 1.0 < center_pos < 2.5:
        return 12.0 + random.gauss(0, 0.2) # Zone humide simulée au centre
        
    return base_resistivity + random.gauss(0, 2.0)

def run_scanner(scan_id, spacing):
    db = get_db_connection()
    cursor = db.cursor()

    print(f"Démarrage du scan combinatoire {scan_id} avec un pas d'espacement de {spacing}m...")

    cursor.execute("SELECT id FROM scans WHERE id = ?", (scan_id,))
    if not cursor.fetchone():
        print(f"Erreur : Scan ID {scan_id} introuvable en base. Sortie.")
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
                print(f"Avertissement : Erreur d'initialisation matérielle : {e}")
                matrix_controller = None

        # Boucles d'exploration combinatoire basées sur vos indices de dipôles (0 à 3)
        # Condition géométrique stricte sur la ligne : i <= l <= k <= j
        for i in range(4):
            for l in range(4):
                for k in range(4):
                    for j in range(4):
                        if not (i <= l <= k <= j):
                            continue # Ignore les géométries inversées ou impossibles

                        # Calcul automatique du facteur K pour ce quadruplet
                        k_factor = calculate_k_factor(i, l, k, j, spacing)
                        if k_factor == 0.0:
                            continue

                        # Mappage des indices pour l'enregistrement en BDD (conserve la lisibilité)
                        stake_a = 4 * i + 1
                        stake_m = 4 * l + 2
                        stake_n = 4 * k + 3
                        stake_b = 4 * j + 4

                        # --- COMMUTATION DES RELAIS ---
                        if matrix_controller is not None:
                            # Activation globale des 4 lignes de bus
                            matrix_controller.activate_quad(i, l, k, j)
                            time.sleep(0.2) # Temps global de stabilisation de la source et des lignes
                        else:
                            print(f"[SIM] Activation combinatoire complète : A{i} M{l} N{k} B{j}")
                            time.sleep(0.1)

                        # --- SIGNAL D'ARRÊT D'URGENCE ---
                        if check_kill_signal():
                            print("!!! ARRET D'URGENCE DEMANDE PAR L'INTERFACE !!!")
                            if batch_data:
                                cursor.executemany("""
                                    INSERT INTO matrix_points (scan_id, stake_a, stake_b, stake_m, stake_n, measured_voltage, injected_current, calculated_apparent_resistivity)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, batch_data)
                                db.commit()
                            cursor.execute("UPDATE scans SET status = 'aborted' WHERE id = ?", (scan_id,))
                            db.commit()
                            return

                        # --- ACQUISITION ADC ---
                        if matrix_controller is not None:
                            voltage_volts, current_amperes = matrix_controller.read_adc()
                            
                            if voltage_volts is None: voltage_volts = 0.0
                            if current_amperes is None: current_amperes = 0.0

                            voltage = voltage_volts
                            current = current_amperes

                            # Calcul final de la résistivité apparente (rho = K * V / I)
                            if abs(current) > 1e-6:
                                rho = k_factor * (voltage / current)
                            else:
                                rho = 0.0
                        else:
                            # MODE SIMULATION MATÉRIELLE
                            rho = simulate_earth_physics(i, l, k, j, spacing)
                            current = 0.045 + random.uniform(-0.002, 0.002) # ~45mA simulés avec shunt 50 Ohms
                            voltage = (rho * current) / k_factor

                        # Archivage temporaire des données lues
                        batch_data.append((scan_id, stake_a, stake_b, stake_m, stake_n, voltage, current, rho))
                        
                        if len(batch_data) >= BATCH_SIZE:
                            cursor.executemany("""
                                INSERT INTO matrix_points (scan_id, stake_a, stake_b, stake_m, stake_n, measured_voltage, injected_current, calculated_apparent_resistivity)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, batch_data)
                            db.commit()
                            batch_data = []
                            print(f"Points sauvegardés - Index [{i},{l},{k},{j}] | K: {k_factor:.2f} | Rho: {rho:.2f} Ohm.m (I: {current*1000:.2f} mA, V: {voltage:.4f} V)")

        # Sauvegarde finale des données restantes
        if batch_data:
            cursor.executemany("""
                INSERT INTO matrix_points (scan_id, stake_a, stake_b, stake_m, stake_n, measured_voltage, injected_current, calculated_apparent_resistivity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, batch_data)
            db.commit()

        cursor.execute("UPDATE scans SET status = 'completed' WHERE id = ?", (scan_id,))
        db.commit()
        print("Scan profiler exécuté avec succès.")

    except Exception as e:
        print(f"Erreur d'exécution critique : {e}")
        cursor.execute("UPDATE scans SET status = 'aborted' WHERE id = ?", (scan_id,))
        db.commit()
    finally:
        if 'matrix_controller' in locals() and matrix_controller is not None:
            matrix_controller.close()
        cursor.close()
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ERT Multi-Profile Combinatorial Engine")
    parser.add_argument("--scan_id", type=int, required=True, help="ID du scan à exécuter")
    parser.add_argument("--spacing", type=float, required=True, help="Distance unitaire 'a' entre deux piquets en mètres")
    
    args = parser.parse_args()
    run_scanner(args.scan_id, args.spacing)