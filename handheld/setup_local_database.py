#!/usr/bin/env python3
"""
Setup script for local MySQL database
Run this to create the local database and user for the handheld RFID system
"""

import mysql.connector
from mysql.connector import Error
import sys

def setup_local_database():
    """
    Setup local MySQL database for the handheld RFID system
    """
    print("=== Local Database Setup ===")
    
    # Get MySQL root credentials
    root_password = input("Enter MySQL root password (press Enter if no password): ").strip()
    
    try:
        # Connect as root to create database and user
        if root_password:
            root_conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password=root_password
            )
        else:
            root_conn = mysql.connector.connect(
                host='localhost',
                user='root'
            )
        
        cursor = root_conn.cursor()
        print("✅ Connected to MySQL as root")
        
        # Create database
        try:
            cursor.execute("CREATE DATABASE IF NOT EXISTS local_db")
            print("✅ Database 'local_db' created/verified")
        except Error as e:
            print(f"Database creation error: {e}")
        
        # Create user and grant privileges
        try:
            cursor.execute("CREATE USER IF NOT EXISTS 'jicmugot16'@'localhost' IDENTIFIED BY 'melonbruh123'")
            cursor.execute("GRANT ALL PRIVILEGES ON local_db.* TO 'jicmugot16'@'localhost'")
            cursor.execute("FLUSH PRIVILEGES")
            print("✅ User 'jicmugot16' created/updated with privileges")
        except Error as e:
            print(f"User creation error: {e}")
        
        cursor.close()
        root_conn.close()
        
        # Now connect as the new user to create tables
        user_conn = mysql.connector.connect(
            host='localhost',
            user='jicmugot16',
            password='melonbruh123',
            database='local_db'
        )
        
        cursor = user_conn.cursor()
        print("✅ Connected as 'jicmugot16'")
        
        # Create tables
        create_tables(cursor)
        
        cursor.close()
        user_conn.close()
        
        print("\n🎉 Database setup complete!")
        print("You can now run the handheld enforcement system.")
        
    except Error as e:
        print(f"❌ MySQL Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure MySQL server is running: sudo systemctl start mysql")
        print("2. Check if you have the correct root password")
        print("3. Try: sudo mysql -u root -p")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def create_tables(cursor):
    """Create necessary tables for the handheld system"""
    
    # Vehicle Evidence table (main storage for scanned violations)
    evidence_table = """
    CREATE TABLE IF NOT EXISTS vehicle_evidence (
        id INT AUTO_INCREMENT PRIMARY KEY,
        rfid_uid VARCHAR(255) NOT NULL,
        photo_path VARCHAR(500),
        violation_type VARCHAR(255),
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        location VARCHAR(255),
        device_id VARCHAR(100) DEFAULT 'HANDHELD_01',
        sync_status ENUM('pending', 'synced') DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_rfid_uid (rfid_uid),
        INDEX idx_timestamp (timestamp),
        INDEX idx_sync_status (sync_status)
    )
    """
    
    # RFID Tags table (for UID lookup)
    rfid_tags_table = """
    CREATE TABLE IF NOT EXISTS rfid_tags (
        id INT AUTO_INCREMENT PRIMARY KEY,
        tag_uid VARCHAR(255) UNIQUE NOT NULL,
        vehicle_id INT,
        status ENUM('active', 'inactive', 'expired') DEFAULT 'active',
        issued_date DATE,
        expiry_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_tag_uid (tag_uid),
        INDEX idx_vehicle_id (vehicle_id)
    )
    """
    
    # Vehicles table (vehicle information)
    vehicles_table = """
    CREATE TABLE IF NOT EXISTS vehicles (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        make VARCHAR(100),
        model VARCHAR(100),
        color VARCHAR(50),
        vehicle_type ENUM('car', 'motorcycle', 'bicycle', 'other') DEFAULT 'car',
        plate_number VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_user_id (user_id),
        INDEX idx_plate_number (plate_number)
    )
    """
    
    # User Profiles table (student/staff information)
    user_profiles_table = """
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id INT PRIMARY KEY,
        full_name VARCHAR(255),
        email VARCHAR(255),
        phone VARCHAR(20),
        user_type ENUM('student', 'staff', 'faculty', 'visitor') DEFAULT 'student',
        department VARCHAR(100),
        status ENUM('active', 'inactive') DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_email (email),
        INDEX idx_user_type (user_type)
    )
    """
    
    tables = [
        ("vehicle_evidence", evidence_table),
        ("rfid_tags", rfid_tags_table),
        ("vehicles", vehicles_table),
        ("user_profiles", user_profiles_table)
    ]
    
    for table_name, table_sql in tables:
        try:
            cursor.execute(table_sql)
            print(f"✅ Table '{table_name}' created/verified")
        except Error as e:
            print(f"❌ Error creating table '{table_name}': {e}")
    
    # Insert sample data for testing
    insert_sample_data(cursor)

def insert_sample_data(cursor):
    """Insert sample data for testing"""
    
    try:
        # Sample user profile
        cursor.execute("""
        INSERT IGNORE INTO user_profiles (user_id, full_name, email, user_type, department)
        VALUES (12345, 'Test Student', 'test.student@university.edu', 'student', 'Computer Science')
        """)
        
        # Sample vehicle
        cursor.execute("""
        INSERT IGNORE INTO vehicles (id, user_id, make, model, color, vehicle_type, plate_number)
        VALUES (1, 12345, 'Toyota', 'Corolla', 'White', 'car', 'ABC-1234')
        """)
        
        # Sample RFID tag (using the one from your test)
        cursor.execute("""
        INSERT IGNORE INTO rfid_tags (tag_uid, vehicle_id, status, issued_date, expiry_date)
        VALUES ('E2806894000050320D373135FB4B', 1, 'active', CURDATE(), DATE_ADD(CURDATE(), INTERVAL 1 YEAR))
        """)
        
        print("✅ Sample test data inserted")
        
    except Error as e:
        print(f"Sample data insertion error: {e}")

def test_connection():
    """Test the database connection"""
    
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='jicmugot16',
            password='melonbruh123',
            database='local_db'
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vehicle_evidence")
        count = cursor.fetchone()[0]
        
        print(f"✅ Connection test successful! Evidence records: {count}")
        
        cursor.close()
        conn.close()
        return True
        
    except Error as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    print("This script will setup the local MySQL database for the handheld RFID system.")
    print("Make sure MySQL server is running before proceeding.\n")
    
    choice = input("Do you want to proceed? (y/n): ").lower().strip()
    
    if choice in ['y', 'yes']:
        setup_local_database()
        print("\nTesting connection...")
        test_connection()
    else:
        print("Setup cancelled.")