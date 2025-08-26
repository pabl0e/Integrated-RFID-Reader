import mysql.connector
from mysql.connector import Error  

def connect_maindb():
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

def connect_localdb():
    try:
        conn = mysql.connector.connect(
            host='localhost',          # Local Device
            user='jicmugot16',
            password='melonbruh123',
            database='local_db'
        )
        print("Connected to the Database Successfully")
        return conn
    
    except Error as e:
        print("Database connection error:", e)
        return None
    
def check_uid(read_uid):
    conn = connect_localdb()
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

                new_data = fetch_info(vehicle_id)
                
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

        except Error as e:
            print("Error during UID check:", e)
        finally:
            cursor.close()
            conn.close()

def fetch_info(vehicle_id):
    """
    Fetch sticker status from the RFID tag table, then user ID, student name,
    make, model, color, vehicle type, and license plate for a given vehicle_id.
    """
    conn = connect_localdb()
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

    