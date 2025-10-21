#!/usr/bin/env python3
"""
Check MySQL access and permissions for binslibal user
"""

import mysql.connector
from mysql.connector import Error

def check_mysql_access():
    """Check what databases and permissions the user has"""
    
    try:
        # Connect to MySQL server
        conn = mysql.connector.connect(
            host='localhost',
            user='binslibal',
            password='Vinceleval423!'
        )
        
        cursor = conn.cursor()
        
        print("🔍 MYSQL ACCESS CHECK")
        print("=" * 40)
        
        # Check current user
        cursor.execute("SELECT USER()")
        user = cursor.fetchone()
        print(f"Connected as: {user[0]}")
        
        # Show available databases
        print("\n📋 Available databases:")
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        for db in databases:
            print(f"   - {db[0]}")
        
        # Check user privileges
        print("\n🔐 User privileges:")
        cursor.execute("SHOW GRANTS FOR CURRENT_USER()")
        grants = cursor.fetchall()
        for grant in grants:
            print(f"   - {grant[0]}")
        
        # Try to create a test database
        print("\n🧪 Testing database creation...")
        test_db_name = "test_rfid_access"
        try:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {test_db_name}")
            cursor.execute(f"DROP DATABASE {test_db_name}")
            print("✅ Database creation: ALLOWED")
        except Error as e:
            print(f"❌ Database creation: DENIED - {e}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Error as e:
        print(f"❌ MySQL connection error: {e}")
        return False

if __name__ == "__main__":
    check_mysql_access()