import serial
import os
import sys
from longrange_db_module import check_uid
import time
from subprocess import Popen 
from display_gui import CarInfoDisplay

def import_gpio():
    try:
        import RPi.GPIO as GPIO
        print("RPi.GPIO module successfully imported.")
        return GPIO
    except ModuleNotFoundError:
        print("RPi.GPIO module not available on non-Raspberry Pi system.")
        return None

def set_reader_power(ser):
    """
    Sets the reader's RF power to MAX (25 dBm / Hex '1B').
    """
    # Command to Write Power (25 dBm): <LF>N1,1B<CR>
    # 1B (hex) is the value for 25 dBm from the command doc
    COMMAND_SET_POWER = b'\x0A\x4E\x31\x2C\x31\x42\x0D' # <LF>N1,1B<CR>
    
    try:
        ser.flushInput()
        ser.write(COMMAND_SET_POWER)
        
        # --- CORRECTED LINE ---
        # The print statement should say 25 dBm
        print(f"Sending Set Max Power command (25 dBm): {COMMAND_SET_POWER.hex()}")
        time.sleep(0.1) # Give reader time to process
        response = ser.read(ser.inWaiting())
        
        # --- CORRECTED LINE ---
        # Check if response is the expected echo/OK <LF>N1B<CR><LF>
        # The hex for '1B' is \x31\x42
        if response == b'\x0A\x4E\x31\x42\x0D\x0A':
            print("Reader power successfully set to 25 dBm.")
        else:
            # This will now correctly show a warning if the response is wrong
            print(f"Warning: Unexpected response when setting power: {response.hex()}")
            
    except Exception as e:
        print(f"Error setting reader power: {e}")

def run_rfid_read(display):
    GPIO = import_gpio()
    last_read = None
    last_data = None
    last_payload = None
    
    try:
        ser = serial.Serial(
            port='/dev/serial0',
            baudrate=38400,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
        )
        print(f"Successfully opened serial port {ser.port} at {ser.baudrate} baud.")

        # --- SET READER POWER ON STARTUP ---
        set_reader_power(ser)
        # -----------------------------------

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        print("Please ensure the RFID reader is connected, the port name is correct, and user permissions are set.")
        sys.exit(1)

    print("Waiting for RFID tag...")

    COMMAND_SINGLE_TAG_EPC = b'\x0A' + b'Q' + b'\x0D'

    while True:
        try:
            ser.flushInput()

            # Using Single-Tag read, as per your original script
            ser.write(COMMAND_SINGLE_TAG_EPC)
            time.sleep(0.1)

            response_data = ser.read(ser.inWaiting())

            if response_data:
                raw_response = response_data.hex()
                # print(f"Received raw response: {raw_response}") # Uncomment for deep debugging

                if len(response_data) >= 4 and \
                   response_data[0] == 0x0A and \
                   response_data[1] == ord('Q') and \
                   response_data[-2:] == b'\x0D\x0A':

                    epc_data_bytes = response_data[2:-2]

                    if epc_data_bytes:
                        try:
                            tag_id = epc_data_bytes.decode('ascii').strip()

                            if raw_response == "0a510d0a": # 'Q' command with no tag
                                # print("No tag detected in RF field.") # Too noisy, comment out
                                if last_payload:
                                    # This will re-display the last valid read
                                    display.root.after(0, display.update_car_info, last_payload['data'], last_payload.get('photo'))
                            else:
                                pc = tag_id[0:4]
                                actual_epc = tag_id[4:-4]
                                crc16 = tag_id[-4:]
                                # print(f"Detected EPC: {actual_epc}") # Too noisy

                                if actual_epc != last_read: 
                                    print(f"NEW Tag Detected: {actual_epc}") # Log only new tags
                                    last_read = actual_epc
                                    # --- THIS IS THE SLOW PART WE ARE FIXING ---
                                    payload = check_uid(actual_epc, display)
                                    # -------------------------------------------
                                    if isinstance(payload, dict) and 'data' in payload:
                                        last_payload = payload
                                    else:
                                        last_payload = {'data': payload, 'photo': None}
                                    last_data = last_payload['data']
                                    
                                else:
                                    # print("Skipping duplicate") # Too noisy
                                    if last_payload:
                                        # Re-display last valid read if tag is held in field
                                        display.root.after(0, display.update_car_info, last_payload['data'], last_payload.get('photo'))

                        except UnicodeDecodeError:
                            print("Error decoding EPC data.")
                    else:
                        # print("Received 'Q' response with no data.")
                        if last_payload:
                            display.root.after(0, display.update_car_info, last_payload['data'], last_payload.get('photo'))
                else:
                    print(f"Received unexpected response format: {raw_response}")
            else:
                # print("No response received from reader.") # Too noisy
                pass

            time.sleep(1.0) # Slightly slower loop to reduce serial/db load

        except serial.SerialException as e:
            print(f"Serial communication error: {e}")
            print("Attempting to close and re-open serial port...")
            ser.close()
            time.sleep(5)
            try:
                ser.open()
                print("Serial port reopened successfully.")
                # Re-set power after re-opening
                set_reader_power(ser)
            except serial.SerialException as e_reopen:
                print(f"Failed to reopen serial port: {e_reopen}")
                sys.exit(1)

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            sys.exit(1)

