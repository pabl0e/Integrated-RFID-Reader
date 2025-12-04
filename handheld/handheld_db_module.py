import mysql.connector
from mysql.connector import Error  
from contextlib import closing
import datetime
import json
import os
import uuid

def connect_maindb():
    try:
        conn = mysql.connector.connect(
            #host='192.168.50.149',	     # Pi's IP address
            #host='192.168.254.114',    # Vince's IP address
            host='10.115.157.248',
            user='binslibal',
            password='Vinceleval423!',
            database='rfid_vehicle_system',  # Using existing database with ALL PRIVILEGES
            ssl_disabled=True,  # Disable SSL to fix version mismatch error
        )
        print("Connected to the Main Database Successfully")
        return conn
    
    except Error as e:
        print("Database connection error:", e)
        return None

def connect_localdb():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='binslibal',
            password='Vinceleval423!',
            database='rfid_vehicle_system'  # Using existing database with ALL PRIVILEGES
        )
        print("Connected to the Local Database Successfully")
        return conn
    
    except Error as e:
        print("Database connection error:", e)
        return None

def store_evidence(rfid_uid, photo_path, violation_type, timestamp=None, location=None, device_id="HANDHELD_01"):
    """
    Store violation record in the violations table.
    Falls back to JSON file storage if database connection fails.
    
    Args:
        rfid_uid: The RFID tag UID that was scanned
        photo_path: Path to the evidence photo file
        violation_type: Type of violation selected
        timestamp: Optional timestamp (uses current time if None)
        location: Optional location info
        device_id: Device identifier for tracking
        
    Returns:
        dict: Success status and violation ID if successful
    """
    # Use current timestamp if not provided
    if timestamp is None:
        timestamp = datetime.datetime.now()
    
    # Try database storage first
    conn = connect_localdb()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Insert violation record - simplified for single table structure
            insert_query = """
                INSERT INTO violations 
                (rfid_uid, photo_path, violation_type, violation_timestamp, location, device_id, reported_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            # Use device_id as reported_by for now, or 1 as default user
            reported_by = 1  # Default user ID for handheld device
            
            cursor.execute(insert_query, (rfid_uid, photo_path, violation_type, timestamp, location, device_id, reported_by))
            conn.commit()
            
            violation_id = cursor.lastrowid
            print(f"Violation stored successfully in database with ID: {violation_id}")
            
            return {
                "ok": True, 
                "evidence_id": violation_id,
                "storage_method": "database",
                "message": f"Violation record created with ID {violation_id}"
            }
            
        except Error as e:
            print(f"Database storage failed: {e}")
        except Exception as e:
            print(f"Unexpected database error: {e}")
        finally:
            cursor.close()
            conn.close()
    
    # Fallback to JSON file storage
    try:
        print("Falling back to JSON file storage...")
        
        # Create violations directory
        violations_dir = "violations"
        os.makedirs(violations_dir, exist_ok=True)
        
        # Generate unique violation ID
        violation_id = str(uuid.uuid4())[:8]
        
        # Create violation record
        violation_record = {
            "violation_id": violation_id,
            "rfid_uid": rfid_uid,
            "photo_path": photo_path,
            "violation_type": violation_type,
            "violation_timestamp": timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
            "location": location,
            "device_id": device_id,
            "reported_by": 1,
            "sync_status": "pending"
        }
        
        # Save to JSON file
        json_filename = f"violation_{violation_id}.json"
        json_path = os.path.join(violations_dir, json_filename)
        
        with open(json_path, 'w') as f:
            json.dump(violation_record, f, indent=2)
        
        print(f"Violation stored as JSON file: {json_filename}")
        
        return {
            "ok": True,
            "evidence_id": violation_id,
            "storage_method": "json_file",
            "json_file": json_path,
            "message": f"Violation stored as JSON file with ID {violation_id}"
        }
        
    except Exception as e:
        print(f"JSON storage also failed: {e}")
        return {
            "ok": False, 
            "error": f"Both database and JSON storage failed: {e}",
            "storage_method": "none"
        }

def check_uid(read_uid):
    """
    Check if RFID UID exists in any previous violations
    Since we only have violations table, we'll check for existing violations
    """
    conn = connect_localdb()
    if conn:
        try:
            cursor = conn.cursor()

            # Check if the RFID UID has previous violations
            query = "SELECT COUNT(*) FROM violations WHERE rfid_uid = %s"
            cursor.execute(query, (read_uid,))
            result = cursor.fetchone()

            if result and result[0] > 0:
                print(f"UID '{read_uid}' has {result[0]} previous violations.")
                return {
                    'uid_status': 'found',
                    'previous_violations': result[0],
                    'message': f'Found {result[0]} previous violations'
                }
            else:
                print(f"UID '{read_uid}' has no previous violations.")
                return {
                    'uid_status': 'new',
                    'previous_violations': 0,
                    'message': 'No previous violations found'
                }

        except Error as e:
            print("Error during UID check:", e)
            return {
                'uid_status': 'error',
                'previous_violations': 0,
                'message': f'Database error: {e}'
            }
        finally:
            cursor.close()
            conn.close()
    
    return {
        'uid_status': 'error',
        'previous_violations': 0,
        'message': 'Database connection failed'
    }

def sync_violations(batch_size: int = 300, insert_ignore: bool = True) -> dict:
    """
    Sync violations with CORRECTED mapping for:
    1. Trimming RFID UIDs to match Main DB (24 chars) - Fixes "Skipping" error
    2. Using Absolute Paths for images - Fixes "no_image.jpg" error
    """
    # Acquire connections
    main_conn = connect_maindb()
    local_conn = connect_localdb()

    if not main_conn or not local_conn:
        return {"ok": False, "error": "DB connection failed (main or local)."}

    stats = {
        "uploaded_violations": 0,
        "ok": True
    }

    try:
        with closing(local_conn.cursor(dictionary=True)) as lcur, closing(main_conn.cursor()) as mcur:
            
            # 1. Get pending local violations
            lcur.execute("SELECT * FROM violations WHERE sync_status = 'pending'")
            local_rows = lcur.fetchall()

            if not local_rows:
                print("No pending violations to sync.")
                return stats

            print(f"Found {len(local_rows)} pending violations to sync...")

            for row in local_rows:
                try:
                    # --- STEP 1: MAP DATA ---
                    
                    # A. RFID -> Vehicle ID Lookup (FIXED)
                    # We slice [:24] to remove the extra suffix (e.g., '2F59') so it matches Main DB
                    raw_uid = row['rfid_uid']
                    clean_uid = raw_uid[:24]
                    
                    mcur.execute("SELECT vehicle_id FROM rfid_tags WHERE tag_uid = %s LIMIT 1", (clean_uid,))
                    tag_result = mcur.fetchone()
                    
                    if not tag_result or tag_result[0] is None:
                        # Fallback: Try the raw UID just in case
                        mcur.execute("SELECT vehicle_id FROM rfid_tags WHERE tag_uid = %s LIMIT 1", (raw_uid,))
                        tag_result = mcur.fetchone()
                        
                        if not tag_result or tag_result[0] is None:
                            print(f"Skipping: RFID {clean_uid} is not linked to a vehicle in Main DB.")
                            continue 
                    
                    vehicle_id = tag_result[0]

                    # B. Violation Type Map (String -> ID)
                    local_type = row['violation_type']
                    v_type_id = 1 # Default
                    
                    if "No Parking" in local_type:
                        v_type_id = 1
                    elif "Unauthorized" in local_type:
                        v_type_id = 2
                    
                    # C. Read Image File (BLOB) - FIXED WITH ABSOLUTE PATH
                    image_blob = None
                    image_filename = "no_image.jpg"
                    
                    # Get the directory where THIS script is located
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    # Join it with the relative path from DB (e.g., "evidences/evidence_...")
                    full_image_path = os.path.join(base_dir, row['photo_path'])
                    
                    if row['photo_path'] and os.path.exists(full_image_path):
                        image_filename = os.path.basename(row['photo_path'])
                        with open(full_image_path, 'rb') as file:
                            image_blob = file.read()
                    else:
                        print(f"⚠️ Warning: Could not find image at: {full_image_path}")
                    
                    # --- STEP 2: INSERT INTO MAIN DB ---
                    insert_query = """
                        INSERT INTO violations 
                        (vehicle_id, violation_type_id, description, location, reported_by, 
                         status, created_at, updated_at, image_data, image_filename, 
                         image_mime_type, contest_status)
                        VALUES (%s, %s, %s, %s, %s, 'resolved', %s, %s, %s, %s, 'image/jpeg', NULL)
                    """
                    
                    ts = row.get('violation_timestamp')

                    mcur.execute(insert_query, (
                        vehicle_id,
                        v_type_id,
                        local_type,
                        row.get('location', 'Unknown'),
                        1,              # reported_by
                        ts,             # created_at
                        ts,             # updated_at
                        image_blob,
                        image_filename
                    ))
                    
                    main_conn.commit()
                    
                    # --- STEP 3: UPDATE LOCAL STATUS ---
                    update_query = "UPDATE violations SET sync_status = 'synced' WHERE id = %s"
                    
                    with closing(local_conn.cursor()) as update_cur:
                        update_cur.execute(update_query, (row['id'],))
                        local_conn.commit()
                        
                    stats["uploaded_violations"] += 1
                    print(f"Synced violation {row['id']} -> Vehicle {vehicle_id} (Image: {image_filename})")

                except Exception as inner_e:
                    print(f"Failed to sync violation {row.get('id')}: {inner_e}")
                    continue

        return stats

    except Error as e:
        stats["ok"] = False
        stats["error"] = f"MySQL error: {e}"
        print(stats["error"])
        return stats

    finally:
        if local_conn.is_connected(): local_conn.close()
        if main_conn.is_connected(): main_conn.close()

def add_new_uid(read_uid: str) -> dict:
    """
    Insert a tag into rfid_tags table exactly once.
    Returns dict with status info: {'success': bool, 'message': str, 'new_uid': bool}
    """
    # Try local database first
    conn = connect_localdb()
    if not conn:
        # Try main database as fallback
        conn = connect_maindb()
        if not conn:
            return {
                'success': False,
                'message': 'Failed to connect to both local and main database',
                'new_uid': False
            }
    
    try:
        cursor = conn.cursor()
        query = """
            INSERT IGNORE INTO rfid_tags (tag_uid, status, assigned_date)
            VALUES (%s, 'active', CURDATE())
        """
        cursor.execute(query, (read_uid,))
        conn.commit()
        
        if cursor.rowcount == 1:
            # New UID added successfully
            return {
                'success': True,
                'message': f'New UID {read_uid} registered successfully',
                'new_uid': True
            }
        else:
            # UID already exists
            return {
                'success': True,
                'message': f'UID {read_uid} already exists in database',
                'new_uid': False
            }
            
    except Error as e:
        return {
            'success': False,
            'message': f'Database error: {e}',
            'new_uid': False
        }
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        conn.close()