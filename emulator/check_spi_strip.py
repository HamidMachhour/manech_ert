#!/usr/bin/env python3
import time
import sys
import spidev

def send_to_strip(spi, led_list):
    """Translates Python RGB list into WS2812B timing bytes over SPI."""
    spi_data = []
    for rgb in led_list:
        r, g, b = rgb[0], rgb[1], rgb[2]
        for byte in (g, r, b):
            for bit in range(8):
                if (byte >> (7 - bit)) & 1:
                    spi_data.append(0b11110000)
                else:
                    spi_data.append(0b11000000)
    spi.xfer2(spi_data)

def clear_strip(spi, led_count=16):
    """Explicitly forces all pixels to black to reset the shift registers."""
    blank_list = [[0, 0, 0] for _ in range(led_count)]
    send_to_strip(spi, blank_list)

def main():
    print("==================================================")
    print("   WS2812B Addressable LED Strip SPI Tester       ")
    print("==================================================")
    
    try:
        spi = spidev.SpiDev()
        spi.open(0, 0)
        spi.max_speed_hz = 6400000
        print(" -> [OK] SPI Bus 0.0 opened successfully.")
    except Exception as e:
        print(f" -> [ERROR] Could not access SPI bus: {e}")
        sys.exit(1)

    LED_COUNT = 16
    
    # Force a clean hardware clear right at boot to remove any sticky green pixels
    print(" -> Flushing strip state cleanly...")
    clear_strip(spi, LED_COUNT)
    time.sleep(0.2)

    print(f" -> Starting diagnostic cycle for {LED_COUNT} pixels...")
    try:
        while True:
            print(" -> Illuminating: RED")
            red_test = [[255, 0, 0] for _ in range(LED_COUNT)]
            send_to_strip(spi, red_test)
            time.sleep(1.5)

            print(" -> Illuminating: GREEN")
            green_test = [[0, 255, 0] for _ in range(LED_COUNT)]
            send_to_strip(spi, green_test)
            time.sleep(1.5)

            print(" -> Running Light Chaser Sequence...")
            for i in range(LED_COUNT):
                chaser_list = [[0, 0, 0] for _ in range(LED_COUNT)]
                chaser_list[i] = [0, 0, 255]  # Blue node
                send_to_strip(spi, chaser_list)
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print("\n -> Diagnostics interrupted by user.")
    finally:
        print(" -> Shutting down lighting element arrays gracefully.")
        clear_strip(spi, LED_COUNT)  # Clear before exit
        spi.close()
        print(" -> [FINISHED] Test footprint decoupled.")

if __name__ == "__main__":
    main()
