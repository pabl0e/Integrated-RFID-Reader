import mysql.connector
from mysql.connector import Error
import serial
import time
import sys

# --- Database Configuration ---
# Update 'host' to the IP address of your laptop/server
DB_CONFIG = {
    'host': '192.168.50.81', 
    'user': 'jicmugot16',
    'password': 'melonbruh123',
    'database': 'rfid_vehicle_system',
    'connection_timeout': 10
}

def get_db_connection():
    """Establishes a standard connection to the database (No Pool)."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"DB Connection Error: {e}")
        return None

def add_new_uid(read_uid: str) -> bool:
    """
    Checks if UID exists. If not, adds it.
    Returns: True if added, False if exists or error.
    """
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database for insertion.")
        return False
        
    cursor = None
    try:
        cursor = conn.cursor()
        # Insert only if the tag_uid does NOT already exist.
        query = """
            INSERT INTO rfid_tags (tag_uid)
            SELECT %s
            FROM DUAL
            WHERE NOT EXISTS (
                SELECT 1 FROM rfid_tags WHERE tag_uid = %s
            )
        """
        cursor.execute(query, (read_uid, read_uid))
        conn.commit()
        
        if cursor.rowcount == 1:
            return True # Successfully added
        else:
            return False # Already existed
            
    except Error as e:
        print(f"Error inserting UID: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def import_gpio():
    try:
        import RPi.GPIO as GPIO
        # print("RPi.GPIO module successfully imported.")
        return GPIO
    except ModuleNotFoundError:
        print("RPi.GPIO module not available (Running on PC?).")
        return None

def run_rfid_read():
    GPIO = import_gpio() 
    
    try:
        ser = serial.Serial(
            port='/dev/serial0',  # Ensure this matches your Pi's configuration
            baudrate=38400,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
        )
        print(f"Serial port {ser.port} opened. Waiting for RFID tag...")

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)

    # --- FM503 Command Definitions ---
    COMMAND_SINGLE_TAG_EPC = b'\x0A' + b'Q' + b'\x0D'

    while True:
        try:
            ser.flushInput()
            # print(f"Scanning...") # Optional: reduce spam
            ser.write(COMMAND_SINGLE_TAG_EPC)
            time.sleep(0.1)

            response_data = ser.read(ser.inWaiting())

            if response_data:
                raw_response = response_data.hex()

                # Basic validation of response packet
                if len(response_data) >= 4 and \
                   response_data[0] == 0x0A and \
                   response_data[1] == ord('Q') and \
                   response_data[-2:] == b'\x0D\x0A':

                    # Extract data between header/command and footer
                    epc_data_bytes = response_data[2:-2]

                    if epc_data_bytes:
                        try:
                            tag_id = epc_data_bytes.decode('ascii').strip()

                            # Check for the specific "No Tag" response code
                            if raw_response == "0a510d0a": 
                                pass # No tag, do nothing
                            else:
                                # Parse EPC (removes PC bytes and CRC bytes)
                                actual_epc = tag_id[4:-4]
                                print(f"Detected EPC: {actual_epc}")
                                
                                # --- DATABASE INTERACTION ---
                                if add_new_uid(actual_epc):
                                    print(f" >> ADDED new UID: {actual_epc}")
                                else:
                                    print(f" >> UID exists: {actual_epc}")

                        except UnicodeDecodeError:
                            print("Error decoding EPC data.")
            
            # Loop delay
            time.sleep(1.5)

        except serial.SerialException as e:
            print(f"Serial error: {e}. Reconnecting...")
            ser.close()
            time.sleep(5)
            try:
                ser.open()
            except:
                pass
        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

if __name__ == "__main__":
    run_rfid_read()