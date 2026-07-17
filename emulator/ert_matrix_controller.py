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
    Manages a 16-Electrode ERT Switch Matrix using an MCP23017 I/O expander
    and synchronizes a 16-LED WS2812B strip using raw spidev native byte-arrays.
    """
    
    # MCP23017 Register Addresses
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
        
        # 1. Initialize SMBus2 for MCP23017
        last_i2c_error = None
        validated_bus_id = i2c_bus_id

        for bus_id in [i2c_bus_id, 1, 0]:
            try:
                self.bus = smbus2.SMBus(bus_id)
                
                # Configure tous les pins du Port A et B en SORTIES (0 = Output)
                self.bus.write_byte_data(self.mcp_address, self.IODIRA, 0x00)
                self.bus.write_byte_data(self.mcp_address, self.IODIRB, 0x00)
                
                self.hardware_present = True
                validated_bus_id = bus_id
                print(f" -> [OK] Physical MCP23017 detected and initialized on I2C bus {bus_id}.")
                break
            except Exception as exc:
                last_i2c_error = exc
                print(f" -> [WARN] I2C bus {bus_id} unavailable: {exc}")

        if not self.hardware_present:
            print(f" -> [SIMULATION] No physical I2C device found. Running in offline test mode. Last error: {last_i2c_error}")
        else:
            try:
                if ADS1115_MODULE is not None:
                    # Utilise le bus_id validé dynamiquement lors de la boucle précédente
                    self.adc = ADS1115_MODULE(address=0x48, busnum=validated_bus_id)
                    self.adc_present = True
                    print(f" -> [OK] ADS1115 ADC detected and initialized on the shared I2C bus {validated_bus_id}.")
                else:
                    print(" -> [WARN] ADS1115 Python library is not available; ADC readings will be simulated.")
            except Exception as exc:
                self.adc_present = False
                print(f" -> [WARN] ADS1115 initialization failed: {exc}")
        
        # 2. Initialize Hardware SPI via spidev for WS2812B
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)
            self.spi.max_speed_hz = 6400000
            self.spi_present = True
            print(" -> [OK] Hardware SPI bus successfully mapped.")
        except Exception:
            self.spi_present = False
            print(" -> [SIMULATION] SPI Bus not accessible. Simulating LED outputs.")
        
        # 3. Create a plain Python list for tracking colors
        self.led_list = [[0, 0, 0] for _ in range(self.led_count)]
        
        # 4. Initial system flush
        self.clear_all()

    def _send_to_led_strip(self):
        """Translates color list into raw SPI pulses if hardware is online."""
        if not self.spi_present:
            print(f"    [SIM LIGHTS] Active LED Color Map: {self.led_list}")
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
            print(f" -> SPI write execution failure: {e}")

    def clear_strip(self):
        """Dedicated function to turn off all pixels on the LED strip."""
        self.led_list = [[0, 0, 0] for _ in range(self.led_count)]
        self._send_to_led_strip()

    def clear_all(self):
        """Safely deactivates all relays and clears the LED strip."""
        self.clear_strip()

        if self.hardware_present:
            try:
                self.bus.write_byte_data(self.mcp_address, self.GPIOA, 0x00)
                self.bus.write_byte_data(self.mcp_address, self.GPIOB, 0x00)
            except OSError as e:
                print(f" -> Hardware connection lost during clear operation: {e}")
        else:
            print("    [SIM HARDWARE] Matrix Open Isolation: All 16 relay pins forced LOW (0x00).")

    def _write_to_relays(self, combined_16bit_word):
        """Writes a 16-bit word to the MCP23017 GPIO registers directly."""
        if not self.hardware_present:
            print(f"    [SIM HARDWARE] Relay Register Word Sent: {combined_16bit_word:016b}")
            return

        byte_A = combined_16bit_word & 0xFF
        byte_B = (combined_16bit_word >> 8) & 0xFF

        try:
            self.bus.write_byte_data(self.mcp_address, self.GPIOA, byte_A)
            self.bus.write_byte_data(self.mcp_address, self.GPIOB, byte_B)
        except OSError as e:
            print(f" -> Hardware communication lost during write sequence: {e}")

    def _electrode_bitmask(self, elec: int) -> int:
        """
        Map a 1-based electrode number (1..16) to the combined 16-bit register
        word where GPIOA holds odd electrodes (1,3,5...) in bits 0..7 and
        GPIOB holds even electrodes (2,4,6...) in bits 8..15.
        """
        if elec < 1 or elec > 16:
            return 0

        if elec % 2 == 1:
            index = (elec - 1) // 2
            return 1 << index
        else:
            index = (elec // 2) - 1
            return 1 << (8 + index)

    def activate_injection_quad(self, elec_A, elec_B):
        """Sets LEDs (A, B) to RED, closes injection relays."""
        print(f"\n[Command] Activating Injection Quad on Electrodes A={elec_A}, B={elec_B}")
        self.clear_all()  
        time.sleep(0.01)  
        
        self.led_list[elec_A - 1] = [255, 0, 0]  # Red
        self.led_list[elec_B - 1] = [255, 0, 0]  
        self._send_to_led_strip()
        
        combined = self._electrode_bitmask(elec_A) | self._electrode_bitmask(elec_B)
        self._write_to_relays(combined)

    def activate_measurement_quad(self, elec_M, elec_N):
        """Sets LEDs (M, N) to GREEN, closes potential reading relays."""
        print(f"\n[Command] Activating Measurement Quad on Electrodes M={elec_M}, N={elec_N}")
        self.clear_all()  
        time.sleep(0.01)
        
        self.led_list[elec_M - 1] = [0, 255, 0]  # Green
        self.led_list[elec_N - 1] = [0, 255, 0]  
        self._send_to_led_strip()
        
        combined = self._electrode_bitmask(elec_M) | self._electrode_bitmask(elec_N)
        self._write_to_relays(combined)

    def read_adc(self):
        """Read the ADS1115 differential voltage channels and return current/voltage values."""
        if not self.adc_present or self.adc is None:
            return None, None

        try:
            # Gain=1 donne une plage de +/-4.096V. Le pas LSB est de 0.125 mV (0.000125V).
            # Index de l'ancienne lib Adafruit pour les mesures différentielles :
            # 0 = Différentiel entre A0 (positif) et A1 (négatif)
            # 3 = Différentiel entre A2 (positif) et A3 (négatif)
            voltage_raw = self.adc.read_adc_difference(0, gain=1)
            current_raw = self.adc.read_adc_difference(3, gain=1)

            # Conversion du signal brut en Volts physiques
            voltage_volts = voltage_raw * 0.000125
            current_volts = current_raw * 0.000125

            # Calcul de l'intensité passant par le shunt de 10 Ohms (U = R * I)
            shunt_resistance_ohms = 10.0
            current_ma = (current_volts / shunt_resistance_ohms) * 1000.0

            return voltage_volts, current_ma
        except Exception as exc:
            print(f" -> [WARN] ADS1115 read failed: {exc}")
            return None, None

    def close(self):
        self.clear_all()
        if self.hardware_present:
            self.bus.close()
        if self.spi_present:
            self.spi.close()
        print("\n -> [INFO] ERT Controller hardware instances safely released.")

if __name__ == "__main__":
    print("Testing Ultra-Lightweight Inline SPI Driver with ADS1115 Interface...")
    matrix = ErtMatrixController(i2c_bus_id=0, mcp_address=0x20)
    try:
        matrix.activate_injection_quad(1, 4)
        time.sleep(1.0)
        
        # Test de lecture des capteurs
        v, i = matrix.read_adc()
        if v is not None:
            print(f" -> Mesures lues : Tension = {v:.4f} V, Courant = {i:.2f} mA")
            
        matrix.activate_measurement_quad(2, 3)
        time.sleep(1.0)
    finally:
        matrix.close()