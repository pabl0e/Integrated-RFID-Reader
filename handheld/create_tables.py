#!/usr/bin/env python3
"""
Create database tables for RFID system
"""

import mysql.connector
from mysql.connector import Error

def create_tables():
    """Create all required tables for the RFID system"""
    
    try:
        # Connect to local database
        conn = mysql.connector.connect(
            host='localhost',
            user='binslibal',
            password='Vinceleval423!',
            database='rfid_vehicle_system'  # Fixed to match handheld_db_module
        )
        
        cursor = conn.cursor()
        
        print("Creating tables in rfid_vehicle_system...")
        
        # Create vehicle_evidence table
        vehicle_evidence_sql = """
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
        
        cursor.execute(vehicle_evidence_sql)
        print("✅ Created vehicle_evidence table")
        
        # Create rfid_tags table
        rfid_tags_sql = """
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
        
        cursor.execute(rfid_tags_sql)
        print("✅ Created rfid_tags table")
        
        # Create vehicles table
        vehicles_sql = """
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
        
        cursor.execute(vehicles_sql)
        print("✅ Created vehicles table")
        
        # Create user_profiles table
        user_profiles_sql = """
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
        
        cursor.execute(user_profiles_sql)
        print("✅ Created user_profiles table")
        
        # Commit changes
        conn.commit()
        
        # Show tables
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print(f"\n📊 Tables created in local_db:")
        for table in tables:
            print(f"   - {table[0]}")
            
        # Add sample data
        print("\n🔧 Adding sample data...")
        
        # Sample user
        cursor.execute("""
        INSERT IGNORE INTO user_profiles (user_id, full_name, email, user_type, department)
        VALUES (12345, 'Test Student', 'test.student@university.edu', 'student', 'Computer Science')
        """)
        
        # Sample vehicle  
        cursor.execute("""
        INSERT IGNORE INTO vehicles (id, user_id, make, model, color, vehicle_type, plate_number)
        VALUES (1, 12345, 'Toyota', 'Corolla', 'White', 'car', 'ABC-1234')
        """)
        
        # Sample RFID tag
        cursor.execute("""
        INSERT IGNORE INTO rfid_tags (tag_uid, vehicle_id, status, issued_date, expiry_date)
        VALUES ('E2806894000050320D373135FB4B', 1, 'active', CURDATE(), DATE_ADD(CURDATE(), INTERVAL 1 YEAR))
        """)
        
        conn.commit()
        print("✅ Sample data added")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Database setup complete!")
        return True
        
    except Error as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    create_tables()