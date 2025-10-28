# Integrated RFID Reader System

A comprehensive **RFID-based vehicle tracking and parking enforcement system** designed for educational institutions and parking facilities. The system provides real-time vehicle registration verification and parking violation enforcement using multiple deployment configurations. This project was made in compliance for our university capstone project.

![System Overview](https://img.shields.io/badge/Platform-Raspberry%20Pi-red) ![Language](https://img.shields.io/badge/Language-Python-blue) ![Database](https://img.shields.io/badge/Database-MySQL%2FMariaDB-orange) ![License](https://img.shields.io/badge/License-MIT-green)

## System Overview

This integrated system consists of **three main components**:

1. **Handheld Device** - Portable violation enforcement unit
2. **Long-Range Station 1** - Entry point 
3. **Long-Range Station 2** - Exit point

The handheld device can operate **independently** with local storage and **sync** with a central database when network connectivity is available.

## Key Features

### Handheld Enforcement Device
- **RFID Tag Scanning** - FM-503 compatible RFID reader
- **Evidence Photography** - High-quality camera integration (Picamera2)
- **Violation Classification** - Two specific violation types:
  - Parking in No Parking Zones
  - Unauthorized Parking in designated spots
- **OLED Display** - Real-time feedback and menu navigation
- **Offline Operation** - Local SQLite/MySQL storage with sync capability
- **Button Interface** - Physical navigation controls (UP/DOWN/CENTER/BACK)
- **Automatic Backup** - JSON fallback storage when database unavailable

### Long-Range Monitoring Stations
- **Continuous RFID Monitoring** - Real-time vehicle detection
- **GUI Display System** - Full-screen vehicle information display
- **Student/Staff Verification** - Complete profile integration
- **Vehicle Registration Database** - Make, model, color, license plate tracking
- **Time & Access Logging** - Entry/exit timestamp recording
- **Multi-threaded Operation** - Non-blocking RFID scanning and GUI updates

### Database Architecture
- **Local Database** - Individual device storage (MySQL/MariaDB)
- **Central Database** - Network-synchronized main repository
- **Bidirectional Sync** - Evidence upload and reference data download
- **Data Integrity** - Comprehensive indexing and relationship management
- **Backup Systems** - Multiple storage fallback mechanisms

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Handheld      │    │  Long-Range 1   │    │  Long-Range 2   │
│   Enforcement   │    │  (Entry Point)  │    │  (Exit Point)   │
│                 │    │                 │    │                 │
│ • RFID Scanner  │    │ • RFID Monitor  │    │ • RFID Monitor  │
│ • Camera        │    │ • GUI Display   │    │ • GUI Display   │
│ • OLED Display  │    │ • Database Log  │    │ • Database Log  │
│ • Local Storage │    │ • Real-time UI  │    │ • Real-time UI  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Central MySQL  │
                    │    Database     │
                    │                 │
                    │ • Vehicle Data  │
                    │ • User Profiles │
                    │ • RFID Tags     │
                    │ • Violations    │
                    └─────────────────┘
```

## Hardware Requirements

### Handheld Device
- **Raspberry Pi Zero W**
- **FM-503 RFID Reader** (UHF 860-960MHz)
- **Pi Camera Module** (v1 or later)
- **128x128 Waveshare OLED  Multi-color Display** (SSD1351)
- **Navigation Buttons** (4-button configuration)
- **18650 Lithium-Ion Batteries** (At least 2 pcs, Parallel configuration, 5V 1A)
- **MicroSD Card** (32GB+ recommended)

### Long-Range Stations  
- **Raspberry Pi Zero W** or Raspberry Pi 4
- **FM-503 RFID Reader** (UHF long-range)
- **HDMI Display** (1920x1080 recommended)
- **Ethernet Connection** (for database sync)
- **MicroSD Card** (64GB+ recommended)

## Database Schema

### Core Tables

#### `vehicle_evidence` (Violations Storage)
```sql
id                INT AUTO_INCREMENT PRIMARY KEY
rfid_uid          VARCHAR(255) NOT NULL           -- Scanned RFID tag
photo_path        VARCHAR(500)                    -- Evidence photo location  
violation_type    VARCHAR(255)                    -- Violation classification
timestamp         DATETIME DEFAULT CURRENT_TIMESTAMP
location          VARCHAR(255)                    -- Violation location
device_id         VARCHAR(100)                    -- Recording device ID
sync_status       ENUM('pending', 'synced')       -- Sync state
created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

#### `rfid_tags` (Tag Registry)
```sql
id                INT AUTO_INCREMENT PRIMARY KEY
tag_uid           VARCHAR(255) UNIQUE NOT NULL    -- RFID identifier
vehicle_id        INT                             -- Foreign key to vehicles
status            ENUM('active', 'inactive', 'expired')
issued_date       DATE
expiry_date       DATE
created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

#### `vehicles` (Vehicle Information)
```sql
id                INT AUTO_INCREMENT PRIMARY KEY  
user_id           INT                             -- Owner reference
make              VARCHAR(100)                    -- Vehicle make
model             VARCHAR(100)                    -- Vehicle model
color             VARCHAR(50)                     -- Vehicle color
vehicle_type      ENUM('car', 'motorcycle', 'bicycle', 'other')
plate_number      VARCHAR(20)                     -- License plate
created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

#### `user_profiles` (User Information)
```sql
user_id           INT PRIMARY KEY                 -- Student/Staff ID
full_name         VARCHAR(255)                    -- Complete name
email             VARCHAR(255)                    -- Contact email
phone             VARCHAR(20)                     -- Phone number
user_type         ENUM('student', 'staff', 'faculty', 'visitor')
department        VARCHAR(100)                    -- Academic department
status            ENUM('active', 'inactive')      -- Account status
created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

## Installation & Setup

### 1. System Preparation

```bash
# Update Raspberry Pi OS
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install python3-pip git mysql-server -y

# Install Python dependencies
pip3 install mysql-connector-python pillow picamera2 RPi.GPIO
```

### 2. Database Setup

```bash
# Clone repository
git clone https://github.com/yourusername/Integrated-RFID-Reader.git
cd Integrated-RFID-Reader

# Setup database (for each device)
cd handheld  # or longrange1/longrange2
python3 create_tables.py
python3 test_database.py
```

### 3. Hardware Configuration

#### Handheld Device GPIO Mapping
| Component | GPIO Pin | Physical Pin |
|-----------|----------|--------------|
| UP Button | GPIO 4 | Pin 7 |
| DOWN Button | GPIO 27 | Pin 13 |
| CENTER Button | GPIO 17 | Pin 11 |
| BACK Button | GPIO 26 | Pin 37 |
| OLED SDA | GPIO 2 | Pin 3 |
| OLED SCL | GPIO 3 | Pin 5 |
| Camera | CSI Port | Camera Connector |

#### RFID Reader Connection
| RFID Pin | Pi Pin | Function |
|----------|--------|----------|
| VCC | 5V | Power |
| GND | GND | Ground |
| TX | GPIO 14 (TXD) | Serial Communication |
| RX | GPIO 15 (RXD) | Serial Communication |

### 4. Configuration Files

Update database credentials in each module:
```python
# handheld_db_module.py
def connect_localdb():
    conn = mysql.connector.connect(
        host='localhost',
        user='your_username',        # Update this
        password='your_password',    # Update this  
        database='rfid_vehicle_system'
    )
```

## Usage

### Handheld Enforcement Device

1. **Power On** - Boot the Raspberry Pi with the enforcement software
2. **Main Menu** - Press CENTER button to start enforcement process
3. **RFID Scan** - Present RFID tag to reader (automatic detection)
4. **Photo Capture** - System automatically captures evidence photo
5. **Violation Selection** - Use UP/DOWN buttons to select violation type, CENTER to confirm
6. **Database Storage** - Violation automatically recorded with timestamp

### Long-Range Monitoring

1. **Automatic Start** - System begins monitoring on boot
2. **Real-time Display** - GUI shows vehicle information when tags detected
3. **Database Logging** - All access events automatically recorded
4. **Background Sync** - Periodic synchronization with central database

## 📡 Network Synchronization

The system supports **automatic bidirectional synchronization**:

### Upload (Local → Central)
- Violation evidence records
- Access log entries  
- Photo file transfers
- Status updates

### Download (Central → Local)
- Updated vehicle registrations
- New RFID tag assignments
- User profile changes
- System configuration updates

### Offline Operation
- **Local Storage** - All operations continue without network
- **Queue Management** - Changes stored locally until sync available
- **Conflict Resolution** - Intelligent merging of data changes
- **Backup Systems** - JSON file fallback for critical data

## API & Integration

### Database Functions

```python
# Store violation evidence
store_evidence(
    rfid_uid="ABC123456789",
    photo_path="/path/to/evidence.jpg", 
    violation_type="Parking in No Parking Zones",
    location="Campus Parking Area",
    device_id="HANDHELD_01"
)

# Check RFID tag information
tag_info = check_uid("ABC123456789")
print(tag_info['student_name'])  # Returns associated user info

# Synchronize databases
sync_result = sync_databases()
print(f"Uploaded {sync_result['uploaded_evidence_rows']} records")
```

### RFID Integration

```python
# Scan for RFID tags
scanned_uid = scan_rfid_for_enforcement()
if scanned_uid:
    print(f"Detected tag: {scanned_uid}")
```

## Monitoring & Maintenance

### System Health Checks
```bash
# Test database connections
python3 test_database.py

# Check RFID hardware
python3 handheld_rfid_module.py

# Verify camera operation  
python3 -c "from picamera2 import Picamera2; print('Camera OK')"
```

### Log Files
- **Application Logs** - `/var/log/rfid_system.log`
- **Database Sync** - `/var/log/database_sync.log`
- **Hardware Status** - `/var/log/hardware_status.log`

## Security Features

- **Encrypted Database Connections** - MySQL SSL/TLS support
- **User Authentication** - Individual device credentials
- **Data Integrity** - Transaction-based database operations
- **Access Control** - Role-based user permissions
- **Audit Trail** - Complete violation and access logging

## Contributing

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'Add some AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. **Open** a Pull Request

## Testing

```bash
# Run system tests
python3 test_database.py       # Database connectivity
python3 test_rfid.py          # RFID hardware
python3 test_camera.py        # Camera functionality
python3 test_sync.py          # Network synchronization
```

## Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check MySQL service
sudo systemctl status mysql
sudo systemctl restart mysql

# Verify user permissions
mysql -u binslibal -p -e "SHOW DATABASES;"
```

#### RFID Reader Not Detected  
```bash
# Check serial permissions
sudo usermod -a -G dialout $USER
# Logout/login required

# Test serial connection
ls -la /dev/ttyUSB* /dev/serial*
```

#### Camera Initialization Failed
```bash
# Enable camera interface
sudo raspi-config  # > Interface Options > Camera > Enable

# Check camera detection
vcgencmd get_camera
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Project Tags

`RFID` `Raspberry-Pi` `MySQL` `Python` `IoT` `Parking-Management` `Vehicle-Tracking` `Database-Sync` `Hardware-Integration` `Real-Time-Systems`
