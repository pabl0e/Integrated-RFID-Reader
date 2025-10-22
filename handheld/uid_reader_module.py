from handheld_db_module import add_new_uid
import serial
import os
import sys
import time
from subprocess import Popen 
import time


'''Python Scripts for the UID Reader Module'''

def main():
    """Main function to run the application"""
    run_rfid_read()

def import_gpio():
    try:
        import RPi.GPIO as GPIO
        print("RPi.GPIO module successfully imported.")
        return GPIO
    except ModuleNotFoundError:
        print("RPi.GPIO module not available on non-Raspberry Pi system.")
        return None
    
def run_rfid_read():
    GPIO = import_gpio()  # This is where the import happens
    last_read = None
    last_data = None
    last_payload = None
    try:
        ser = serial.Serial(
            #port='/dev/ttyUSB0',
            port='/dev/serial0',  # Ensure this is the correct serial port
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
                            else:
                                pc = tag_id[0:4]
                                actual_epc = tag_id[4:-4]
                                crc16 = tag_id[-4:]
                                print(f"Detected EPC: {actual_epc}")
                                try:
                                    result = add_new_uid(actual_epc)
                                except Exception as e:
                                    print(f"Exception while registering UID: {e}")
                                    result = {'success': False, 'message': str(e), 'new_uid': False}

                                # Print detailed result so we can diagnose DB errors on the Pi
                                if isinstance(result, dict):
                                    if result.get('success'):
                                        if result.get('new_uid'):
                                            print(f"New UID registered: {actual_epc}")
                                        else:
                                            print(f"UID already exists in DB: {actual_epc}")
                                    else:
                                        print(f"Failed to register UID: {result.get('message')}")
                                        # Optional fallback: write UID to a local file for later processing
                                        try:
                                            os.makedirs('pending_uids', exist_ok=True)
                                            with open(os.path.join('pending_uids', f"{actual_epc}.txt"), 'w') as f:
                                                f.write(result.get('message') or 'db_failure')
                                            print('Saved UID to pending_uids for later sync')
                                        except Exception as file_err:
                                            print(f'Could not write fallback UID file: {file_err}')
                                else:
                                    print(f"add_new_uid returned unexpected value: {result}")

                        except UnicodeDecodeError:
                            print("Error decoding EPC data. It might not be ASCII hex characters as expected.")
                    else:
                        print("Received 'U' response with no data (likely 'none' for no tag).")
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
                print("Serial port reopened successfully.")
            except serial.SerialException as e_reopen:
                print(f"Failed to reopen serial port: {e_reopen}")
                sys.exit(1)

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            sys.exit(1)

# UID insertion is handled by handheld_db_module.add_new_uid

if __name__ == "__main__":
    main()