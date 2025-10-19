#!/usr/bin/env python3
"""
Verify database tables exist on Pi
"""

import mysql.connector
from mysql.connector import Error

def verify_tables():
    """Check if tables exist in the database"""
    
    try:
        # Connect to the database
        conn = mysql.connector.connect(
            host='localhost',
            user='binslibal',
            password='Vinceleval423!',
            database='rfid_vehicle_system'
        )
        
        cursor = conn.cursor()
        
        print("🔍 DATABASE VERIFICATION")
        print("=" * 40)
        
        # Check current database
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()
        print(f"Current database: {current_db[0]}")
        
        # Show all tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        if tables:
            print(f"\n📊 Tables found ({len(tables)}):")
            for table in tables:
                print(f"   ✅ {table[0]}")
                
                # Show table structure
                cursor.execute(f"DESCRIBE {table[0]}")
                columns = cursor.fetchall()
                print(f"      Columns: {len(columns)}")
                
                # Show record count
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                print(f"      Records: {count}")
                
                if table[0] == 'violations' and count > 0:
                    # Show sample violations
                    cursor.execute("SELECT id, rfid_uid, violation_type FROM violations LIMIT 3")
                    violations = cursor.fetchall()
                    print("      Sample records:")
                    for v in violations:
                        print(f"        ID:{v[0]}, UID:{v[1]}, Type:{v[2]}")
                
                print()
        else:
            print("❌ No tables found in database")
        
        # Check if we can access from external connections
        print("🌐 Network access test:")
        cursor.execute("SHOW VARIABLES LIKE 'bind_address'")
        bind_result = cursor.fetchone()
        if bind_result:
            print(f"   MySQL bind address: {bind_result[1]}")
        
        cursor.close()
        conn.close()
        
        return len(tables) > 0
        
    except Error as e:
        print(f"❌ Database verification error: {e}")
        return False

if __name__ == "__main__":
    verify_tables()