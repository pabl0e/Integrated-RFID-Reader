#!/usr/bin/env python3
"""
Automated Database Sync Service for RFID System
Monitors WiFi connectivity and automatically syncs local data to main database
"""

import time
import subprocess
import threading
import logging
import json
import os
import socket
import sys
from datetime import datetime, timedelta
from handheld_db_module import connect_localdb, connect_maindb, sync_violations
from handheld_db_module import add_new_uid  # We'll modify this to also sync RFID tags

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/rfid_sync.log'),
        logging.StreamHandler()
    ]
)

class AutoSyncService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sync_interval = 300  # Check every 5 minutes
        self.last_sync_attempt = None
        self.last_successful_sync = None
        self.min_sync_interval = 60  # Minimum 1 minute between sync attempts
        self.running = True
        self.wifi_connected = False
        self.main_db_reachable = False
        
        # Sync status file
        self.status_file = '/tmp/rfid_sync_status.json'
        
        # Load previous sync status
        self.load_sync_status()
        
    def load_sync_status(self):
        """Load previous sync status from file"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r') as f:
                    status = json.load(f)
                    if 'last_successful_sync' in status:
                        self.last_successful_sync = datetime.fromisoformat(status['last_successful_sync'])
                    self.logger.info(f"Loaded sync status: last successful sync at {self.last_successful_sync}")
        except Exception as e:
            self.logger.warning(f"Could not load sync status: {e}")
    
    def save_sync_status(self):
        """Save current sync status to file"""
        try:
            status = {
                'last_successful_sync': self.last_successful_sync.isoformat() if self.last_successful_sync else None,
                'last_sync_attempt': self.last_sync_attempt.isoformat() if self.last_sync_attempt else None,
                'wifi_connected': self.wifi_connected,
                'main_db_reachable': self.main_db_reachable
            }
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Could not save sync status: {e}")
    
    def check_wifi_connection(self):
        """Check if WiFi is connected and has internet access"""
        try:
            # Check if WiFi interface is up and has an IP
            result = subprocess.run(['iwconfig'], capture_output=True, text=True, timeout=10)
            wifi_up = 'IEEE 802.11' in result.stdout and 'ESSID:' in result.stdout
            
            if not wifi_up:
                return False
            
            # Check internet connectivity by pinging a reliable server
            result = subprocess.run(['ping', '-c', '1', '-W', '3', '8.8.8.8'], 
                                  capture_output=True, timeout=10)
            internet_connected = result.returncode == 0
            
            return wifi_up and internet_connected
            
        except Exception as e:
            self.logger.warning(f"WiFi check failed: {e}")
            return False
    
    def check_main_database_connectivity(self):
        """Check if main database is reachable"""
        try:
            # Try to connect to main database
            conn = connect_maindb()
            if conn:
                # Test with a simple query
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                conn.close()
                return True
            return False
        except Exception as e:
            self.logger.debug(f"Main database connectivity check failed: {e}")
            return False
    
    def sync_rfid_tags(self):
        """Sync RFID tags from local to main database"""
        local_conn = connect_localdb()
        main_conn = connect_maindb()
        
        if not local_conn or not main_conn:
            return {"ok": False, "error": "Database connection failed"}
        
        stats = {
            "uploaded_tags": 0,
            "ok": True
        }
        
        try:
            local_cursor = local_conn.cursor()
            main_cursor = main_conn.cursor()
            
            # Get all local RFID tags
            local_cursor.execute("SELECT * FROM rfid_tags")
            local_tags = local_cursor.fetchall()
            
            if local_tags:
                # Get column names
                columns = [desc[0] for desc in local_cursor.description]
                
                # Prepare insert query for main database
                placeholders = ', '.join(['%s'] * len(columns))
                insert_query = f"INSERT IGNORE INTO rfid_tags ({', '.join(columns)}) VALUES ({placeholders})"
                
                # Insert tags into main database
                for tag in local_tags:
                    try:
                        main_cursor.execute(insert_query, tag)
                        if main_cursor.rowcount > 0:
                            stats["uploaded_tags"] += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to sync tag {tag[1] if len(tag) > 1 else 'unknown'}: {e}")
                
                main_conn.commit()
                self.logger.info(f"Synced {stats['uploaded_tags']} RFID tags to main database")
            
            local_cursor.close()
            main_cursor.close()
            
        except Exception as e:
            stats["ok"] = False
            stats["error"] = str(e)
            self.logger.error(f"RFID tags sync failed: {e}")
        finally:
            try:
                local_conn.close()
                main_conn.close()
            except:
                pass
        
        return stats
    
    def perform_full_sync(self):
        """Perform complete synchronization of all data"""
        self.logger.info("Starting full database synchronization...")
        sync_results = {}
        
        try:
            # Sync violations
            self.logger.info("Syncing violations...")
            violation_result = sync_violations()
            sync_results['violations'] = violation_result
            
            # Sync RFID tags
            self.logger.info("Syncing RFID tags...")
            tags_result = self.sync_rfid_tags()
            sync_results['rfid_tags'] = tags_result
            
            # Check if all syncs were successful
            all_successful = all(result.get('ok', False) for result in sync_results.values())
            
            if all_successful:
                self.last_successful_sync = datetime.now()
                self.logger.info("Full synchronization completed successfully")
                
                # Log sync statistics
                violations_uploaded = sync_results.get('violations', {}).get('uploaded_violations', 0)
                tags_uploaded = sync_results.get('rfid_tags', {}).get('uploaded_tags', 0)
                self.logger.info(f"Sync summary: {violations_uploaded} violations, {tags_uploaded} RFID tags")
                
            else:
                self.logger.error("Some synchronization operations failed")
                for sync_type, result in sync_results.items():
                    if not result.get('ok', False):
                        self.logger.error(f"{sync_type} sync failed: {result.get('error', 'Unknown error')}")
            
            return all_successful
            
        except Exception as e:
            self.logger.error(f"Full sync failed with exception: {e}")
            return False
    
    def should_attempt_sync(self):
        """Determine if we should attempt a sync based on timing and conditions"""
        now = datetime.now()
        
        # Don't sync too frequently
        if (self.last_sync_attempt and 
            now - self.last_sync_attempt < timedelta(seconds=self.min_sync_interval)):
            return False
        
        # Always sync if we've never synced successfully
        if not self.last_successful_sync:
            return True
        
        # Sync if it's been more than the sync interval since last attempt
        if (self.last_sync_attempt and 
            now - self.last_sync_attempt >= timedelta(seconds=self.sync_interval)):
            return True
        
        # Sync if WiFi just came online and we haven't synced recently
        if (self.wifi_connected and self.main_db_reachable and
            now - self.last_successful_sync >= timedelta(seconds=self.min_sync_interval)):
            return True
        
        return False
    
    def monitor_and_sync(self):
        """Main monitoring loop"""
        self.logger.info("Starting automated sync service...")
        
        while self.running:
            try:
                # Check connectivity status
                prev_wifi_status = self.wifi_connected
                prev_db_status = self.main_db_reachable
                
                self.wifi_connected = self.check_wifi_connection()
                self.main_db_reachable = self.check_main_database_connectivity() if self.wifi_connected else False
                
                # Log connectivity changes
                if prev_wifi_status != self.wifi_connected:
                    self.logger.info(f"WiFi status changed: {'Connected' if self.wifi_connected else 'Disconnected'}")
                
                if prev_db_status != self.main_db_reachable:
                    self.logger.info(f"Main database status changed: {'Reachable' if self.main_db_reachable else 'Unreachable'}")
                
                # Attempt sync if conditions are met
                if (self.wifi_connected and self.main_db_reachable and self.should_attempt_sync()):
                    self.last_sync_attempt = datetime.now()
                    self.logger.info("Attempting database synchronization...")
                    
                    success = self.perform_full_sync()
                    if success:
                        self.logger.info("Synchronization completed successfully")
                    else:
                        self.logger.warning("Synchronization completed with errors")
                
                # Save current status
                self.save_sync_status()
                
                # Wait before next check
                time.sleep(30)  # Check every 30 seconds
                
            except KeyboardInterrupt:
                self.logger.info("Sync service interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Sync service error: {e}")
                time.sleep(60)  # Wait longer on error
        
        self.logger.info("Sync service stopped")
    
    def start(self):
        """Start the sync service"""
        try:
            self.monitor_and_sync()
        except Exception as e:
            self.logger.error(f"Sync service failed to start: {e}")
    
    def stop(self):
        """Stop the sync service"""
        self.running = False

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RFID Auto-Sync Service')
    parser.add_argument('--manual-sync', action='store_true', help='Perform one-time manual sync and exit')
    parser.add_argument('--check-status', action='store_true', help='Check sync status and exit')
    
    args = parser.parse_args()
    
    service = AutoSyncService()
    
    if args.manual_sync:
        print("Performing manual synchronization...")
        success = service.perform_full_sync()
        service.save_sync_status()
        sys.exit(0 if success else 1)
    
    elif args.check_status:
        print("=== Sync Status ===")
        print(f"WiFi Connected: {service.check_wifi_connection()}")
        print(f"Main DB Reachable: {service.check_main_database_connectivity()}")
        if service.last_successful_sync:
            print(f"Last Successful Sync: {service.last_successful_sync}")
        else:
            print("Last Successful Sync: Never")
        sys.exit(0)
    
    try:
        service.start()
    except KeyboardInterrupt:
        print("\nShutting down sync service...")
        service.stop()

if __name__ == "__main__":
    main()