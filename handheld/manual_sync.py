#!/usr/bin/env python3
"""
Manual Database Sync Script
Performs immediate synchronization of local data to main database
"""

import sys
import argparse
from datetime import datetime
from handheld_db_module import connect_localdb, connect_maindb, sync_violations

def sync_rfid_tags():
    """Sync RFID tags from local to main database"""
    print("Syncing RFID tags...")
    
    local_conn = connect_localdb()
    main_conn = connect_maindb()
    
    if not local_conn or not main_conn:
        print("❌ Database connection failed")
        return False
    
    try:
        local_cursor = local_conn.cursor()
        main_cursor = main_conn.cursor()
        
        # Get all local RFID tags
        local_cursor.execute("SELECT * FROM rfid_tags")
        local_tags = local_cursor.fetchall()
        
        if not local_tags:
            print("ℹ️  No RFID tags to sync")
            return True
        
        # Get column names
        columns = [desc[0] for desc in local_cursor.description]
        
        # Prepare insert query for main database
        placeholders = ', '.join(['%s'] * len(columns))
        insert_query = f"INSERT IGNORE INTO rfid_tags ({', '.join(columns)}) VALUES ({placeholders})"
        
        uploaded_count = 0
        
        # Insert tags into main database
        for tag in local_tags:
            try:
                main_cursor.execute(insert_query, tag)
                if main_cursor.rowcount > 0:
                    uploaded_count += 1
            except Exception as e:
                print(f"⚠️  Failed to sync tag {tag[1] if len(tag) > 1 else 'unknown'}: {e}")
        
        main_conn.commit()
        print(f"✅ Synced {uploaded_count} RFID tags to main database")
        
        local_cursor.close()
        main_cursor.close()
        
        return True
        
    except Exception as e:
        print(f"❌ RFID tags sync failed: {e}")
        return False
    finally:
        try:
            local_conn.close()
            main_conn.close()
        except:
            pass

def check_connectivity():
    """Check database connectivity"""
    print("Checking database connectivity...")
    
    # Check local database
    local_conn = connect_localdb()
    if local_conn:
        print("✅ Local database: Connected")
        local_conn.close()
    else:
        print("❌ Local database: Failed")
        return False
    
    # Check main database
    main_conn = connect_maindb()
    if main_conn:
        print("✅ Main database: Connected")
        main_conn.close()
    else:
        print("❌ Main database: Failed")
        return False
    
    return True

def get_sync_stats():
    """Get statistics about local data to be synced"""
    print("Checking local data to sync...")
    
    local_conn = connect_localdb()
    if not local_conn:
        print("❌ Cannot connect to local database")
        return
    
    try:
        cursor = local_conn.cursor()
        
        # Check violations
        cursor.execute("SELECT COUNT(*) FROM violations")
        violations_count = cursor.fetchone()[0]
        print(f"📊 Local violations: {violations_count}")
        
        # Check RFID tags
        cursor.execute("SELECT COUNT(*) FROM rfid_tags")
        tags_count = cursor.fetchone()[0]
        print(f"📊 Local RFID tags: {tags_count}")
        
        cursor.close()
        
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
    finally:
        local_conn.close()

def perform_full_sync():
    """Perform complete synchronization"""
    print(f"🔄 Starting manual sync at {datetime.now()}")
    print("=" * 50)
    
    # Check connectivity first
    if not check_connectivity():
        print("❌ Sync aborted due to connectivity issues")
        return False
    
    # Get stats
    get_sync_stats()
    print()
    
    success = True
    
    # Sync violations
    try:
        print("Syncing violations...")
        result = sync_violations()
        if result.get('ok', False):
            uploaded = result.get('uploaded_violations', 0)
            print(f"✅ Violations sync completed: {uploaded} records uploaded")
        else:
            print(f"❌ Violations sync failed: {result.get('error', 'Unknown error')}")
            success = False
    except Exception as e:
        print(f"❌ Violations sync failed: {e}")
        success = False
    
    # Sync RFID tags
    try:
        if not sync_rfid_tags():
            success = False
    except Exception as e:
        print(f"❌ RFID tags sync failed: {e}")
        success = False
    
    print("=" * 50)
    if success:
        print(f"🎉 Manual sync completed successfully at {datetime.now()}")
    else:
        print(f"⚠️  Manual sync completed with errors at {datetime.now()}")
    
    return success

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Manual Database Sync')
    parser.add_argument('--check', action='store_true', help='Check connectivity only')
    parser.add_argument('--stats', action='store_true', help='Show sync statistics only')
    parser.add_argument('--violations-only', action='store_true', help='Sync violations only')
    parser.add_argument('--tags-only', action='store_true', help='Sync RFID tags only')
    
    args = parser.parse_args()
    
    if args.check:
        check_connectivity()
    elif args.stats:
        get_sync_stats()
    elif args.violations_only:
        print("Syncing violations only...")
        result = sync_violations()
        if result.get('ok', False):
            print(f"✅ Violations sync completed: {result.get('uploaded_violations', 0)} records")
        else:
            print(f"❌ Violations sync failed: {result.get('error', 'Unknown error')}")
    elif args.tags_only:
        sync_rfid_tags()
    else:
        perform_full_sync()

if __name__ == "__main__":
    main()