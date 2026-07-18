#!/usr/bin/env python3
import time
import smbus2
import spidev

try:
    import Adafruit_ADS1x15 as Adafruit_ADS1x15
    ADS1115_MODULE = Adafruit_ADS1x15.ADS1115
except Exception:
    ADS1115_MODULE = None

class ErtMatrixController:
    """
    Gère une matrice d'électrodes ERT à 16 piquets avec disposition alternée :
    A0-M0-N0-B0 - A1-M1-N1-B1 - A2-M2-N2-B2 - A3-M3-N3-B3
    Utilise un MCP23017 pour piloter les relais et un ruban de 16 LED WS2812B via SPI.
    """
    
    # Adresses des registres du MCP23017
    IODIRA = 0x00   
    IODIRB = 0x01   
    GPIOA  = 0x12   
    GPIOB  = 0x13   

    def __init__(self, i2c_bus_id=0, mcp_address=0x20, led_count=16):
        self.mcp_address = mcp_address
        self.led_count = led_count
        self.hardware_present = False
        self.spi_present = False
        self.bus = None
        self.adc = None
        self.adc_present = False
        
        # 1. Initialisation de l'I2C pour le MCP23017
        last_i2c_error = None
        validated_bus_id = i2c_bus_id

        for bus_id in [i2c_bus_id, 1, 0]:
            try:
                self.bus = smbus2.SMBus(bus_id)
                # Configuration de toutes les broches en sorties (0x00 = Output)
                self.bus.write_byte_data(self.mcp_address, self.IODIRA, 0x00)
                self.bus.write_byte_data(self.mcp_address, self.IODIRB, 0x00)
                self.hardware_present = True
                validated_bus_id = bus_id
                print(f" -> [OK] MCP23017 physique détecté et initialisé sur le bus I2C {bus_id}.")
                break
            except Exception as exc:
                last_i2c_error = exc
                print(f" -> [WARN] Bus I2C {bus_id} indisponible : {exc}")

        if not self.hardware_present:
            print(f" -> [SIMULATION] Aucun périphérique I2C physique détecté. Mode déconnecté. Dernier message : {last_i2c_error}")
        else:
            try:
                if ADS1115_MODULE is not None:
                    self.adc = ADS1115_MODULE(address=0x48, busnum=validated_bus_id)
                    self.adc_present = True
                    print(f" -> [OK] ADS1115 détecté et initialisé sur le bus partagé I2C {validated_bus_id}.")
                else:
                    print(" -> [WARN] Bibliothèque Adafruit_ADS1x15 manquante ; mesures simulées.")
            except Exception as exc:
                self.adc_present = False
                print(f" -> [WARN] Échec d'initialisation de l'ADS1115 : {exc}")
        
        # 2. Initialisation de l'interface SPI pour les LED WS2812B
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)
            self.spi.max_speed_hz = 6400000
            self.spi_present = True
            print(" -> [OK] Bus SPI matériel correctement mappé.")
        except Exception:
            self.spi_present = False
            print(" -> [SIMULATION] Bus SPI inaccessible. Animation LED simulée.")
        
        # 3. Initialisation de la table d'état des couleurs des LED
        self.led_list = [[0, 0, 0] for _ in range(self.led_count)]
        
        # 4. Extinction générale de sécurité au démarrage
        self.clear_all()

    def _send_to_led_strip(self):
        """Transmet l'état des couleurs au ruban de LED via le protocole SPI."""
        if not self.spi_present:
            return
            
        spi_data = []
        for rgb in self.led_list:
            r, g, b = rgb[0], rgb[1], rgb[2]
            for byte in (g, r, b):
                for bit in range(8):
                    if (byte >> (7 - bit)) & 1:
                        spi_data.append(0b11110000)
                    else:
                        spi_data.append(0b11000000)
        try:
            self.spi.xfer2(spi_data)
        except OSError as e:
            print(f" -> Échec de l'envoi SPI aux LED : {e}")

    def clear_strip(self):
        """Éteint le ruban de LED."""
        self.led_list = [[0, 0, 0] for _ in range(self.led_count)]
        self._send_to_led_strip()

    def clear_all(self):
        """Ouvre tous les relais (mise hors tension) et éteint les LED."""
        self.clear_strip()
        if self.hardware_present:
            try:
                self.bus.write_byte_data(self.mcp_address, self.GPIOA, 0x00)
                self.bus.write_byte_data(self.mcp_address, self.GPIOB, 0x00)
            except OSError as e:
                print(f" -> Perte de connexion matérielle lors de la coupure générale : {e}")
        else:
            print("    [SIM MATÉRIEL] Isolation complète : Les 16 broches de relais sont à l'état BAS (0x00).")

    def _write_to_relays(self, combined_16bit_word):
        """Envoie un mot de 16 bits directement aux registres du MCP23017."""
        if not self.hardware_present:
            print(f"    [SIM MATÉRIEL] Mot binaire appliqué aux relais : {combined_16bit_word:016b}")
            return

        byte_A = combined_16bit_word & 0xFF
        byte_B = (combined_16bit_word >> 8) & 0xFF

        try:
            self.bus.write_byte_data(self.mcp_address, self.GPIOA, byte_A)
            self.bus.write_byte_data(self.mcp_address, self.GPIOB, byte_B)
        except OSError as e:
            print(f" -> Erreur de communication I2C lors de l'écriture relais : {e}")

    def _get_absolute_pin(self, piquet_type, index) -> int:
            """
            Mappe les étiquettes des piquets vers le numéro de relais physique (1 à 16)
            selon la nouvelle distribution cyclique et disjointe :
            """
            if not (0 <= index <= 3):
                return 0

            if piquet_type == 'A':
                return 4 * index + 1   # A0=1, A1=5, A2=9, A3=13
            
            elif piquet_type == 'M':
                return 4 * index + 2   # M0=2, M1=6, M2=10, M3=14
            
            elif piquet_type == 'N':
                return 4 * index + 3   # N0=3, N1=7, N2=11, N3=15
            
            elif piquet_type == 'B':
                return 4 * index + 4   # B0=4, B1=8, B2=12, B3=16
                
            return 0

    def _electrode_bitmask(self, pin_number: int) -> int:
        """
        Génère le masque binaire 16 bits selon votre nouveau câblage linéaire direct :
        - Port A (PA0 -> PA7) contrôle les broches physiques 1 -> 8
        - Port B (PB0 -> PB7) contrôle les broches physiques 9 -> 16
        """
        if pin_number < 1 or pin_number > 16:
            return 0

        if pin_number <= 8:
            # Broches 1 à 8 sur le Port A (bits 0 à 7)
            # Broche 1 -> bit 0, Broche 8 -> bit 7
            bit_position = pin_number - 1
            return 1 << bit_position
        else:
            # Broches 9 à 16 sur le Port B (bits 8 à 15 du mot global 16 bits)
            # Broche 9 -> bit 8 (soit PB0), Broche 16 -> bit 15 (soit PB7)
            bit_position = (pin_number - 9) + 8
            return 1 << bit_position
            
    def activate_quad(self, idx_A, idx_M, idx_N, idx_B):
        """
        Active simultanément les 4 relais nécessaires à la mesure sans aucun risque de court-circuit
        grâce à la séparation physique des bus. Met à jour les LED (Rouge pour injection, Vert pour mesure).
        """
        pin_A = self._get_absolute_pin('A', idx_A)
        pin_M = self._get_absolute_pin('M', idx_M)
        pin_N = self._get_absolute_pin('N', idx_N)
        pin_B = self._get_absolute_pin('B', idx_B)

        print(f"[Commande] Activation des relais : A{idx_A}(Relais {pin_A}), M{idx_M}(Relais {pin_M}), N{idx_N}(Relais {pin_N}), B{idx_B}(Relais {pin_B})")
        
        self.clear_all()
        time.sleep(0.01)

        # Coloration du ruban de LED
        self.led_list[pin_A - 1] = [255, 0, 0]  # Rouge pour injection
        self.led_list[pin_B - 1] = [255, 0, 0]
        self.led_list[pin_M - 1] = [0, 255, 0]  # Vert pour mesure potentiel
        self.led_list[pin_N - 1] = [0, 255, 0]
        self._send_to_led_strip()

        # Construction et écriture du masque binaire
        combined = (self._electrode_bitmask(pin_A) | 
                    self._electrode_bitmask(pin_M) | 
                    self._electrode_bitmask(pin_N) | 
                    self._electrode_bitmask(pin_B))
        self._write_to_relays(combined)

    def read_adc(self):
        """
        Lit les tensions différentielles de l'ADS1115 (A0-A1 pour le sol, A2-A3 pour le shunt).
        Retourne : (tension_volts, courant_amperes)
        """
        if not self.adc_present or self.adc is None:
            return None, None

        try:
            # 1. Lecture de la tension différentielle V (M - N) sur le canal 0
            # Gain=1 permet une mesure jusqu'à +/-4.096V (LSB = 0.000125V)
            voltage_raw = self.adc.read_adc_difference(0, gain=1)
            voltage_volts = voltage_raw * 0.000125

            # 2. Lecture différentielle aux bornes de la résistance shunt sur le canal 3
            # Gain=16 est indispensable pour la résistance de 50 Ohms sous 5V (Plage maximale +/-0.256V, LSB = 0.0000078125V)
            current_raw = self.adc.read_adc_difference(3, gain=16)
            shunt_voltage_volts = current_raw * 0.0000078125

            # Calcul de l'intensité réelle (I = U / R) avec R_shunt = 50.0 Ohms
            shunt_resistance_ohms = 50.0
            current_amperes = shunt_voltage_volts / shunt_resistance_ohms

            return voltage_volts, current_amperes
        except Exception as exc:
            print(f" -> [WARN] Échec de scrutation de l'ADS1115 : {exc}")
            return None, None

    def close(self):
        self.clear_all()
        if self.hardware_present:
            self.bus.close()
        if self.spi_present:
            self.spi.close()
        print("\n -> [INFO] Ressources matérielles du contrôleur ERT libérées.")

if __name__ == "__main__":
    matrix = ErtMatrixController(i2c_bus_id=0, mcp_address=0x20)
    try:
        matrix.activate_quad(0, 1, 2, 3) # Test d'un quadruplet de piquets
        time.sleep(1.0)
        v, i = matrix.read_adc()
        if v is not None:
            print(f" -> Données lues : Tension = {v:.5f} V, Courant = {i*1000:.3f} mA")
    finally:
        matrix.close()