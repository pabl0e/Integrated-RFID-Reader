import serial
import os
import sys
from longrange_db_module import check_uid
import time
from subprocess import Popen 
from display_gui import CarInfoDisplay
from longrange_db_module import fetch_info

# Check if the platform supports RPi.GPIO (only on Raspberry Pi)
def import_gpio():
    try:
        import RPi.GPIO as GPIO
        print("RPi.GPIO module successfully imported.")
        return GPIO
    except ModuleNotFoundError:
        print("RPi.GPIO module not available on non-Raspberry Pi system.")
        return None

# Call the function to conditionally import RPi.GPIO

    
# --- Serial Port Configuration ---
# Based on "FM-503 command format.pdf":
# Baud Rate: 38400 (default)
# Data Bits: 8 bit
# Stop Bits: 1 bit
# Parity Bit: none

def run_rfid_read(display):
    GPIO = import_gpio()  # This is where the import happens
    last_read = None
    last_data = None
    last_payload = None
    try:
        ser = serial.Serial(
            port='/dev/ttyUSB0',
            #port='/dev/serial0',  # Ensure this is the correct serial port
            baudrate=38400,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
        )
        print(f"Successfully opened serial port {ser.port} at {ser.baudrate} baud.")

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        print("Please ensure the RFID reader is connected, the port name is correct, and user permissions (e.g., 'dialout' group) are set.")
        sys.exit(1)

    print("Waiting for RFID tag...")

    # --- FM503 Command Definitions ---
    COMMAND_GET_VERSION = b'\x0A' + b'V' + b'\x0D'
    COMMAND_GET_READER_ID = b'\x0A' + b'S' + b'\x0D'
    COMMAND_SINGLE_TAG_EPC = b'\x0A' + b'Q' + b'\x0D'
    COMMAND_MULTI_TAG_EPC = b'\x0A' + b'U' + b'\x0D'

    # --- Main Loop for RFID Reading ---
    while True:
        try:
            ser.flushInput()

            print(f"\nSending Multi-TAG read EPC command (U): {COMMAND_MULTI_TAG_EPC.hex()}")
            ser.write(COMMAND_MULTI_TAG_EPC)
            time.sleep(0.1)

            response_data = ser.read(ser.inWaiting())

            if response_data:
                raw_response = response_data.hex()
                print(f"Received raw response:v", raw_response)

                if len(response_data) >= 4 and \
                   response_data[0] == 0x0A and \
                   response_data[1] == ord('U') and \
                   response_data[-2:] == b'\x0D\x0A':

                    epc_data_bytes = response_data[2:-2]

                    if epc_data_bytes:
                        try:
                            tag_id = epc_data_bytes.decode('ascii').strip()

                            if raw_response == "0a550d0a":
                                print("No tag detected in RF field.")
                                if last_payload:
                                    display.root.after(0, display.update_car_info, last_payload['data'], last_payload.get('photo'))
                            else:
                                pc = tag_id[0:4]
                                actual_epc = tag_id[4:-4]
                                crc16 = tag_id[-4:]
                                print(f"Detected EPC: {actual_epc}")
                                
                                if actual_epc != last_read: 
                                    last_read = actual_epc
                                    payload = check_uid(actual_epc, display)  # may return {'data':..., 'photo':...} or just new_data
                                    # normalize to a consistent structure and keep old last_data for backward compatibility
                                    if isinstance(payload, dict) and 'data' in payload:
                                        last_payload = payload
                                    else:
                                        last_payload = {'data': payload, 'photo': None}
                                    last_data = last_payload['data']  # keep your old variable usable
                                else:
                                    print("Skipping duplicate")
                                    if last_payload:
                                        display.root.after(0, display.update_car_info, last_payload['data'], last_payload.get('photo'))

                        except UnicodeDecodeError:
                            print("Error decoding EPC data. It might not be ASCII hex characters as expected.")
                    else:
                        print("Received 'U' response with no data (likely 'none' for no tag).")
                        if last_payload:
                            display.root.after(0, display.update_car_info, last_payload['data'], last_payload.get('photo'))
                else:
                    print("Received unexpected response format for 'U' command.")
            else:
                print("No response received from reader within timeout.")

            time.sleep(1.5)

        except serial.SerialException as e:
            print(f"Serial communication error: {e}")
            print("Attempting to close and re-open serial port...")
            ser.close()
            time.sleep(5)
            try:
                ser.open()
                print("Serial port re-opened successfully.")
            except serial.SerialException as e_reopen:
                print(f"Failed to re-open serial port: {e_reopen}")
                print("Exiting script due to persistent serial port issues.")
                sys.exit(1)

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            sys.exit(1)

