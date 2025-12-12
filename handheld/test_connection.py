import socket
import mysql.connector
from handheld_db_module import connect_maindb, connect_localdb

# Configuration
TARGET_IP = '10.36.255.248'
TARGET_PORT = 3306

def check_network_port():
    print(f"\n--- 1. NETWORK CHECK ({TARGET_IP}:{TARGET_PORT}) ---")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3) # 3 second timeout
    try:
        result = sock.connect_ex((TARGET_IP, TARGET_PORT))
        if result == 0:
            print("✅ SUCCESS: Port 3306 is OPEN. Network is good.")
            return True
        else:
            print(f"❌ FAILED: Port is closed or unreachable (Error code: {result}).")
            print("   -> Check Windows Firewall on the laptop.")
            print("   -> Check if both devices are on the same Wi-Fi.")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    finally:
        sock.close()

def check_db_login():
    print("\n--- 2. DATABASE LOGIN CHECK ---")
    conn = connect_maindb()
    if conn:
        print(f"✅ SUCCESS: Logged into Main DB at {TARGET_IP}!")
        print(f"   Server Info: {conn.get_server_info()}")
        conn.close()
    else:
        print("❌ FAILED: Network is okay, but Login failed.")
        print("   -> Check if user 'binslibal' exists on the Laptop.")
        print("   -> Check if the password on the Laptop is 'Vinceleval423!'")
        print("   -> Check if user 'binslibal' has permission to connect from '%' or this IP.")

if __name__ == "__main__":
    if check_network_port():
        check_db_login()
    else:
        print("\nSkipping DB login check because the network port is blocked.")
