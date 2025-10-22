#!/usr/bin/env python3
"""
Create the missing rfid_tags table in the rfid_vehicle_system database
"""

import mysql.connector
from mysql.connector import Error
from handheld_db_module import connect_localdb

def create_rfid_tags_table():
    """Create the rfid_tags table in the local database"""
    print("Creating rfid_tags table...")
    
    conn = connect_localdb()
    if not conn:
        print("❌ Failed to connect to local database")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Create rfid_tags table with the structure from create_tables.py
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS rfid_tags (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tag_uid VARCHAR(255) UNIQUE NOT NULL,
            vehicle_id INT DEFAULT NULL,
            status ENUM('active', 'inactive', 'expired') DEFAULT 'active',
            issued_date DATE DEFAULT NULL,
            expiry_date DATE DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_tag_uid (tag_uid),
            INDEX idx_vehicle_id (vehicle_id)
        )
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        
        print("✅ rfid_tags table created successfully")
        
        # Verify the table was created
        cursor.execute("SHOW TABLES LIKE 'rfid_tags'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("✅ Table verification: rfid_tags table now exists")
            
            # Show table structure
            cursor.execute("DESCRIBE rfid_tags")
            columns = cursor.fetchall()
            print("   Table structure:")
            for col in columns:
                print(f"     {col[0]} - {col[1]} - {col[2]} - {col[3]}")
        else:
            print("❌ Table verification failed")
            return False
        
        cursor.close()
        conn.close()
        return True
        
    except Error as e:
        print(f"❌ Failed to create table: {e}")
        conn.close()
        return False

def test_uid_insertion_after_creation():
    """Test UID insertion after table creation"""
    from handheld_db_module import add_new_uid
    
    print("\nTesting UID insertion after table creation...")
    
    test_uid = "TEST123456789ABC"
    
    try:
        result = add_new_uid(test_uid)
        
        if isinstance(result, dict):
            if result.get('success'):
                if result.get('new_uid'):
                    print("✅ New UID inserted successfully")
                else:
                    print("✅ UID already exists (expected behavior)")
                return True
            else:
                print(f"❌ UID insertion failed: {result.get('message')}")
                return False
        else:
            print(f"❌ Unexpected result format: {result}")
            return False
            
    except Exception as e:
        print(f"❌ UID insertion test failed: {e}")
        return False

def main():
    """Create table and test UID insertion"""
    print("=== RFID TAGS TABLE CREATION ===")
    
    if create_rfid_tags_table():
        if test_uid_insertion_after_creation():
            print("\n🎉 SUCCESS! UID registration should now work properly.")
            print("You can now run the UID registration functionality.")
        else:
            print("\n❌ Table created but UID insertion still fails.")
    else:
        print("\n❌ Failed to create rfid_tags table.")

if __name__ == "__main__":
    main()