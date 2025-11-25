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
    last_payload = None
    last_gui_update_time = 0
    
    # Command 'U' (Inventory) gets the data faster and usually includes PC bits
    COMMAND_MULTI_TAG_EPC = b'\x0A' + b'U' + b'\x0D'

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
        set_reader_power(ser)

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)

    print("Waiting for RFID tag...")

    # Initialize buffer
    data_buffer = b""

    while True:
        try:
            ser.flushInput()
            ser.write(COMMAND_MULTI_TAG_EPC)

            # --- CRITICAL FIX: COLLECTION LOOP ---
            # Wait for the reader to finish sending the FULL long tag.
            # We wait until we see the End Byte (0x0D) or timeout after 0.2s.
            collection_start = time.time()
            while (time.time() - collection_start) < 0.2:
                if ser.inWaiting() > 0:
                    data_buffer += ser.read(ser.inWaiting())
                    if b'\x0D' in data_buffer:
                        break # We found the end of the message!
                time.sleep(0.005)
            # -------------------------------------

            # --- PROCESSING LOOP ---
            while b'\x0A' in data_buffer and b'\x0D' in data_buffer:
                try:
                    start_idx = data_buffer.index(b'\x0A')
                    end_idx = data_buffer.index(b'\x0D', start_idx)
                    
                    packet_end = end_idx + 1
                    if len(data_buffer) > packet_end and data_buffer[packet_end] == 0x0A:
                        packet_end += 1

                    packet = data_buffer[start_idx : packet_end]
                    data_buffer = data_buffer[packet_end:] 
                    
                    if len(packet) > 6:
                        raw_payload = packet[2:].strip()
                        
                        try:
                            tag_full_string = raw_payload.decode('ascii')
                            
                            # --- ROBUST UID EXTRACTION ---
                            # Target UID length is 24 chars (Standard Gen2)
                            target_len = 24
                            actual_epc = ""

                            # Strategy 1: Smart Search for 'E2' (Standard Gen2 Start)
                            # This handles "000E2..." or "3000E2..." or just "E2..."
                            if "E2" in tag_full_string:
                                e2_index = tag_full_string.find("E2")
                                # Check if we have enough characters after E2 to make a full UID
                                if e2_index + target_len <= len(tag_full_string):
                                    actual_epc = tag_full_string[e2_index : e2_index + target_len]
                            
                            # Strategy 2: Fallback (If no E2 found, but length looks like Header + UID)
                            elif len(tag_full_string) >= 24:
                                # If it starts with '3000' (common header), strip it
                                if tag_full_string.startswith("3000") and len(tag_full_string) >= 28:
                                    actual_epc = tag_full_string[4:28]
                                # If it starts with '000' (glitchy header), strip it
                                elif tag_full_string.startswith("000") and len(tag_full_string) >= 27:
                                    actual_epc = tag_full_string[3:27]
                                else:
                                    # Desperate fallback: Take the first 24 chars
                                    actual_epc = tag_full_string[:24]

                            # -----------------------------
                            
                            # Final Verification: Only process if we got exactly 24 chars
                            if len(actual_epc) == 24:
                                if actual_epc != last_read:
                                    print(f"NEW Tag Streamed: {actual_epc}")
                                    last_read = actual_epc
                                    
                                    payload = check_uid(actual_epc, display)
                                    
                                    if isinstance(payload, dict) and 'data' in payload:
                                        last_payload = payload
                                    else:
                                        last_payload = {'data': payload, 'photo': None}
                                    
                                    last_gui_update_time = time.time()

                                else:
                                    current_time = time.time()
                                    if last_payload and (current_time - last_gui_update_time > 2.0):
                                        display.root.after(0, display.update_car_info, last_payload['data'], last_payload.get('photo'))
                                        last_gui_update_time = current_time

                        except UnicodeDecodeError:
                            pass 
                except ValueError:
                    break
            time.sleep(0.02) 

        except serial.SerialException as e:
            print(f"Serial Error: {e}")
            ser.close()
            time.sleep(2)
            try: ser.open(); set_reader_power(ser); 
            except: pass
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(1)