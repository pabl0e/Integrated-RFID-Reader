#!/usr/bin/env python3
"""
Test script to verify MySQL database setup for RFID system
Tests both local and main database connections
"""

from handheld_db_module import connect_localdb, connect_maindb, store_evidence
import datetime

def test_local_database():
    """Test local database connection and table structure"""
    print("=== Testing Local Database Connection ===")
    
    conn = connect_localdb()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Test if tables exist
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✅ Found {len(tables)} tables in local_db:")
            for table in tables:
                print(f"   - {table[0]}")
            
            # Test table structure
            if tables:
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"DESCRIBE {table_name}")
                    columns = cursor.fetchall()
                    print(f"✅ Table '{table_name}' structure:")
                    for col in columns:
                        print(f"   - {col[0]} ({col[1]})")
                    print()
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error testing local database: {e}")
            return False
    else:
        print("❌ Could not connect to local database")
        return False

def test_main_database():
    """Test main database connection"""
    print("=== Testing Main Database Connection ===")
    
    conn = connect_maindb()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ Connected to main database, MySQL version: {version[0]}")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Error testing main database: {e}")
            return False
    else:
        print("❌ Could not connect to main database")
        return False

def test_evidence_storage():
    """Test evidence storage functionality"""
    print("=== Testing Evidence Storage ===")
    
    # Test data
    test_rfid = "TEST123456789"
    test_photo = "test_photo.jpg"
    test_violation = "Test Violation"
    
    result = store_evidence(
        rfid_uid=test_rfid,
        photo_path=test_photo,
        violation_type=test_violation,
        location="Test Location",
        device_id="TEST_DEVICE"
    )
    
    if result["ok"]:
        storage_method = result.get("storage_method", "unknown")
        evidence_id = result.get("evidence_id", "N/A")
        print(f"✅ Evidence stored successfully!")
        print(f"   Storage method: {storage_method}")
        print(f"   Evidence ID: {evidence_id}")
        
        if storage_method == "database":
            print("   📊 Database storage working perfectly!")
        elif storage_method == "json_file":
            print("   📁 JSON fallback storage working!")
            print(f"   File: {result.get('json_file', 'N/A')}")
        
        return True
    else:
        print(f"❌ Evidence storage failed: {result.get('error', 'Unknown error')}")
        return False

def main():
    """Run all database tests"""
    print("🧪 RFID System Database Test Suite")
    print("=" * 50)
    
    # Test results
    local_test = test_local_database()
    print()
    
    main_test = test_main_database()
    print()
    
    evidence_test = test_evidence_storage()
    print()
    
    # Summary
    print("=" * 50)
    print("🎯 TEST SUMMARY:")
    print(f"   Local Database:  {'✅ PASS' if local_test else '❌ FAIL'}")
    print(f"   Main Database:   {'✅ PASS' if main_test else '❌ FAIL'}")
    print(f"   Evidence Storage: {'✅ PASS' if evidence_test else '❌ FAIL'}")
    
    if all([local_test, evidence_test]):
        print("\n🎉 Your RFID system database setup is ready!")
        print("   You can now run the handheld enforcement system.")
    elif local_test and evidence_test:
        print("\n✅ Local system working! Main database optional for testing.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()