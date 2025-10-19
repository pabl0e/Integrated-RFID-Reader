#!/usr/bin/env python3
"""
Test SSH tunnel connection from Windows to Pi database
Run this on Windows while SSH tunnel is active
"""

import mysql.connector
from mysql.connector import Error

def test_tunnel_connection():
    """Test connection through SSH tunnel"""
    
    try:
        print("🧪 Testing SSH tunnel connection...")
        print("Make sure SSH tunnel is running: ssh -L 3307:localhost:3306 binslibal@192.168.50.149")
        
        # Connect through the tunnel (port 3307 on localhost)
        conn = mysql.connector.connect(
            host='127.0.0.1',  # localhost (Windows)
            port=3307,         # SSH tunnel port
            user='binslibal',
            password='Vinceleval423!',
            database='rfid_vehicle_system'
        )
        
        cursor = conn.cursor()
        
        print("✅ SSH tunnel connection successful!")
        
        # Show tables through tunnel
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        if tables:
            print(f"\n📊 Tables visible through tunnel ({len(tables)}):")
            for table in tables:
                print(f"   ✅ {table[0]}")
                
                # Show record count
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                print(f"      Records: {count}")
        else:
            print("❌ No tables visible through tunnel")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Error as e:
        print(f"❌ SSH tunnel connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure SSH tunnel is running")
        print("2. Check tunnel command: ssh -L 3307:localhost:3306 binslibal@192.168.50.149")
        print("3. Verify port 3307 is free on Windows")
        return False

if __name__ == "__main__":
    test_tunnel_connection()