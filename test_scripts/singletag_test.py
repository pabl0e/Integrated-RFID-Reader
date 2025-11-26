import serial
import time
import sys

# --- Configuration based on original script ---
SERIAL_PORT = '/dev/serial0'
BAUD_RATE = 38400
TIMEOUT = 1
READS_LIMIT = 5

# Commands based on original script
# <LF>Q<CR> - Command to read a single tag
COMMAND_SINGLE_TAG_EPC = b'\x0A\x51\x0D'
# <LF>N1,1B<CR> - Set Power to 25 dBm
COMMAND_SET_POWER = b'\x0A\x4E\x31\x2C\x31\x42\x0D'

def set_reader_power(ser):
    """
    Sets the reader's RF power to MAX (25 dBm) upon startup.
    This mirrors the 'set_reader_power' function in the original script.
    """
    try:
        ser.flushInput()
        # print(f"Sending Set Max Power command (25 dBm)...")
        ser.write(COMMAND_SET_POWER)
        time.sleep(0.1) # Give reader time to process
        
        # We read the response just to clear the buffer, similar to original script
        ser.read(ser.inWaiting())
            
    except Exception as e:
        print(f"Error setting reader power: {e}")

def main():
    reads_count = 0
    # Removed 'last_read_epc' variable as it is no longer needed for tracking duplicates
    ser = None

    try:
        # 1. Open Serial Port
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUD_RATE,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=TIMEOUT
        )
        print(f"Successfully opened serial port {ser.port} at {ser.baudrate} baud.")

        # 2. Set Power
        set_reader_power(ser)

        print(f"Starting scan. Script will exit after {READS_LIMIT} total reads (duplicates allowed).")
        print("Waiting for RFID tag...")

        # 3. Main Loop
        while reads_count < READS_LIMIT:
            try:
                ser.flushInput()
                # Send 'Q' command
                ser.write(COMMAND_SINGLE_TAG_EPC)
                # Wait briefly for hardware response
                time.sleep(0.1)

                response_data = ser.read(ser.inWaiting())

                if response_data:
                    # --- INLINE EXTRACTION LOGIC (MIRRORING SOURCE SCRIPT) ---
                    
                    raw_response = response_data.hex()
                    
                    # Validate response structure: starts with <LF>Q and ends with <CR><LF>
                    if len(response_data) >= 4 and \
                       response_data[0] == 0x0A and \
                       response_data[1] == ord('Q') and \
                       response_data[-2:] == b'\x0D\x0A':

                        # Strip header/footer bytes to get the data section
                        epc_data_bytes = response_data[2:-2]

                        if epc_data_bytes:
                            try:
                                # Decode ASCII to get the full tag string
                                tag_id = epc_data_bytes.decode('ascii').strip()

                                # Check if response is just an empty 'Q' acknowledgement (no tag detected)
                                if raw_response == "0a510d0a": 
                                    pass # No tag detected in RF field.
                                else:
                                    # --- SLICING LOGIC FROM SOURCE TEXT ---
                                    # The source script defines the actual EPC as the middle part,
                                    # cutting off the first 4 chars (PC) and last 4 chars (CRC).
                                    actual_epc = tag_id[4:-4]
                                    # --------------------------------------

                                    # Process successful read
                                    # We ensure it's not empty, but we NO LONGER check against the last read.
                                    if actual_epc:
                                        print(f"UID: {actual_epc}")
                                        # Increment count even if it's the same tag
                                        reads_count += 1
                                        print(f"--> Read count: {reads_count}/{READS_LIMIT}")

                            except UnicodeDecodeError:
                                print("Error decoding EPC data.")
                    # ---------------------------------------------------------

            except serial.SerialException as e:
                print(f"Serial communication error: {e}")
                break
            except KeyboardInterrupt:
                print("\nStopped by user.")
                break
                
            # Sleep slightly to prevent flooding the serial port too rapidly
            time.sleep(0.5)

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)
    finally:
        if ser and ser.is_open:
            ser.close()
            print("Serial port closed. Exiting.")

if __name__ == "__main__":
    main()