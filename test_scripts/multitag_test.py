import serial
import time
import sys

# --- Configuration ---
SERIAL_PORT = '/dev/serial0'
BAUD_RATE = 38400
TIMEOUT = 1
# Script stops after collecting this many unique UIDs total
READS_LIMIT = 20 

# --- Commands ---
# <LF>U<CR> - Multi-tag read command
COMMAND_MULTI_TAG_EPC = b'\x0A' + b'U' + b'\x0D'
# <LF>N1,1B<CR> - Set Power to 25 dBm
COMMAND_SET_POWER = b'\x0A\x4E\x31\x2C\x31\x42\x0D'

def set_reader_power(ser):
    try:
        ser.flushInput()
        ser.write(COMMAND_SET_POWER)
        time.sleep(0.1)
        if ser.inWaiting() > 0:
            ser.read(ser.inWaiting())
        print("Power set to MAX (25dBm).")
    except Exception as e:
        print(f"Error setting reader power: {e}")

def main():
    unique_tags_found = set()
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

        print(f"Starting MULTI-TAG BURST scan (Command 'U').")
        print(f"Script will exit after finding {READS_LIMIT} unique tags.")
        print("Waiting for RFID tags...")

        # 3. Main Loop
        while len(unique_tags_found) < READS_LIMIT:
            try:
                # Send command trigger
                ser.write(COMMAND_MULTI_TAG_EPC)
                
                # --- CRITICAL WAIT TIME ---
                # Wait 0.2s to allow the reader to fill the buffer with a burst of tags
                time.sleep(0.2) 

                # Check if any data arrived
                if ser.inWaiting() > 0:
                    # Read the ENTIRE buffer blob at once
                    raw_burst_data = ser.read(ser.inWaiting())

                    # --- THE FIX: SPLIT THE BURST ---
                    # Packets are separated by \r\n (0D 0A). Split the blob by these markers.
                    packets = raw_burst_data.split(b'\r\n')
                    
                    tags_in_this_burst = 0

                    for packet in packets:
                        # Filter out empty packets from the split operation
                        if len(packet) < 4: continue

                        # Check for start marker: <LF>U (0A 55)
                        # Note: The \r\n at the end is gone because of the split.
                        if packet.startswith(b'\nU'):
                            # Strip the 2-byte start marker (\nU) to get the ASCII data
                            epc_ascii_data = packet[2:]
                            
                            try:
                                # Decode ASCII
                                tag_str = epc_ascii_data.decode('ascii').strip()

                                # Standard Slicing: remove 4 char PC head, 4 char CRC tail
                                if len(tag_str) > 8:
                                    actual_epc = tag_str[4:-4]
                                    
                                    # Ensure it looks like valid hex
                                    try:
                                        int(actual_epc, 16)
                                        # Print it
                                        print(f"UID: {actual_epc}")
                                        tags_in_this_burst += 1
                                        unique_tags_found.add(actual_epc)
                                    except ValueError: pass # Ignore noise
                            except UnicodeDecodeError: pass # Ignore decoding errors

                    # --- Report burst count if tags were found ---
                    if tags_in_this_burst > 0:
                        print(f"--- Burst Summary: Read {tags_in_this_burst} tags simultaneously. ---")
                        print(f"Total Unique Tags Found: {len(unique_tags_found)}/{READS_LIMIT}\n")

            except serial.SerialException as e:
                print(f"Serial communication error: {e}")
                break
            except KeyboardInterrupt:
                print("\nStopped by user.")
                break
            
            # Small sleep between major command loops
            time.sleep(0.1)

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)
    finally:
        if ser and ser.is_open:
            ser.close()
            print("Serial port closed. Exiting.")

if __name__ == "__main__":
    main()