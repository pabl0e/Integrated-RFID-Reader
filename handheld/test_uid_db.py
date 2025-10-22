#!/usr/bin/env python3
"""
Database connectivity test for UID registration
Run this on the Pi to diagnose the exact database error
"""

import sys
import traceback
from handheld_db_module import connect_localdb, connect_maindb, add_new_uid

def test_database_connections():
    """Test both local and main database connections"""
    print("=== DATABASE CONNECTIVITY TEST ===")
    
    # Test local database connection
    print("\n1. Testing LOCAL database connection...")
    try:
        local_conn = connect_localdb()
        if local_conn:
            print("✅ Local database connection: SUCCESS")
            try:
                cursor = local_conn.cursor()
                cursor.execute("SELECT DATABASE(), USER(), VERSION()")
                result = cursor.fetchone()
                print(f"   Database: {result[0]}")
                print(f"   User: {result[1]}")
                print(f"   MySQL Version: {result[2]}")
                cursor.close()
                local_conn.close()
            except Exception as e:
                print(f"❌ Local database query failed: {e}")
                local_conn.close()
        else:
            print("❌ Local database connection: FAILED")
    except Exception as e:
        print(f"❌ Local database connection error: {e}")
        traceback.print_exc()
    
    # Test main database connection
    print("\n2. Testing MAIN database connection...")
    try:
        main_conn = connect_maindb()
        if main_conn:
            print("✅ Main database connection: SUCCESS")
            try:
                cursor = main_conn.cursor()
                cursor.execute("SELECT DATABASE(), USER(), VERSION()")
                result = cursor.fetchone()
                print(f"   Database: {result[0]}")
                print(f"   User: {result[1]}")
                print(f"   MySQL Version: {result[2]}")
                cursor.close()
                main_conn.close()
            except Exception as e:
                print(f"❌ Main database query failed: {e}")
                main_conn.close()
        else:
            print("❌ Main database connection: FAILED")
    except Exception as e:
        print(f"❌ Main database connection error: {e}")
        traceback.print_exc()

def test_rfid_tags_table():
    """Test if rfid_tags table exists and is accessible"""
    print("\n3. Testing rfid_tags table...")
    
    # Try local database first
    conn = connect_localdb()
    if not conn:
        print("   Trying main database instead...")
        conn = connect_maindb()
    
    if not conn:
        print("❌ No database connection available for table test")
        return
    
    try:
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SHOW TABLES LIKE 'rfid_tags'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("✅ rfid_tags table exists")
            
            # Check table structure
            cursor.execute("DESCRIBE rfid_tags")
            columns = cursor.fetchall()
            print("   Table structure:")
            for col in columns:
                print(f"     {col[0]} - {col[1]} - {col[2]} - {col[3]}")
            
            # Check current record count
            cursor.execute("SELECT COUNT(*) FROM rfid_tags")
            count = cursor.fetchone()[0]
            print(f"   Current records: {count}")
            
        else:
            print("❌ rfid_tags table does not exist")
            
            # Show available tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print("   Available tables:")
            for table in tables:
                print(f"     {table[0]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Table test failed: {e}")
        traceback.print_exc()
        conn.close()

def test_uid_insertion():
    """Test the actual UID insertion function"""
    print("\n4. Testing UID insertion function...")
    
    test_uid = "TEST123456789ABC"
    
    try:
        print(f"   Testing with UID: {test_uid}")
        result = add_new_uid(test_uid)
        
        print(f"   Result type: {type(result)}")
        print(f"   Result: {result}")
        
        if isinstance(result, dict):
            if result.get('success'):
                if result.get('new_uid'):
                    print("✅ New UID inserted successfully")
                else:
                    print("✅ UID already exists (expected behavior)")
            else:
                print(f"❌ UID insertion failed: {result.get('message')}")
        else:
            print(f"❌ Unexpected result format: {result}")
            
    except Exception as e:
        print(f"❌ UID insertion test failed: {e}")
        traceback.print_exc()

def main():
    """Run all database tests"""
    print("Starting database diagnostic tests...")
    print("This will help identify the exact cause of UID registration failures")
    
    test_database_connections()
    test_rfid_tags_table()
    test_uid_insertion()
    
    print("\n=== TEST COMPLETE ===")
    print("Please share the output above to help diagnose the issue.")

if __name__ == "__main__":
    main()