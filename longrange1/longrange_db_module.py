import mysql.connector
from mysql.connector import pooling # <-- IMPORT POOLING
import time
from mysql.connector import Error  
from display_gui import CarInfoDisplay
from PIL import Image
import io

# --- Create the pool ONCE when the module is imported ---
try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="rfid_pool",
        pool_size=3,  # Start with 3, can increase to 5 if needed
        #host='192.168.50.238',
        host='10.56.87.248',
        user='jicmugot16',
        password='melonbruh123',
        database='rfid_vehicle_system',
        autocommit=True
    )
    print("Database connection pool created successfully.")
except Error as e:
    print(f"Error creating connection pool: {e}")
    db_pool = None

# Cache settings
TAG_CACHE_TTL = 300.0  # seconds (UID TTL cache time)
_tag_cache = {}        # {uid: (timestamp, {'data':..., 'photo':...})}

RED_X_IMAGE_PATH = "/home/jicmugot16/longrange1/Red_X.jpg"

def process_image_data(image_data):
    """Takes raw bytes, opens, and resizes them to 500x900."""
    try:
        stream = io.BytesIO(image_data)
        img = Image.open(stream).convert('RGB')
        # Resize here in the background thread!
        img.thumbnail((500, 900), Image.LANCZOS)
        return img
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

# --- Pre-load the Red X image bytes ONCE ---
try:
    with open(RED_X_IMAGE_PATH, "rb") as f:
        _raw_x_data = f.read()
    _RED_X_IMG = process_image_data(_raw_x_data)
except Exception as e:
    print(f"Could not load Red X: {e}")
    _RED_X_IMG = None


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

def get_db_connection():
    """
    REVISED function to get a connection from the POOL.
    Replaces the old connect_db().
    """
    if not db_pool:
        print("Database pool is not available.")
        return None
    try:
        # Get a connection from the pool
        conn = db_pool.get_connection()
        return conn
    except Error as e:
        print(f"Error getting connection from pool: {e}")
        return None

def check_uid(read_uid, display):

    # Check the cache first
    cached_data = _get_cached(read_uid)
    if cached_data:
        # print("Cache HIT") # Uncomment for debugging
        # Don't log every cache hit, too noisy
        # add_access_log(cached_data['data'].get('vehicle_id'), read_uid, 'entry', 'entrance', success=1)
        display.root.after(0, display.update_car_info, cached_data['data'], cached_data.get('photo'))
        return cached_data
    
    # print("Cache MISS") # Uncomment for debugging

    # --- Use the POOL to get a connection ---
    conn = get_db_connection()
    cursor = None # Define cursor outside try block
    
    empty_data = {k: 'N/A' for k in
                  ['sticker_status','usc_id','vehicle_id','student_name','make','model','color','vehicle_type','license_plate']}

    if not conn:
        # Show N/A but still log a failed attempt
        add_access_log(None, read_uid, 'entry', 'entrance', success=0) # This will get its own connection
        display.root.after(0, display.update_car_info, empty_data, _RED_X_IMG)
        return {'data': empty_data, 'photo': _RED_X_IMG}

    try:
        cursor = conn.cursor()
        query = """
            SELECT
                v.sticker_status,
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
            # --- NO MATCH: show red X + log failure (success=0)
            add_access_log(None, read_uid, 'entry', 'entrance', success=0)
            display.root.after(0, display.update_car_info, empty_data, _RED_X_IMG)
            return {'data': empty_data, 'photo': _RED_X_IMG}

        # --- MATCH FOUND
        (sticker_status, usc_id, vehicle_id, full_name, make, model, color, vehicle_type,
         plate_number, blob, file_type) = result

        data = {
            'sticker_status': sticker_status,
            'usc_id': str(usc_id),
            'vehicle_id': vehicle_id,
            'student_name': full_name,
            'make': make,
            'model': model,
            'color': color,
            'vehicle_type': vehicle_type,
            'license_plate': plate_number
        }

        # ... inside the MATCH FOUND section ...
        (sticker_status, usc_id, vehicle_id, full_name, make, model, color, vehicle_type,
         plate_number, blob, file_type) = result

        # REPLACE the old photo logic with this:
        if blob:
            photo = process_image_data(blob) # Resize it NOW
        else:
            photo = None
            
        # Update cache to store the object, not bytes
        _put_cached(read_uid, {'data': data, 'photo': photo})

        # success=1
        add_access_log(vehicle_id, read_uid, 'entry', 'entrance', success=1)

        # Update display
        display.root.after(0, display.update_car_info, data, photo)
        return {'data': data, 'photo': photo}

    except Error as e:
        print("Error during UID check:", e)
        error_data = {k: 'Error' for k in
                      ['sticker_status','usc_id','vehicle_id','student_name','make','model','color','vehicle_type','license_plate']}
        
        add_access_log(None, read_uid, 'entry', 'entrance', success=0)
        display.root.after(0, display.update_car_info, error_data, _RED_X_IMG)
        return {'data': error_data, 'photo': _RED_X_IMG}
    
    finally:
        # --- CRITICAL CHANGE ---
        # This returns the connection to the pool, it doesn't close it
        if cursor:
            cursor.close()
        if conn:
            conn.close() 


def add_access_log(vehicle_id, tag_uid, entry_type, location, success):
    """Add an access log entry. (Now uses the pool)"""
    conn = get_db_connection()
    cursor = None # Define cursor outside try block
    if not conn:
        print("Error: Could not get DB connection to add access log.")
        return
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO access_logs
            (vehicle_id, tag_uid, entry_type, location, success)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (vehicle_id, tag_uid, entry_type, location, success))
        # conn.commit() # Not needed if autocommit=True in pool
        print("Access log added.")
    except Error as e:
        print(f"Error inserting access log: {e}")
    finally:
        # --- CRITICAL CHANGE ---
        # Return connection to the pool
        if cursor:
            cursor.close()
        if conn:
            conn.close()
