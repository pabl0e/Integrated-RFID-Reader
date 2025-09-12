import mysql.connector
from mysql.connector import Error  
from display_gui import CarInfoDisplay

def connect_db():
    try:
        conn = mysql.connector.connect(
            #host='192.168.50.239',           # FRANZ Laptop (NCR)
            #host='192.168.50.200',           # MUGOT Laptop (NCR)
            #host='192.168.20.238',           # MUGOT Laptop (DML)
            #host='192.168.20.',                # FRANZ Laptop (DML)  
            #host='192.168.254.135',          # MUGOT Laptop (Vince House)   
            #host='192.168.1.47',           # MUGOT Laptop (Mugot House)     
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
                add_access_log(vehicle_id, read_uid, 'entry', 'entrance')

                # vehicle + user info
                new_data = fetch_info(vehicle_id)

                # profile picture (None if not present)
                profile_bytes = None
                try:
                    # usc_id in new_data is a str; convert if numeric
                    usc_id_num = int(new_data['usc_id'])
                except Exception:
                    usc_id_num = new_data['usc_id']

                pic = fetch_profile_picture(usc_id_num)
                if pic and pic.get('profile_image_bytes'):
                    profile_bytes = pic['profile_image_bytes']

                # update GUI
                display.root.after(0, display.update_car_info, new_data, profile_bytes)

                # return both for caller reuse
                return {'data': new_data, 'photo': profile_bytes}

            else:
                print(f"UID '{read_uid}' not found. No action taken.")
                new_data = {
                    'sticker_status': 'N/A',
                    'usc_id': 'N/A',
                    'student_name': 'N/A',
                    'make': 'N/A',
                    'model': 'N/A',
                    'color': 'N/A',
                    'vehicle_type': 'N/A',
                    'license_plate': 'N/A'
                }
                # pass None so GUI shows blank placeholder
                display.root.after(0, display.update_car_info, new_data, None)
                return {'data': new_data, 'photo': None}

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
            'usc_id': 'N/A',
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
              v.usc_id,
              up.full_name,
              v.make,
              v.model,
              v.color,
              v.vehicle_type,
              v.plate_number
            FROM vehicles v
            LEFT JOIN user_profiles up
              ON v.usc_id = up.usc_id
            LEFT JOIN rfid_tags rt
              ON rt.vehicle_id = v.id
            WHERE v.id = %s
            LIMIT 1
        """
        cursor.execute(query, (vehicle_id,))
        row = cursor.fetchone()
        if row:
            status, usc_id, full_name, make, model, color, vehicle_type, plate_number = row
            print("Info Fetched Successfully")
            return {
                'sticker_status': status,
                'usc_id': str(usc_id),
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
                'usc_id': 'N/A',
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
            'usc_id': 'Error',
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

def fetch_profile_picture(usc_id: int):
    """
    Returns the profile picture for the given usc_id from user_profiles.
    Output:
      {
        'profile_image_bytes': <bytes> or None,
        'profile_image_mime': <str> or None
      }
    """
    conn = connect_db()
    if not conn:
        return {'profile_image_bytes': None, 'profile_image_mime': None}

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT profile_picture, file_type
            FROM user_profiles
            WHERE usc_id = %s
            LIMIT 1
            """,
            (usc_id,)
        )
        row = cursor.fetchone()
        if row:
            blob, file_type = row
            return {
                'profile_image_bytes': bytes(blob) if blob else None,
                'profile_image_mime': file_type if file_type else None
            }
        else:
            return {'profile_image_bytes': None, 'profile_image_mime': None}
    except Error as e:
        print("Error fetching profile picture:", e)
        return {'profile_image_bytes': None, 'profile_image_mime': None}
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()