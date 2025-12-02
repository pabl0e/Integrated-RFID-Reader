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
            # Upload local violations to main database (excluding id to avoid conflicts)
            lcur.execute("SELECT * FROM violations")
            all_cols = [d[0] for d in lcur.description]
            
            # Find id column index and exclude it
            id_index = all_cols.index('id') if 'id' in all_cols else None
            violations_cols = [c for c in all_cols if c != 'id']
            
            placeholders = ", ".join(["%s"] * len(violations_cols))
            collist = ", ".join(f"`{c}`" for c in violations_cols)

            insert_sql = f"INSERT INTO violations ({collist}) VALUES ({placeholders})"

            # Upload in batches
            # Determine indexes for matching columns used to correlate rows
            try:
                ridx = all_cols.index('rfid_uid')
            except ValueError:
                ridx = None
            try:
                tidx = all_cols.index('violation_timestamp')
            except ValueError:
                tidx = None
            try:
                didx = all_cols.index('device_id')
            except ValueError:
                didx = None

            while True:
                rows = lcur.fetchmany(batch_size)
                if not rows:
                    break

                # Remove id column from each row if it exists
                if id_index is not None:
                    filtered_rows = [tuple(val for i, val in enumerate(row) if i != id_index) for row in rows]
                else:
                    filtered_rows = rows

                # Insert into main DB
                mcur.executemany(insert_sql, filtered_rows)
                main_conn.commit()
                stats["uploaded_violations"] += len(rows)

                # After successful insert, update local sync_status to match main DB 'status' column
                # We will query main DB for each inserted row using (rfid_uid, violation_timestamp, device_id)
                if ridx is not None and tidx is not None and didx is not None:
                    for row in rows:
                        # original row includes id at id_index; get matching keys from original row
                        rfid_val = row[ridx]
                        ts_val = row[tidx]
                        dev_val = row[didx]

                        try:
                            # Fetch status from main DB
                            mcur.execute("SELECT status FROM violations WHERE rfid_uid=%s AND violation_timestamp=%s AND device_id=%s LIMIT 1",
                                         (rfid_val, ts_val, dev_val))
                            res = mcur.fetchone()
                            main_status = res[0] if res else 'synced'

                            # Update local row's sync_status
                            with closing(local_conn.cursor()) as lupd:
                                lupd.execute("UPDATE violations SET sync_status=%s WHERE rfid_uid=%s AND violation_timestamp=%s AND device_id=%s",
                                             (main_status, rfid_val, ts_val, dev_val))
                                local_conn.commit()
                        except Exception:
                            # If any error occurs, continue; do not abort entire sync
                            continue

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
            INSERT IGNORE INTO rfid_tags (tag_uid, status, issued_date)
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