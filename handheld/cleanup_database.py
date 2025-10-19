#!/usr/bin/env python3
"""
Database Cleanup Script for RFID Violations System
Safely deletes the rfid_vehicle_system database to start fresh
"""

import mysql.connector
from mysql.connector import Error

def cleanup_database():
    """Delete the rfid_vehicle_system database completely"""
    
    print("🧹 DATABASE CLEANUP SCRIPT")
    print("=" * 50)
    print("⚠️  WARNING: This will DELETE the entire rfid_vehicle_system database!")
    print("   - All violations data will be lost")
    print("   - All users data will be lost")
    print("   - This action cannot be undone")
    print("=" * 50)
    
    # Ask for confirmation
    confirm = input("Are you sure you want to delete the database? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("❌ Database cleanup cancelled.")
        return False
    
    try:
        # Connect to MySQL server (without specifying database)
        print("\n🔌 Connecting to MySQL server...")
        conn = mysql.connector.connect(
            host='localhost',
            user='binslibal',
            password='Vinceleval423!'
        )
        
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SHOW DATABASES LIKE 'rfid_vehicle_system'")
        db_exists = cursor.fetchone()
        
        if db_exists:
            print("📋 Found rfid_vehicle_system database")
            
            # Show current tables before deletion
            try:
                cursor.execute("USE rfid_vehicle_system")
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                
                if tables:
                    print("📊 Current tables in database:")
                    for table in tables:
                        print(f"   - {table[0]}")
                        
                        # Show record count for each table
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                            count = cursor.fetchone()[0]
                            print(f"     Records: {count}")
                        except:
                            print("     Records: Unable to count")
                else:
                    print("📊 No tables found in database")
                    
            except Error as e:
                print(f"⚠️  Could not check tables: {e}")
            
            # Final confirmation
            final_confirm = input("\n🗑️  Proceed with deletion? (yes/no): ").strip().lower()
            if final_confirm not in ['yes', 'y']:
                print("❌ Database cleanup cancelled.")
                return False
            
            # Drop the database
            print("\n🗑️  Deleting rfid_vehicle_system database...")
            cursor.execute("DROP DATABASE rfid_vehicle_system")
            print("✅ Database deleted successfully!")
            
        else:
            print("ℹ️  rfid_vehicle_system database not found (already deleted or never created)")
        
        # Show remaining databases
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        print("\n📋 Remaining databases:")
        for db in databases:
            if db[0] not in ['information_schema', 'performance_schema', 'mysql', 'sys']:
                print(f"   - {db[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Database cleanup completed successfully!")
        print("💡 You can now run create_tables.py to set up a fresh database")
        
        return True
        
    except Error as e:
        print(f"❌ Error during database cleanup: {e}")
        if 'Access denied' in str(e):
            print("💡 Try running with different MySQL credentials")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def quick_cleanup():
    """Quick cleanup without prompts (for development)"""
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='binslibal',
            password='Vinceleval423!'
        )
        
        cursor = conn.cursor()
        cursor.execute("DROP DATABASE IF EXISTS rfid_vehicle_system")
        cursor.close()
        conn.close()
        
        print("✅ Quick cleanup completed - rfid_vehicle_system database deleted")
        return True
        
    except Error as e:
        print(f"❌ Quick cleanup failed: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    # Check for quick mode argument
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        print("🚀 Running quick cleanup...")
        quick_cleanup()
    else:
        cleanup_database()