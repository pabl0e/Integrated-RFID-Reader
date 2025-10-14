import mysql.connector
from mysql.connector import Error  
from contextlib import closing

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
            
        return new_data

def store_evidence(rfid_uid, photo_path, violation_type, timestamp=None, location=None, device_id="HANDHELD_01"):
    """
    Store evidence record in the local vehicle_evidence table.
    Falls back to JSON file storage if database connection fails.
    
    Args:
        rfid_uid: The RFID tag UID that was scanned
        photo_path: Path to the evidence photo file
        violation_type: Type of violation selected
        timestamp: Optional timestamp (uses current time if None)
        location: Optional location info
        device_id: Device identifier for tracking
        
    Returns:
        dict: Success status and evidence ID if successful
    """
    # Use current timestamp if not provided
    if timestamp is None:
        import datetime
        timestamp = datetime.datetime.now()
    
    # Try database storage first
    conn = connect_localdb()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Insert evidence record
            insert_query = """
                INSERT INTO vehicle_evidence 
                (rfid_uid, photo_path, violation_type, timestamp, location, device_id, sync_status)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            """
            
            cursor.execute(insert_query, (rfid_uid, photo_path, violation_type, timestamp, location, device_id))
            conn.commit()
            
            evidence_id = cursor.lastrowid
            print(f"Evidence stored successfully in database with ID: {evidence_id}")
            
            return {
                "ok": True, 
                "evidence_id": evidence_id,
                "storage_method": "database",
                "message": f"Evidence record created with ID {evidence_id}"
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
        import json
        import os
        import uuid
        
        print("Falling back to JSON file storage...")
        
        # Create evidence directory
        evidences_dir = "evidences"
        os.makedirs(evidences_dir, exist_ok=True)
        
        # Generate unique evidence ID
        evidence_id = str(uuid.uuid4())[:8]
        
        # Create evidence record
        evidence_record = {
            "evidence_id": evidence_id,
            "rfid_uid": rfid_uid,
            "photo_path": photo_path,
            "violation_type": violation_type,
            "timestamp": timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
            "location": location,
            "device_id": device_id,
            "sync_status": "pending"
        }
        
        # Save to JSON file
        json_filename = f"evidence_{evidence_id}.json"
        json_path = os.path.join(evidences_dir, json_filename)
        
        with open(json_path, 'w') as f:
            json.dump(evidence_record, f, indent=2)
        
        print(f"Evidence stored as JSON file: {json_filename}")
        
        return {
            "ok": True,
            "evidence_id": evidence_id,
            "storage_method": "json_file",
            "json_file": json_path,
            "message": f"Evidence stored as JSON file with ID {evidence_id}"
        }
        
    except Exception as e:
        print(f"JSON storage also failed: {e}")
        return {
            "ok": False, 
            "error": f"Both database and JSON storage failed: {e}",
            "storage_method": "none"
        }

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

def copy_table(source_conn, dest_conn, table_name, batch_size=500, insert_ignore=True):
    """
    Copy an entire table from source_conn to dest_conn in small batches.

    Args:
        source_conn: MySQL connection to copy FROM (e.g., main DB).
        dest_conn:   MySQL connection to copy TO   (e.g., local Pi DB).
        table_name:  Name of the table to copy (must exist on both).
        batch_size:  Number of rows to move per chunk (limits memory).
        insert_ignore: If True, uses INSERT IGNORE to skip duplicate-key errors.
                       (Assumes appropriate unique keys/PK exist.)
    """
    # Create cursors for both DBs and ensure they are closed after use
    with closing(dest_conn.cursor()) as dcur, closing(source_conn.cursor()) as scur:
        # Speed bulk operation on destination: temporarily disable FK checks
        # (Avoids constraints firing on each row during TRUNCATE/INSERT)
        dcur.execute("SET FOREIGN_KEY_CHECKS=0")

        # Clear destination table so we replace it with the source snapshot
        dcur.execute(f"TRUNCATE TABLE `{table_name}`")

        # Select everything from the source table
        scur.execute(f"SELECT * FROM `{table_name}`")

        # Build a generic INSERT that matches the source column order
        cols = [desc[0] for desc in scur.description]  # column names from SELECT
        placeholders = ", ".join(["%s"] * len(cols))   # %s for each column
        collist = ", ".join(f"`{c}`" for c in cols)    # backticked col names

        # Optional INSERT IGNORE to avoid duplicate errors (if keys overlap)
        insert_kw = "INSERT IGNORE" if insert_ignore else "INSERT"
        insert_sql = f"{insert_kw} INTO `{table_name}` ({collist}) VALUES ({placeholders})"

        # Stream rows in batches—keeps RAM usage low on the Pi
        while True:
            rows = scur.fetchmany(batch_size)  # get next chunk
            if not rows:
                break
            dcur.executemany(insert_sql, rows)  # push chunk to dest
            dest_conn.commit()                  # commit each chunk (safer on Pi)

        # Re-enable FK checks after bulk load
        dcur.execute("SET FOREIGN_KEY_CHECKS=1")

def sync_databases(
    batch_size: int = 300,
    evidence_table: str = "vehicle_evidence",
    tag_table: str = "rfid_tags",
    user_table: str = "user_profiles",   # use your exact table name
    vehicle_table: str = "vehicles",
    insert_ignore: bool = True
) -> dict:
    """
    Lightweight two-way sync tailored for a Raspberry Pi Zero W.

    Steps:
        1) Append local evidence -> main DB (batched)
        2) Purge local evidence table (after successful upload)
        3) Refresh local reference tables from main DB:
           rfid_tags, user_profiles, vehicles

    Args:
        batch_size: rows per batch for memory/CPU control.
        evidence_table: name of the evidence table to upload (local -> main).
        tag_table, user_table, vehicle_table: reference tables to mirror (main -> local).
        insert_ignore: if True, use INSERT IGNORE during inserts to avoid duplicate-key errors.

    Returns:
        dict with basic counters and status.
    """
    # Acquire connections. Reuse your existing helpers from your module.
    main_conn = connect_maindb()   # authoritative, cloud/central
    local_conn = connect_localdb() # Raspberry Pi local DB

    # If either connection fails, abort early with a clear error
    if not main_conn or not local_conn:
        return {"ok": False, "error": "DB connection failed (main or local)."}

    # Accumulate simple stats for visibility/logging
    stats = {
        "uploaded_evidence_rows": 0,  # how many evidence rows pushed to main
        "refreshed_tables": [],       # which tables we mirrored back to local
        "ok": True
    }

    try:
        # Use context managers so cursors are always closed
        with closing(local_conn.cursor()) as lcur, closing(main_conn.cursor()) as mcur:
            # ------------------ 1) Upload local evidence -> main ------------------
            # We stream all columns (SELECT *). This requires same column order and types.
            lcur.execute(f"SELECT * FROM `{evidence_table}`")
            evidence_cols = [d[0] for d in lcur.description]   # column names as returned by SELECT
            placeholders = ", ".join(["%s"] * len(evidence_cols))
            collist = ", ".join(f"`{c}`" for c in evidence_cols)

            # INSERT IGNORE prevents duplicate-key errors from breaking the sync
            insert_kw = "INSERT IGNORE" if insert_ignore else "INSERT"
            ev_insert_sql = f"{insert_kw} INTO `{evidence_table}` ({collist}) VALUES ({placeholders})"

            # Fetch and forward evidence rows in small chunks
            while True:
                rows = lcur.fetchmany(batch_size)  # pull next chunk from local
                if not rows:
                    break
                mcur.executemany(ev_insert_sql, rows)  # push chunk to main
                main_conn.commit()                     # commit each chunk
                stats["uploaded_evidence_rows"] += len(rows)

            # ------------------ 2) Purge local evidence (post-upload) -------------
            # Only clear local evidence after successful upload to main.
            with closing(local_conn.cursor()) as lpurge:
                lpurge.execute(f"TRUNCATE TABLE `{evidence_table}`")
                local_conn.commit()

            # -------------s----- 3) Refresh local reference tables -----------------
            # Pull authoritative copies of these tables from main back to local.
            for tname in (tag_table, user_table, vehicle_table):
                copy_table(
                    source_conn=main_conn,     # FROM main (authoritative)
                    dest_conn=local_conn,      # TO local (Pi)
                    table_name=tname,
                    batch_size=batch_size,
                    insert_ignore=insert_ignore
                )
                stats["refreshed_tables"].append(tname)

        # If we got here, everything finished without raising an exception
        return stats

    # MySQL-specific failures (e.g., connectivity, SQL syntax, constraint issues)
    except Error as e:
        stats["ok"] = False
        stats["error"] = f"MySQL error: {e}"
        return stats

    # Any other unexpected Python/runtime errors
    except Exception as e:
        stats["ok"] = False
        stats["error"] = f"Unexpected error: {e}"
        return stats

    # Always attempt to close connections, even on error
    finally:
        try:
            local_conn.close()
        except Exception:
            pass
        try:
            main_conn.close()
        except Exception:
            pass
