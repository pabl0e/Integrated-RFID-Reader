#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Handheld Parking Enforcement System - Violations Database
Records violations directly to violations table with required fields:
- RFID UID, Photo path, Violation type, Location, Device ID, Timestamp
"""

import sys
import time
import os
from PIL import ImageFont
from handheld_rfid_module import scan_rfid_for_enforcement
from handheld_db_module import store_evidence, check_uid, add_new_uid

# DFR0528 UPS HAT Battery Reading
UPS_AVAILABLE = False
UPS_I2C_ADDRESS = 0x10  # DFR0528 I2C address
UPS_SOC_LSB = 0.003906  # LSB for State of Charge (0.003906% per bit)
UPS_VOLTAGE_LSB = 1.25  # LSB for Voltage (1.25mV per bit)
UPS_CHARGING_THRESHOLD = 4000  # Voltage threshold (mV) to detect charging
try:
    import smbus
    # Test connection
    _test_bus = smbus.SMBus(1)
    _test_bus.read_byte_data(UPS_I2C_ADDRESS, 0x01)  # Read PID to verify
    _test_bus.close()
    UPS_AVAILABLE = True
    print("UPS HAT (DFR0528) initialized successfully")
except ImportError:
    print("smbus not available, battery monitoring disabled")
except Exception as e:
    print(f"UPS HAT initialization failed: {e}")

def get_battery_level():
    """
    Read battery percentage from DFR0528 UPS HAT.
    Returns battery percentage (0-100) or -1 if unavailable.
    
    Uses Electric Quantity registers 0x05 (high) and 0x06 (low).
    LSB = 0.003906% per the datasheet.
    """
    if not UPS_AVAILABLE:
        return -1
    
    bus = None
    try:
        # Create fresh bus connection each time to get updated readings
        bus = smbus.SMBus(1)
        
        # Read SOC (State of Charge) registers
        soc_high = bus.read_byte_data(UPS_I2C_ADDRESS, 0x05)
        soc_low = bus.read_byte_data(UPS_I2C_ADDRESS, 0x06)
        
        # Calculate percentage: (high << 8 | low) * LSB
        raw_soc = (soc_high << 8) | soc_low
        percentage = int(raw_soc * UPS_SOC_LSB)
        
        # Clamp to valid range
        if percentage > 100:
            percentage = 100
        elif percentage < 0:
            percentage = 0
            
        return percentage
    except Exception as e:
        print(f"Battery read error: {e}")
        return -1
    finally:
        if bus:
            try:
                bus.close()
            except:
                pass

def get_battery_voltage():
    """
    Read battery voltage from DFR0528 UPS HAT.
    Returns voltage in mV or -1 if unavailable.
    
    Uses Voltage registers 0x03 (high) and 0x04 (low).
    LSB = 1.25mV per the datasheet.
    """
    if not UPS_AVAILABLE:
        return -1
    
    bus = None
    try:
        bus = smbus.SMBus(1)
        
        # Read voltage registers
        v_high = bus.read_byte_data(UPS_I2C_ADDRESS, 0x03)
        v_low = bus.read_byte_data(UPS_I2C_ADDRESS, 0x04)
        
        # Calculate voltage: (high << 8 | low) * LSB mV
        raw_voltage = (v_high << 8) | v_low
        voltage_mv = int(raw_voltage * UPS_VOLTAGE_LSB)
        
        return voltage_mv
    except Exception as e:
        print(f"Voltage read error: {e}")
        return -1
    finally:
        if bus:
            try:
                bus.close()
            except:
                pass

def is_charging():
    """
    Detect if the UPS HAT is charging.
    Charging is detected when voltage exceeds the charging threshold.
    """
    voltage = get_battery_voltage()
    if voltage < 0:
        return False
    return voltage > UPS_CHARGING_THRESHOLD

def get_battery_icon(level):
    """Return a text icon based on battery level"""
    if level < 0:
        return "[???]"
    elif level <= 10:
        return "[!  ]"  # Critical
    elif level <= 25:
        return "[=  ]"  # Low
    elif level <= 50:
        return "[== ]"  # Medium
    elif level <= 75:
        return "[===]"  # Good
    else:
        return "[===]"  # Full

# Add delay for SPI interface initialization on startup
print("Initializing SPI interface for OLED...")
time.sleep(10)  # Allow SPI interface to stabilize

# Try to import OLED module
try:
    from OLED import Clear_Screen, Draw_All_Elements, Display_Image
    OLED_AVAILABLE = True
    print("OLED module loaded successfully")
    # Additional delay after OLED module load
    time.sleep(1)
except ImportError:
    OLED_AVAILABLE = False
    print("OLED module not available, using console output only")
    
    # Fallback functions for when OLED is not available
    def Clear_Screen():
        print("OLED: Clear Screen")
    
    def Draw_All_Elements(elements):
        print("OLED: Drawing elements:")
        for element in elements:
            if element[0] == 'text':
                print(f"  Text: {element[1][2]}")
            elif element[0] == 'rectangle':
                print(f"  Rectangle at {element[1]}")
    
    def Display_Image(img):
        print("OLED: Displaying image")

# Try to import camera module
try:    
    from picamera2 import Picamera2
    CAMERA_AVAILABLE = True
    print("Camera module loaded successfully")
except ImportError:
    CAMERA_AVAILABLE = False
    print("Camera module not available, using mock camera")

# Camera and menu functions
def show_main_menu_with_camera():
    """Show main menu and wait for user to press CENTER button to continue"""
    print("=== MAIN MENU ===")
    
    try:
        from PIL import ImageFont
        
        try:
            font = ImageFont.load_default()
        except Exception:   
            font = None
        
        # Try to import GPIO for button handling
        try:
            import RPi.GPIO as GPIO
            GPIO_AVAILABLE = True
            
            # Set up GPIO pins
            UP_PIN = 4      # GPIO 4 (Pin 7)
            DOWN_PIN = 27   # GPIO 27 (Pin 13)
            CENTER_PIN = 17 # GPIO 17 (Pin 11)
            BACK_PIN = 26   # GPIO 26 (Pin 37)
            
            # Initialize GPIO
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup([UP_PIN, DOWN_PIN, CENTER_PIN, BACK_PIN], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                print("GPIO buttons initialized for main menu")
            except Exception as gpio_error:
                print(f"GPIO setup error: {gpio_error}")
                GPIO_AVAILABLE = False
            
        except ImportError:
            print("RPi.GPIO not available, using keyboard input")
            GPIO_AVAILABLE = False
        
        # Initialize camera first
        picam2 = None
        if CAMERA_AVAILABLE:
            try:
                picam2 = Picamera2()
                picam2.start()
                print("Camera initialized successfully")
            except Exception as e:
                print(f"Camera initialization failed: {e}")
                picam2 = None
        else:
            print("Using mock camera")
        
        # Show main menu screen
        def draw_main_menu():
            # Get battery level and charging status
            battery = get_battery_level()
            charging = is_charging()
            
            if battery >= 0:
                if charging:
                    battery_text = f"Batt: {battery}% CHG"
                    battery_color = 'cyan'
                else:
                    battery_text = f"Batt: {battery}%"
                    battery_color = 'green' if battery > 25 else ('yellow' if battery > 10 else 'red')
            else:
                battery_text = "Batt: N/A"
                battery_color = 'white'
            
            elements_to_draw = [
                ('text', (10, 5, "PARKING", font), {'fill': 'white'}),
                ('text', (10, 18, "VIOLATIONS", font), {'fill': 'white'}),
                ('text', (10, 31, "ENFORCEMENT", font), {'fill': 'white'}),
                ('text', (10, 48, "RIGHT: Start", font), {'fill': 'cyan'}),
                ('text', (10, 61, "LEFT: UID Reg", font), {'fill': 'blue'}),
                ('text', (10, 74, "UP+DOWN: Exit", font), {'fill': 'red'}),
                ('text', (10, 90, battery_text, font), {'fill': battery_color}),
                ('text', (10, 105, "Ready!", font), {'fill': 'white'})
            ]
            
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
        
        # Show the menu
        draw_main_menu()
        
        if GPIO_AVAILABLE:
            print("Press CENTER to start enforcement, BACK for UID registration, UP+DOWN to exit")
            
            last_refresh = time.time()
            REFRESH_INTERVAL = 5  # Refresh battery display every 5 seconds
            
            while True:
                # Periodically refresh display to update battery status
                if time.time() - last_refresh >= REFRESH_INTERVAL:
                    draw_main_menu()
                    last_refresh = time.time()
                
                # Read button states
                center_state = GPIO.input(CENTER_PIN)
                back_state = GPIO.input(BACK_PIN)
                up_state = GPIO.input(UP_PIN)
                down_state = GPIO.input(DOWN_PIN)
                
                # Check for exit combination (UP + DOWN)
                if up_state == GPIO.HIGH and down_state == GPIO.HIGH:
                    print("UP+DOWN buttons pressed - Exiting system")
                    time.sleep(0.5)  # Debounce
                    return picam2, False
                
                elif center_state == GPIO.HIGH:
                    print("CENTER button pressed - Starting enforcement!")
                    time.sleep(0.5)  # Debounce
                    return picam2, True
                
                elif back_state == GPIO.HIGH:
                    print("BACK button pressed - Starting UID registration")
                    time.sleep(0.5)  # Debounce
                    
                    # Run UID registration
                    run_uid_registration()
                    
                    # Redraw main menu after UID registration
                    draw_main_menu()
                    continue
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
        else:
            # Keyboard fallback for testing
            print("Press Enter to start enforcement, 'u' for UID registration, 'q' to exit:")
            user_input = input().strip().lower()
            if user_input == 'q':
                print("Exiting system")
                return picam2, False
            elif user_input == 'u':
                print("Starting UID registration!")
                run_uid_registration()
                # Loop back to main menu
                return show_main_menu_with_camera()
            else:
                print("Starting enforcement!")
                return picam2, True
                
    except Exception as e:
        print(f"Main menu error: {e}")
        # Return camera and True to continue despite errors
        return picam2 if 'picam2' in locals() else None, True

def run_rfid_scanner():
    """Run RFID scanner with dedicated scanning screen"""
    print("=== RFID SCANNER ===")
    
    try:
        from PIL import ImageFont
        
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        

        
        # Show RFID scanning screen
        def draw_rfid_screen():
            elements_to_draw = [
                ('text', (15, 15, "RFID SCANNER", font), {'fill': 'white'}),
                ('text', (20, 35, "Place RFID tag", font), {'fill': 'cyan'}),
                ('text', (20, 50, "near reader...", font), {'fill': 'cyan'}),
                ('text', (10, 75, "Scanning...", font), {'fill': 'yellow'})
            ]
            
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
        

        
        # Show the scanning screen
        draw_rfid_screen()
        
        print("RFID Scanner active - attempting RFID scan")
        
        # Try to use the actual RFID scanner
        try:
            scanned_uid = scan_rfid_for_enforcement()
            if scanned_uid:
                # Show success screen
                success_elements = [
                    ('text', (15, 15, "RFID FOUND!", font), {'fill': 'green'}),
                    ('text', (10, 35, f"UID: {scanned_uid[:16]}", font), {'fill': 'white'}),
                    ('text', (10, 50, f"{scanned_uid[16:] if len(scanned_uid) > 16 else ''}", font), {'fill': 'white'}),
                    ('text', (15, 75, "Proceeding...", font), {'fill': 'green'})
                ]
                
                if OLED_AVAILABLE:
                    Clear_Screen()
                    Draw_All_Elements(success_elements)
                else:
                    Draw_All_Elements(success_elements)
                
                time.sleep(2)  # Show success for 2 seconds
                return scanned_uid
        except Exception as e:
            print(f"RFID scanner error: {e}")
        
        # Show RFID scan failed screen
        failed_elements = [
            ('text', (10, 15, "RFID SCAN", font), {'fill': 'white'}),
            ('text', (15, 30, "FAILED", font), {'fill': 'red'}),
            ('text', (10, 50, "No tag detected", font), {'fill': 'yellow'}),
            ('text', (10, 65, "Please try", font), {'fill': 'white'}),
            ('text', (10, 80, "again", font), {'fill': 'white'})
        ]
        
        if OLED_AVAILABLE:
            Clear_Screen()
            Draw_All_Elements(failed_elements)
        else:
            Draw_All_Elements(failed_elements)
        
        print("RFID scan failed. System will return None.")
        time.sleep(3)
        return None
            
    except Exception as e:
        print(f"RFID scanner error: {e}")
        return None

def run_photo_capture(picam2):
    """Capture evidence photo with preview - SAVES TO ABSOLUTE PATH"""
    print("=== PHOTO CAPTURE ===")
    
    try:
        from PIL import ImageFont
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        
        # Try to import GPIO for button handling
        try:
            import RPi.GPIO as GPIO
            GPIO_AVAILABLE = True
            
            CENTER_PIN = 17 # GPIO 17 (Pin 11)
            BACK_PIN = 26   # GPIO 26 (Pin 37)
            
            try:
                try:
                    GPIO.setmode(GPIO.BCM)
                except:
                    pass
                GPIO.setup([CENTER_PIN, BACK_PIN], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            except Exception as gpio_error:
                print(f"GPIO setup error: {gpio_error}")
                GPIO_AVAILABLE = False
                
        except ImportError:
            print("RPi.GPIO not available, using keyboard input fallback")
            GPIO_AVAILABLE = False
        
        # Show "Ready to capture" screen - wait for CENTER button
        def draw_ready_to_capture_screen():
            elements_to_draw = [
                ('text', (10, 10, "PHOTO CAPTURE", font), {'fill': 'white'}),
                ('text', (10, 30, "Aim camera at", font), {'fill': 'orange'}),
                ('text', (10, 45, "the violation", font), {'fill': 'orange'}),
                ('text', (10, 65, "RIGHT: Capture", font), {'fill': 'cyan'}),  # Shows as yellow on BGR
                ('text', (10, 80, "LEFT: Cancel", font), {'fill': 'blue'}),  # Shows as red on BGR
                ('text', (10, 100, "Ready...", font), {'fill': 'green'})
            ]
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
        
        # Wait for user to press CENTER before capturing
        draw_ready_to_capture_screen()
        
        if GPIO_AVAILABLE:
            print("Press CENTER to capture photo, BACK to cancel")
            while True:
                center_state = GPIO.input(CENTER_PIN)
                back_state = GPIO.input(BACK_PIN)
                
                if center_state == GPIO.HIGH:
                    print("CENTER button pressed - Capturing photo...")
                    time.sleep(0.3)  # Debounce
                    break
                
                elif back_state == GPIO.HIGH:
                    print("BACK button pressed - Photo capture cancelled")
                    time.sleep(0.3)  # Debounce
                    return False, None
                
                time.sleep(0.1)
        else:
            # Keyboard fallback
            print("Press Enter to capture photo, 'q' to cancel:")
            user_input = input().strip().lower()
            if user_input == 'q':
                print("Photo capture cancelled")
                return False, None
        
        # Show photo capture screen
        def draw_photo_capture_screen():
            elements_to_draw = [
                ('text', (10, 15, "PHOTO CAPTURE", font), {'fill': 'white'}),
                ('text', (15, 35, "Taking photo", font), {'fill': 'cyan'}),
                ('text', (15, 50, "for evidence", font), {'fill': 'cyan'}),
                ('text', (20, 75, "Capturing...", font), {'fill': 'yellow'}),
                ('text', (15, 95, "Please wait", font), {'fill': 'white'})
            ]
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
        
        # Show capture screen
        draw_photo_capture_screen()
        
        # --- PATH FIX: Ensure we save to the absolute directory of the script ---
        # 1. Get the directory where THIS script is located
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Create absolute path for evidences folder
        evidences_dir = os.path.join(base_dir, "evidences")
        os.makedirs(evidences_dir, exist_ok=True)
        
        # 3. Generate filename
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        photo_filename = f"evidence_{timestamp}.jpg"
        
        # 4. Create FULL path for file saving (e.g., /home/pi/.../evidences/img.jpg)
        full_photo_path = os.path.join(evidences_dir, photo_filename)
        
        # 5. Create RELATIVE path for Database (e.g., evidences/img.jpg)
        # This is what goes into the DB so the sync script can reconstruct it later
        db_photo_path = os.path.join("evidences", photo_filename)
        
        # Show photo preview screen
        def draw_photo_preview_screen(path_to_display):
            try:
                if OLED_AVAILABLE and os.path.exists(path_to_display):
                    print(f"Displaying captured photo: {path_to_display}")
                    Clear_Screen()
                    try:
                        from PIL import Image
                        captured_image = Image.open(path_to_display)
                        Display_Image(captured_image)
                    except Exception as load_error:
                        print(f"Could not load image: {load_error}")
                else:
                    elements_to_draw = [
                        ('text', (10, 20, "PHOTO PREVIEW", font), {'fill': 'white'}),
                        ('text', (15, 40, "Image captured", font), {'fill': 'green'}),
                        ('text', (10, 60, "Saved OK", font), {'fill': 'green'})
                    ]
                    Draw_All_Elements(elements_to_draw)
            except Exception as img_error:
                print(f"Image preview error: {img_error}")

        # Show failed screen
        def draw_photo_failed_screen():
            elements_to_draw = [
                ('text', (10, 15, "PHOTO CAPTURE", font), {'fill': 'white'}),
                ('text', (15, 35, "FAILED", font), {'fill': 'red'}),
                ('text', (10, 55, "Using mock", font), {'fill': 'yellow'})
            ]
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)

        # CAPTURE LOGIC
        if picam2 and CAMERA_AVAILABLE:
            try:
                time.sleep(1)
                # Save to the ABSOLUTE path
                picam2.capture_file(full_photo_path)
                print(f"Photo captured to: {full_photo_path}")
                
                # Rotate the image 90 degrees clockwise to correct orientation
                try:
                    from PIL import Image
                    img = Image.open(full_photo_path)
                    img_rotated = img.rotate(90, expand=True)
                    img_rotated.save(full_photo_path)
                    print("Image rotated 90° clockwise for correct orientation")
                except Exception as rotate_error:
                    print(f"Image rotation failed (using original): {rotate_error}")
                
                draw_photo_preview_screen(full_photo_path)
                time.sleep(3)
                
                # Return True and the RELATIVE path for the DB
                return True, db_photo_path
            except Exception as e:
                print(f"Camera capture failed: {e}")
                draw_photo_failed_screen()
                time.sleep(2)
        else:
            # Mock camera logic
            time.sleep(1)
            draw_photo_failed_screen()
            time.sleep(1)
        
        # Fallback / Mock file creation
        try:
            with open(full_photo_path, 'w') as f:
                f.write(f"Mock evidence photo - {timestamp}")
            print(f"Mock photo created at: {full_photo_path}")
            
            elements_to_draw = [
                ('text', (10, 20, "MOCK SAVED", font), {'fill': 'yellow'}),
                ('text', (10, 40, "No Camera", font), {'fill': 'red'})
            ]
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
            time.sleep(2)
            
            return True, db_photo_path
            
        except Exception as e:
            print(f"Failed to create photo file: {e}")
            return False, None
            
    except Exception as e:
        print(f"Photo capture error: {e}")
        return False, None

def run_violation_selector():
    """Run violation selector with button interface"""
    print("=== VIOLATION SELECTOR ===")
    
    try:
        from PIL import ImageFont
        
        # Try to import GPIO for button handling
        try:
            import RPi.GPIO as GPIO
            GPIO_AVAILABLE = True
            
            # Set up GPIO pins based on the mapping table
            UP_PIN = 4      # GPIO 4 (Pin 7)
            DOWN_PIN = 27   # GPIO 27 (Pin 13)
            CENTER_PIN = 17 # GPIO 17 (Pin 11)
            BACK_PIN = 26   # GPIO 26 (Pin 37)
            
            # Initialize GPIO only once
            try:
                try:
                    GPIO.setmode(GPIO.BCM)
                except:
                    pass
                    
                GPIO.setup([UP_PIN, DOWN_PIN, CENTER_PIN, BACK_PIN], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                print("GPIO buttons initialized successfully")
                
            except Exception as gpio_error:
                print(f"GPIO setup error: {gpio_error}")
                GPIO_AVAILABLE = False
            
        except ImportError:
            print("RPi.GPIO not available, using keyboard input fallback")
            GPIO_AVAILABLE = False
        
        # Only TWO violation types for the entire project
        violations = [
            "Parking in\nNo Parking Zones",
            "Unauthorized Parking\nin designated spots"
        ]
        selected_index = 0
        
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        
        def draw_menu():
            """Draw the violation selection menu"""
            elements_to_draw = []
            elements_to_draw.append(('text', (5, 2, "SELECT VIOLATION:", font), {'fill': 'white'}))
            
            # Draw both violation options with proper spacing
            # Option 1 starts at y=18, Option 2 starts at y=55
            y_positions = [18, 55]
            
            for i, violation in enumerate(violations):
                y_pos = y_positions[i]
                lines = violation.split('\n')
                
                if i == selected_index:
                    # Highlight selected option with taller rectangle
                    elements_to_draw.append(('rectangle', (3, y_pos - 2, 122, 28), {'fill': 'yellow'}))
                    # Draw both lines
                    elements_to_draw.append(('text', (5, y_pos, lines[0], font), {'fill': 'black'}))
                    if len(lines) > 1:
                        elements_to_draw.append(('text', (5, y_pos + 12, lines[1], font), {'fill': 'black'}))
                else:
                    # Draw both lines
                    elements_to_draw.append(('text', (5, y_pos, lines[0], font), {'fill': 'white'}))
                    if len(lines) > 1:
                        elements_to_draw.append(('text', (5, y_pos + 12, lines[1], font), {'fill': 'white'}))
            
            # Draw instructions at bottom
            elements_to_draw.append(('text', (5, 92, "UP/DOWN: Navigate", font), {'fill': 'red'}))
            elements_to_draw.append(('text', (5, 107, "RIGHT: Select", font), {'fill': 'cyan'}))
            
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw) 
        
        # Main selection loop
        print("Available violations:")
        for i, violation in enumerate(violations):
            print(f"{i+1}. {violation}")
        
        if GPIO_AVAILABLE:
            print("Use UP/DOWN buttons to navigate, CENTER to select")
            draw_menu()
            
            while True:
                # Read button states
                up_state = GPIO.input(UP_PIN)
                down_state = GPIO.input(DOWN_PIN)
                center_state = GPIO.input(CENTER_PIN)
                
                if up_state == GPIO.HIGH:
                    selected_index = (selected_index - 1) % len(violations)
                    draw_menu()
                    time.sleep(0.3)  # Debounce
                
                elif down_state == GPIO.HIGH:
                    selected_index = (selected_index + 1) % len(violations)
                    draw_menu()
                    time.sleep(0.3)  # Debounce
                
                elif center_state == GPIO.HIGH:
                    print(f"Selected: {violations[selected_index]}")
                    break
                
                time.sleep(0.1)
        else:
            # Keyboard fallback
            print("Enter violation number (1 or 2):")
            try:
                choice = int(input()) - 1
                if 0 <= choice < len(violations):
                    selected_index = choice
                else:
                    print("Invalid choice, using first violation")
                    selected_index = 0
            except ValueError:
                print("Invalid input, using first violation")
                selected_index = 0
        
        # Show selection confirmation
        selected_violation = violations[selected_index]
        elements_to_draw = [
            ('text', (10, 10, "SELECTED:", font), {'fill': 'green'})
        ]
        
        # Display selected violation (split for long text)
        if len(selected_violation) > 20:
            lines = selected_violation.split()
            mid = len(lines) // 2
            line1 = " ".join(lines[:mid])
            line2 = " ".join(lines[mid:])
            elements_to_draw.append(('text', (10, 30, line1, font), {'fill': 'yellow'}))
            elements_to_draw.append(('text', (10, 45, line2, font), {'fill': 'yellow'}))
        else:
            elements_to_draw.append(('text', (10, 30, selected_violation, font), {'fill': 'yellow'}))
        
        elements_to_draw.append(('text', (10, 80, "Violation Type", font), {'fill': 'green'}))
        elements_to_draw.append(('text', (10, 95, "Confirmed!", font), {'fill': 'green'}))

        if OLED_AVAILABLE:
            Clear_Screen()
            Draw_All_Elements(elements_to_draw)
        else:
            Draw_All_Elements(elements_to_draw)
        
        time.sleep(3)
        
        print("Violation selection completed.")
        return selected_violation
        
    except Exception as e:
        print(f"Violation selector error: {e}")
        return None

def run_uid_registration():
    """Run UID registration process with OLED interface"""
    print("=== UID REGISTRATION ===")
    
    try:
        from PIL import ImageFont
        
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        
        # Try to import GPIO for button handling
        try:
            import RPi.GPIO as GPIO
            GPIO_AVAILABLE = True
            
            # Set up GPIO pins
            CENTER_PIN = 17 # GPIO 17 (Pin 11) 
            BACK_PIN = 26   # GPIO 26 (Pin 37)
            
            # Initialize GPIO only once
            try:
                try:
                    GPIO.setmode(GPIO.BCM)
                except:
                    pass
                    
                GPIO.setup([CENTER_PIN, BACK_PIN], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                print("GPIO buttons initialized for UID registration")
                
            except Exception as gpio_error:
                print(f"GPIO setup error: {gpio_error}")
                GPIO_AVAILABLE = False
            
        except ImportError:
            print("RPi.GPIO not available, using keyboard input fallback")
            GPIO_AVAILABLE = False
        
        # Show UID registration intro screen
        def draw_uid_intro():
            elements_to_draw = [
                ('text', (10, 10, "UID", font), {'fill': 'white'}),
                ('text', (10, 25, "REGISTRATION", font), {'fill': 'white'}),
                ('text', (10, 40, "MODE", font), {'fill': 'white'}),
                ('text', (10, 60, "RIGHT: Scan UID", font), {'fill': 'cyan'}),
                ('text', (10, 75, "LEFT: Exit to Menu", font), {'fill': 'blue'}),
                ('text', (10, 95, "Ready to register", font), {'fill': 'white'})
            ]
            
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
        
        # Show UID scanning screen
        def draw_uid_scanning():
            elements_to_draw = [
                ('text', (15, 15, "UID SCANNER", font), {'fill': 'white'}),
                ('text', (20, 35, "Place RFID tag", font), {'fill': 'cyan'}),
                ('text', (20, 50, "near reader...", font), {'fill': 'cyan'}),
                ('text', (10, 75, "Scanning...", font), {'fill': 'yellow'})
            ]
            
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
        
        # Show UID registration result
        def draw_uid_result(uid, result):
            if result['success'] and result['new_uid']:
                # New UID registered successfully
                elements_to_draw = [
                    ('text', (10, 10, "NEW UID", font), {'fill': 'green'}),
                    ('text', (10, 25, "REGISTERED!", font), {'fill': 'green'}),
                    ('text', (5, 45, f"UID: {uid[:16]}", font), {'fill': 'white'}),
                    ('text', (5, 60, f"{uid[16:] if len(uid) > 16 else ''}", font), {'fill': 'white'}),
                    ('text', (10, 80, "Added to system", font), {'fill': 'cyan'})
                ]
            elif result['success'] and not result['new_uid']:
                # UID already exists
                elements_to_draw = [
                    ('text', (10, 10, "UID ALREADY", font), {'fill': 'yellow'}),
                    ('text', (10, 25, "EXISTS", font), {'fill': 'yellow'}),
                    ('text', (5, 45, f"UID: {uid[:16]}", font), {'fill': 'white'}),
                    ('text', (5, 60, f"{uid[16:] if len(uid) > 16 else ''}", font), {'fill': 'white'}),
                    ('text', (10, 80, "Already in system", font), {'fill': 'orange'})
                ]
            else:
                # Registration failed
                elements_to_draw = [
                    ('text', (10, 10, "REGISTRATION", font), {'fill': 'red'}),
                    ('text', (10, 25, "FAILED", font), {'fill': 'red'}),
                    ('text', (5, 45, f"UID: {uid[:16] if uid else 'N/A'}", font), {'fill': 'white'}),
                    ('text', (5, 60, f"{uid[16:] if uid and len(uid) > 16 else ''}", font), {'fill': 'white'}),
                    ('text', (10, 80, "Database error", font), {'fill': 'red'})
                ]
            
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
        
        # Main UID registration loop
        while True:
            # Show intro screen
            draw_uid_intro()
            
            if GPIO_AVAILABLE:
                print("Press CENTER to scan UID, BACK to exit to main menu")
                
                waiting_for_input = True
                while waiting_for_input:
                    center_state = GPIO.input(CENTER_PIN)
                    back_state = GPIO.input(BACK_PIN)
                    
                    if center_state == GPIO.HIGH:
                        print("CENTER button pressed - Starting UID scan")
                        time.sleep(0.5)  # Debounce
                        waiting_for_input = False
                        break
                    
                    elif back_state == GPIO.HIGH:
                        print("BACK button pressed - Exiting UID registration")
                        time.sleep(0.5)  # Debounce
                        return False  # Exit to main menu
                    
                    time.sleep(0.1)
            else:
                # Keyboard fallback
                print("Press Enter to scan UID, 'q' to exit to main menu:")
                user_input = input().strip().lower()
                if user_input == 'q':
                    print("Exiting UID registration")
                    return False  # Exit to main menu
            
            # Show scanning screen
            draw_uid_scanning()
            
            print("UID Scanner active - attempting RFID scan")
            
            # Try to use the actual RFID scanner
            try:
                scanned_uid = scan_rfid_for_enforcement()
                if scanned_uid:
                    print(f"Scanned UID: {scanned_uid}")
                    
                    # Register the UID in the database
                    result = add_new_uid(scanned_uid)
                    print(f"Registration result: {result['message']}")
                    
                    # Show result on OLED
                    draw_uid_result(scanned_uid, result)
                    time.sleep(4)  # Show result for 4 seconds
                    
                    # Continue with more scans
                    continue
                else:
                    # Show scan failed screen
                    failed_elements = [
                        ('text', (10, 15, "UID SCAN", font), {'fill': 'white'}),
                        ('text', (15, 30, "FAILED", font), {'fill': 'red'}),
                        ('text', (10, 50, "No tag detected", font), {'fill': 'yellow'}),
                        ('text', (10, 65, "Try again", font), {'fill': 'white'})
                    ]
                    
                    if OLED_AVAILABLE:
                        Clear_Screen()
                        Draw_All_Elements(failed_elements)
                    else:
                        Draw_All_Elements(failed_elements)
                    
                    print("UID scan failed. Returning to menu.")
                    time.sleep(3)
                    continue
                    
            except Exception as e:
                print(f"UID scanner error: {e}")
                
                # Show error screen
                error_elements = [
                    ('text', (10, 15, "SCANNER", font), {'fill': 'white'}),
                    ('text', (15, 30, "ERROR", font), {'fill': 'red'}),
                    ('text', (10, 50, "Hardware issue", font), {'fill': 'yellow'}),
                    ('text', (10, 75, "Check connection", font), {'fill': 'white'})
                ]
                
                if OLED_AVAILABLE:
                    Clear_Screen()
                    Draw_All_Elements(error_elements)
                else:
                    Draw_All_Elements(error_elements)
                
                time.sleep(3)
                continue
                
    except Exception as e:
        print(f"UID registration error: {e}")
        return False

def main():
    """Main enforcement workflow - Records to violations table"""
    
    # Quick initialization
    print("Handheld Violations System - Initializing...")
    time.sleep(2)  # Reduced from 8 seconds
    print("System ready!")
    
    try:
        from PIL import ImageFont
        
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        
        # Brief startup screen
        elements_to_draw = [
            ('text', (15, 20, "SYSTEM", font), {'fill': 'white'}),
            ('text', (10, 40, "INITIALIZING", font), {'fill': 'white'}),
            ('text', (20, 70, "Loading...", font), {'fill': 'yellow'})
        ]
        if OLED_AVAILABLE:
            Clear_Screen()
            Draw_All_Elements(elements_to_draw)
        else:
            Draw_All_Elements(elements_to_draw)
        time.sleep(1)  # Brief initialization screen
        
        print("=== PARKING VIOLATIONS ENFORCEMENT SYSTEM ===")
        print("Two violation types:")
        print("1. Parking in No Parking Zones")
        print("2. Unauthorized Parking in designated Parking spots")
        
        # Show main menu and pre-warm camera
        picam2, should_continue = show_main_menu_with_camera()
        
        if not should_continue:
            print("System cancelled by user")
            return
        
        # Step 1: RFID Scanning (Required field)
        print("Step 1: Scanning RFID tag (Required)...")
        scanned_uid = run_rfid_scanner()
        
        if not scanned_uid:
            print("RFID scanning failed. Cannot proceed without RFID UID.")
            return
        
        print(f"RFID UID captured: {scanned_uid}")
        
        # Check for previous violations
        uid_info = check_uid(scanned_uid)
        if uid_info['previous_violations'] > 0:
            print(f"WARNING: This RFID has {uid_info['previous_violations']} previous violations")
        
        # Step 2: Photo capture (Required field)
        print("Step 2: Taking evidence photo (Required)...")
        photo_success, photo_path = run_photo_capture(picam2)
        
        if not photo_success or not photo_path:
            print("Photo capture failed. Cannot proceed without evidence photo.")
            return
        
        print(f"Photo captured: {photo_path}")
        
        # Step 3: Violation type selection (Required field) - Only 2 options
        print("Step 3: Selecting violation type (Required)...")
        selected_violation = run_violation_selector()
        
        if not selected_violation:
            print("Violation selection failed. Cannot proceed without violation type.")
            return
        
        print(f"Violation selected: {selected_violation}")
        
        # Step 4: Store in violations table with all required fields
        print("Step 4: Recording violation in database...")
        
        # Show storing message
        elements_to_draw = [
            ('text', (10, 20, "RECORDING", font), {'fill': 'yellow'}),
            ('text', (10, 35, "PARKING", font), {'fill': 'yellow'}),
            ('text', (10, 50, "VIOLATION", font), {'fill': 'yellow'}),
            ('text', (10, 70, "Please wait...", font), {'fill': 'white'})
        ]
        if OLED_AVAILABLE:
            Clear_Screen()
            Draw_All_Elements(elements_to_draw)
        else:
            Draw_All_Elements(elements_to_draw)
        
        # Store violation with all required fields for handheld Pi
        result = store_evidence(
            rfid_uid=scanned_uid,          # Required: RFID tag UID
            photo_path=photo_path,         # Required: Evidence photo path
            violation_type=selected_violation,  # Required: One of 2 violation types
            location="Campus Parking Area",     # Required: Location info
            device_id="HANDHELD_01"            # Required: Device identifier
        )
        
        if result["ok"]:
            print(f"Parking violation recorded successfully! ID: {result['evidence_id']}")
            # Show success message
            elements_to_draw = [
                ('text', (10, 10, "PARKING", font), {'fill': 'green'}),
                ('text', (10, 25, "VIOLATION", font), {'fill': 'green'}),
                ('text', (10, 40, "RECORDED", font), {'fill': 'green'}),
                ('text', (10, 60, f"ID: {result['evidence_id']}", font), {'fill': 'white'}),
                ('text', (10, 75, "Enforcement", font), {'fill': 'cyan'}),
                ('text', (10, 90, "Complete!", font), {'fill': 'cyan'})
            ]
        else:
            print(f"Failed to record violation: {result['error']}")
            # Show error message
            elements_to_draw = [
                ('text', (10, 30, "RECORDING", font), {'fill': 'red'}),
                ('text', (10, 50, "FAILED", font), {'fill': 'red'}),
                ('text', (10, 70, "Check database", font), {'fill': 'yellow'})
            ]
        
        if OLED_AVAILABLE:
            Clear_Screen()
            Draw_All_Elements(elements_to_draw)
        else:
            Draw_All_Elements(elements_to_draw)
        
        time.sleep(3)  # Show initial result screen
        
        # Show detailed violation log summary on OLED
        if OLED_AVAILABLE:
            # Determine database type from storage method
            db_type = "MySQL" if result.get('storage_method', '').lower() == 'mysql' else "Local"
            db_status = "OK Saved" if result["ok"] else "X Failed"
            
            # Truncate UID for display (show first 8 characters)
            display_uid = scanned_uid[:8] if len(scanned_uid) > 8 else scanned_uid
            
            # Truncate violation type for display
            violation_short = selected_violation[:20] if len(selected_violation) > 20 else selected_violation
            if len(selected_violation) > 20:
                violation_lines = selected_violation.split()
                mid = len(violation_lines) // 2
                violation_line1 = " ".join(violation_lines[:mid])[:16]
                violation_line2 = " ".join(violation_lines[mid:])[:16]
            else:
                violation_line1 = violation_short
                violation_line2 = ""
            
            # Get violation ID for tracking
            violation_id = result.get('evidence_id', 'N/A')
            display_id = str(violation_id)[:8] if len(str(violation_id)) > 8 else str(violation_id)
            
            # Get previous violations count for this UID
            previous_count = uid_info.get('previous_violations', 0)
            
            summary_elements = [
                ('text', (5, 5, "VIOLATION LOG", font), {'fill': 'white'}),
                ('text', (5, 16, f"ID: {display_id}", font), {'fill': 'green'}),
                ('text', (5, 26, f"UID: {display_uid}", font), {'fill': 'cyan'}),
                ('text', (5, 36, f"Past Violations: {previous_count}", font), {'fill': 'orange' if previous_count > 0 else 'white'}),
                ('text', (5, 46, "Violation Type:", font), {'fill': 'white'}),
                ('text', (5, 56, violation_line1, font), {'fill': 'yellow'}),
            ]
            
            # Add second line of violation if needed
            if violation_line2:
                summary_elements.append(('text', (5, 66, violation_line2, font), {'fill': 'yellow'}))
                db_y_pos = 81
            else:
                db_y_pos = 71
            
            # Add database status
            summary_elements.extend([
                ('text', (5, db_y_pos, f"DB: {db_type}", font), {'fill': 'white'}),
                ('text', (5, db_y_pos + 15, db_status, font), {'fill': 'green' if result["ok"] else 'red'})
            ])
            
            Clear_Screen()
            Draw_All_Elements(summary_elements)
            time.sleep(5)  # Show summary for 5 seconds
        
        print("\n=== PARKING VIOLATION ENFORCEMENT COMPLETE ===")
        print(f"Violation Summary:")
        print(f"  ID: {result.get('evidence_id', 'N/A')}")
        print(f"  RFID UID: {scanned_uid}")
        print(f"  Previous Violations: {uid_info.get('previous_violations', 0)}")
        print(f"  Photo: {photo_path}")
        print(f"  Violation: {selected_violation}")
        print(f"  Location: Campus Parking Area")
        print(f"  Device: HANDHELD_01")
        print(f"  Database: {'Recorded' if result['ok'] else 'Failed'}")
        print(f"  Storage: {result.get('storage_method', 'unknown')}")
        
        time.sleep(5)
        
        # Clean up camera
        if picam2:
            try:
                picam2.stop()
                print("Camera stopped")
            except:
                pass

    except Exception as e:
        print(f"Main system error: {e}")
        # Clean up camera and GPIO before exit
        if 'picam2' in locals() and picam2:
            try:
                picam2.stop()
            except:
                pass
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except:
            pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        try:
            Clear_Screen()
        except:
            pass
        # Clean up GPIO before exit
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except:
            pass
        print("\nParking violations enforcement system interrupted.")
        sys.exit(0)