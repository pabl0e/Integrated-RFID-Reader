import mysql.connector
from mysql.connector import Error  # ✅ correct import

def connect_db():
    try:
        conn = mysql.connector.connect(
            host='192.168.50.238',          # IP of your laptop (MySQL server)
            user='jicmugot16',
            password='melonbruh123',
            database='rfid_vehicle_system'
        )
        return conn
    except Error as e:
        print("Database connection error:", e)
        return None

def check_uid(read_uid):
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()

            # Check if the tag_uid exists in rfid_tags
            query = "SELECT * FROM rfid_tags WHERE tag_uid = %s"
            cursor.execute(query, (read_uid,))
            result = cursor.fetchone()

            if result:
                print(f"✅ UID '{read_uid}' found in database. Logging time...")
                add_time()
            else:
                print(f"❌ UID '{read_uid}' not found. No action taken.")

        except Error as e:
            print("Error during UID check:", e)
        finally:
            cursor.close()
            conn.close()

def add_time():
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            # Only insert timestamp, assuming default CURRENT_TIMESTAMP
            query = "INSERT INTO time_logs () VALUES ()"
            cursor.execute(query)
            conn.commit()
            print("✅ Timestamp added.")
        except Error as e:
            print("Insert error:", e)
        finally:
            cursor.close()
            conn.close()