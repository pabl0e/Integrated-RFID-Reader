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
            host='192.168.50.149',	     # Pi's IP address
            user='binslibal',
            password='Vinceleval423!',
            database='rfid_vehicle_system'  # Using existing database with ALL PRIVILEGES
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
    Sync violations between local and main database.
    Upload local violations to main database and clear local after successful sync.
    
    Args:
        batch_size: rows per batch for memory/CPU control
        insert_ignore: if True, use INSERT IGNORE to avoid duplicate-key errors
        
    Returns:
        dict with sync status and counters
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
        with closing(local_conn.cursor()) as lcur, closing(main_conn.cursor()) as mcur:
            # Upload local violations to main database
            lcur.execute("SELECT * FROM violations")
            violations_cols = [d[0] for d in lcur.description]
            placeholders = ", ".join(["%s"] * len(violations_cols))
            collist = ", ".join(f"`{c}`" for c in violations_cols)

            insert_kw = "INSERT IGNORE" if insert_ignore else "INSERT"
            insert_sql = f"{insert_kw} INTO violations ({collist}) VALUES ({placeholders})"

            # Upload in batches
            while True:
                rows = lcur.fetchmany(batch_size)
                if not rows:
                    break
                mcur.executemany(insert_sql, rows)
                main_conn.commit()
                stats["uploaded_violations"] += len(rows)

            # Clear local violations after successful upload
            with closing(local_conn.cursor()) as lpurge:
                lpurge.execute("DELETE FROM violations WHERE id > 0")  # Clear all violations
                local_conn.commit()

        return stats

    except Error as e:
        stats["ok"] = False
        stats["error"] = f"MySQL error: {e}"
        return stats

    except Exception as e:
        stats["ok"] = False
        stats["error"] = f"Unexpected error: {e}"
        return stats

    finally:
        try:
            local_conn.close()
        except Exception:
            pass
        try:
            main_conn.close()
        except Exception:
            pass