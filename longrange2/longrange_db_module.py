import mysql.connector
from mysql.connector import Error  
from display_gui import CarInfoDisplay

def connect_db():
    try:
        conn = mysql.connector.connect(
            #host='192.168.50.239',          # FRANZ Laptop (NCR)
            #host='192.168.50.200'           # MUGOT Laptop (NCR)
            host='192.168.254.135',          # MUGOT Laptop (Vince House)        
            user='jicmugot16',
            password='melonbruh123',
            database='rfid_vehicle_system'
        )
        print("Connected to the Database Successfully")
        return conn
    
    except Error as e:
        print("Database connection error:", e)
        return None

def check_uid(read_uid, display):
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()

            # Check if the tag_uid exists in rfid_tags
            query = "SELECT * FROM rfid_tags WHERE tag_uid = %s"
            cursor.execute(query, (read_uid,))
            result = cursor.fetchone()

            if result:
                print(f"UID '{read_uid}' found in database. Logging time...")
                vehicle_id = result[2]
                add_access_log(vehicle_id, read_uid, 'exit', 'exit')

                new_data = fetch_info(vehicle_id)

                # Update the GUI using the passed display instance
                display.root.after(0, display.update_car_info, new_data)
                return new_data
            else:
                print(f"UID '{read_uid}' not found. No action taken.")
                new_data = {
                    'sticker_status': 'N/A',
                    'user_id': 'N/A',  # Placeholder for actual user ID
                    'student_name': 'N/A',  # Placeholder for actual student name
                    'make': 'N/A',
                    'model': 'N/A',
                    'color': 'N/A',
                    'vehicle_type': 'N/A',
                    'license_plate': 'N/A'
                }
                # Update the GUI using the passed display instance
                display.root.after(0, display.update_car_info, new_data)
                return new_data
        except Error as e:
            print("Error during UID check:", e)
        finally:
            cursor.close()
            conn.close()

def add_access_log(vehicle_id, tag_uid, entry_type, location):
    conn = connect_db()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO access_logs
              (vehicle_id, tag_uid, entry_type, timestamp, location)
            VALUES
              (%s,         %s,      %s,         CURRENT_TIMESTAMP, %s)
        """
        cursor.execute(query, (vehicle_id, tag_uid, entry_type, location))
        conn.commit()
        print("Access log added.")
    except Error as e:
        print("Insert error:", e)
    finally:
        cursor.close()
        conn.close()

def fetch_info(vehicle_id):
    """
    Fetch sticker status from the RFID tag table, then user ID, student name,
    make, model, color, vehicle type, and license plate for a given vehicle_id.
    """
    conn = connect_db()
    if not conn:
        return {
            'sticker_status': 'N/A',
            'user_id': 'N/A',
            'student_name': 'N/A',
            'make': 'N/A',
            'model': 'N/A',
            'color': 'N/A',
            'vehicle_type': 'N/A',
            'license_plate': 'N/A'
        }
    try:
        cursor = conn.cursor()
        query = """
            SELECT
              rt.status AS sticker_status,
              v.user_id,
              up.full_name,
              v.make,
              v.model,
              v.color,
              v.vehicle_type,
              v.plate_number
            FROM vehicles v
            LEFT JOIN user_profiles up
              ON v.user_id = up.user_id
            LEFT JOIN rfid_tags rt
              ON rt.vehicle_id = v.id
            WHERE v.id = %s
            LIMIT 1
        """
        cursor.execute(query, (vehicle_id,))
        row = cursor.fetchone()
        if row:
            status, user_id, full_name, make, model, color, vehicle_type, plate_number = row
            print("Info Fetched Successfully")
            return {
                'sticker_status': status,
                'user_id': str(user_id),
                'student_name': full_name,
                'make': make,
                'model': model,
                'color': color,
                'vehicle_type': vehicle_type,
                'license_plate': plate_number
            }
        else:
            # No matching vehicle or tag
            return {
                'sticker_status': 'N/A',
                'user_id': 'N/A',
                'student_name': 'N/A',
                'make': 'N/A',
                'model': 'N/A',
                'color': 'N/A',
                'vehicle_type': 'N/A',
                'license_plate': 'N/A'
            }
    except Error as e:
        print("Error fetching vehicle info:", e)
        return {
            'sticker_status': 'Error',
            'user_id': 'Error',
            'student_name': 'Error',
            'make': 'Error',
            'model': 'Error',
            'color': 'Error',
            'vehicle_type': 'Error',
            'license_plate': 'Error'
        }
    finally:
        cursor.close()
        conn.close()

    