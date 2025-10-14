import mysql.connector
import time
from mysql.connector import Error  
from display_gui import CarInfoDisplay

# Cache settings
TAG_CACHE_TTL = 300.0  # seconds (UID TTL cache time)
_tag_cache = {}        # {uid: (timestamp, {'data':..., 'photo':...})}

def _get_cached(uid):
    """Retrieve cached UID data if it's still valid."""
    now = time.time()
    hit = _tag_cache.get(uid)
    if hit and (now - hit[0]) < TAG_CACHE_TTL:
        return hit[1]
    return None

def _put_cached(uid, payload):
    """Store the UID data in cache."""
    _tag_cache[uid] = (time.time(), payload)
    if len(_tag_cache) > 200:
        _tag_cache.pop(next(iter(_tag_cache)))

def connect_db():
    """Set up the MySQL connection with connection pooling."""
    try:
        conn = mysql.connector.connect(
            #host='192.168.50.216',  # Replace with your DB host IP or hostname
            host='192.168.1.16',
            user='jicmugot16',
            password='melonbruh123',
            database='rfid_vehicle_system',
            autocommit=True  # Enable auto commit to avoid unnecessary round trips
        )
        return conn
    except Error as e:
        print("Database connection error:", e)
        return None

def check_uid(read_uid, display):
    """Optimized function to check UID in the database and return user info + photo."""
    # Check the cache first
    cached_data = _get_cached(read_uid)
    if cached_data:
        display.root.after(0, display.update_car_info, cached_data['data'], cached_data.get('photo'))
        return cached_data

    conn = connect_db()
    if not conn:
        # If no DB connection, return empty data with None for photo
        empty_data = {k: 'N/A' for k in
                    ['sticker_status','usc_id','student_name','make','model','color','vehicle_type','license_plate']}
        display.root.after(0, display.update_car_info, empty_data, None)
        return {'data': empty_data, 'photo': None}

    try:
        cursor = conn.cursor()

        # Perform a single JOIN query to fetch everything
        query = """
            SELECT
                t.status,
                v.usc_id,
                v.vehicle_id,
                COALESCE(up.full_name, ''),
                v.make,
                v.model,
                v.color,
                v.vehicle_type,
                v.plate_number,
                up.profile_picture,
                up.profile_picture_type
            FROM rfid_tags AS t
            JOIN vehicles AS v ON v.vehicle_id = t.vehicle_id
            LEFT JOIN user_profiles AS up ON up.usc_id = v.usc_id
            WHERE t.tag_uid = %s
            LIMIT 1
        """
        cursor.execute(query, (read_uid,))
        result = cursor.fetchone()

        if not result:
            # No matching UID found in the DB
            empty_data = {k: 'N/A' for k in
                        ['sticker_status','usc_id','vehicle_id','student_name','make','model','color','vehicle_type','license_plate']}
            display.root.after(0, display.update_car_info, empty_data, None)
            return {'data': empty_data, 'photo': None}

        # Unpack query results
        (status, usc_id, vehicle_id, full_name, make, model, color, vehicle_type, plate_number, blob, file_type) = result

        data = {
            'sticker_status': status,
            'usc_id': str(usc_id),
            'vehicle_id': vehicle_id,
            'student_name': full_name,
            'make': make,
            'model': model,
            'color': color,
            'vehicle_type': vehicle_type,
            'license_plate': plate_number
        }

        photo = bytes(blob) if blob else None

        # Store the result in cache for future use
        _put_cached(read_uid, {'data': data, 'photo': photo})

        # --- Add Access Log Entry ---
        add_access_log(vehicle_id, read_uid, 'entry', 'entrance')  # Insert log when UID is matched

        # Update the GUI with the fetched data
        display.root.after(0, display.update_car_info, data, photo)

        # Return the data and photo
        return {'data': data, 'photo': photo}

    except Error as e:
        print("Error during UID check:", e)
        error_data = {k: 'Error' for k in
                    ['sticker_status','usc_id','vehicle_id','student_name','make','model','color','vehicle_type','license_plate']}
        display.root.after(0, display.update_car_info, error_data, None)
        return {'data': error_data, 'photo': None}

    finally:
        try:
            cursor.close()
        except Exception as e:
            print(f"Error closing cursor: {e}")
        conn.close()

def add_access_log(vehicle_id, tag_uid, entry_type, location):
    """Add an access log entry for when an RFID tag is scanned."""
    conn = connect_db()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO access_logs
            (vehicle_id, tag_uid, entry_type, timestamp, location)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)
        """
        cursor.execute(query, (vehicle_id, tag_uid, entry_type, location))
        conn.commit()
        print("Access log added.")
    except Error as e:
        print(f"Error inserting access log: {e}")
    finally:
        cursor.close()
        conn.close()
