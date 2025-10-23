# RFID Database Auto-Sync System

This system provides automated synchronization of local RFID data (violations and RFID tags) to the main database when WiFi connectivity is available.

## Features

- **Automatic WiFi Detection**: Monitors WiFi connectivity and internet access
- **Smart Sync Timing**: Syncs when connected, with configurable intervals
- **Comprehensive Data Sync**: Syncs both violations and RFID tags
- **Robust Error Handling**: Handles connection failures gracefully
- **Status Logging**: Detailed logging of sync operations
- **Manual Control**: Manual sync options for immediate synchronization
- **System Service**: Runs automatically on boot

## Installation

### 1. Install as System Service (Recommended)

```bash
# Make control script executable
chmod +x sync_control.sh

# Install the service (requires sudo)
sudo ./sync_control.sh install

# Start the service
sudo ./sync_control.sh start
```

### 2. Manual Installation

```bash
# Copy service file
sudo cp rfid-autosync.service /etc/systemd/system/

# Create log file
sudo touch /var/log/rfid_sync.log
sudo chown pi:pi /var/log/rfid_sync.log

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable rfid-autosync
sudo systemctl start rfid-autosync
```

## Usage

### Service Control

```bash
# Check service status
./sync_control.sh status

# View live logs
./sync_control.sh logs

# Restart service
sudo ./sync_control.sh restart

# Stop service
sudo ./sync_control.sh stop

# Uninstall service
sudo ./sync_control.sh uninstall
```

### Manual Sync

```bash
# Full manual sync
python3 manual_sync.py

# Check connectivity only
python3 manual_sync.py --check

# Show sync statistics
python3 manual_sync.py --stats

# Sync violations only
python3 manual_sync.py --violations-only

# Sync RFID tags only
python3 manual_sync.py --tags-only
```

### Direct Service Control

```bash
# Check status with details
python3 auto_sync_service.py --check-status

# Perform one-time sync
python3 auto_sync_service.py --manual-sync
```

## Configuration

### Sync Settings

Edit `auto_sync_service.py` to modify:

```python
self.sync_interval = 300        # Check every 5 minutes
self.min_sync_interval = 60     # Minimum 1 minute between attempts
```

### Database Settings

Sync uses the same database connections as the main application:
- Local DB: `connect_localdb()` - localhost, rfid_vehicle_system
- Main DB: `connect_maindb()` - 192.168.50.149, rfid_vehicle_system

### Log Configuration

- **Service Logs**: `/var/log/rfid_sync.log`
- **Status File**: `/tmp/rfid_sync_status.json`
- **systemd Logs**: `journalctl -u rfid-autosync`

## How It Works

### 1. WiFi Monitoring
- Checks `iwconfig` for WiFi interface status
- Tests internet connectivity with ping to 8.8.8.8
- Verifies main database reachability

### 2. Sync Logic
- **Violations**: Uses existing `sync_violations()` function
- **RFID Tags**: Copies all local tags to main database using `INSERT IGNORE`
- **Timing**: Syncs based on intervals and connectivity changes

### 3. Data Flow
```
Local Database → Auto-Sync Service → Main Database
                      ↓
                 Log Files & Status
```

### 4. Error Handling
- Connection failures are logged but don't stop the service
- Failed sync attempts are retried on the next cycle
- Manual sync is always available as backup

## Sync Status

The system maintains sync status in `/tmp/rfid_sync_status.json`:

```json
{
  "last_successful_sync": "2025-10-22T14:30:00",
  "last_sync_attempt": "2025-10-22T14:35:00", 
  "wifi_connected": true,
  "main_db_reachable": true
}
```

## Troubleshooting

### Service Won't Start
```bash
# Check service status
sudo systemctl status rfid-autosync

# Check logs
journalctl -u rfid-autosync -f

# Verify file permissions
ls -la /home/pi/Integrated-RFID-Reader/handheld/auto_sync_service.py
```

### Sync Failures
```bash
# Test connectivity manually
python3 manual_sync.py --check

# Check database access
python3 test_uid_db.py

# View detailed logs
tail -f /var/log/rfid_sync.log
```

### WiFi Detection Issues
```bash
# Test WiFi detection
iwconfig
ping -c 1 8.8.8.8

# Check service logs for WiFi status changes
grep "WiFi status" /var/log/rfid_sync.log
```

## System Requirements

- Python 3.x
- MySQL connector (`pip3 install mysql-connector-python`)
- WiFi interface (`wlan0` or similar)
- systemd (for service mode)
- Root access (for service installation)

## File Structure

```
handheld/
├── auto_sync_service.py      # Main auto-sync service
├── manual_sync.py            # Manual sync script
├── sync_control.sh           # Service control script
├── rfid-autosync.service     # systemd service file
├── handheld_db_module.py     # Database functions
└── README_SYNC.md           # This file
```

## Security Notes

- Database credentials are stored in `handheld_db_module.py`
- Service runs as `pi` user (not root)
- Logs may contain sensitive information - protect accordingly
- Network traffic is unencrypted MySQL protocol

## Integration

The auto-sync system integrates seamlessly with:
- Handheld violation recording (`handheld_main.py`)
- UID registration system (`uid_reader_module.py`)
- Existing database structure and functions
- All data flows through the same database module