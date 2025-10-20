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
from handheld_db_module import store_evidence, check_uid

# Try to import OLED module
try:
    from OLED import Clear_Screen, Draw_All_Elements, Display_Image
    OLED_AVAILABLE = True
    print("OLED module loaded successfully")
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
            CENTER_PIN = 17 # GPIO 17 (Pin 11)
            BACK_PIN = 26   # GPIO 26 (Pin 37)
            
            # Initialize GPIO
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup([CENTER_PIN, BACK_PIN], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
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
            elements_to_draw = [
                ('text', (10, 10, "PARKING", font), {'fill': 'white'}),
                ('text', (10, 25, "VIOLATIONS", font), {'fill': 'white'}),
                ('text', (10, 40, "ENFORCEMENT", font), {'fill': 'white'}),
                ('text', (10, 60, "CENTER: Start", font), {'fill': 'cyan'}),
                ('text', (10, 75, "BACK: Exit", font), {'fill': 'blue'}),
                ('text', (10, 95, "Ready to scan!", font), {'fill': 'white'})
            ]
            
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
        
        # Show the menu
        draw_main_menu()
        
        if GPIO_AVAILABLE:
            print("Press CENTER button to start enforcement, BACK button to exit")
            
            while True:
                # Read button states
                center_state = GPIO.input(CENTER_PIN)
                back_state = GPIO.input(BACK_PIN)
                
                if center_state == GPIO.HIGH:
                    print("CENTER button pressed - Starting enforcement!")
                    time.sleep(0.5)  # Debounce
                    return picam2, True
                
                elif back_state == GPIO.HIGH:
                    print("BACK button pressed - Exiting system")
                    time.sleep(0.5)  # Debounce
                    return picam2, False
                
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
        else:
            # Keyboard fallback for testing
            print("Press Enter to start enforcement, 'q' to exit:")
            user_input = input().strip().lower()
            if user_input == 'q':
                print("Exiting system")
                return picam2, False
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
    """Capture evidence photo with preview"""
    print("=== PHOTO CAPTURE ===")
    
    try:
        from PIL import ImageFont
        
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        
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
        
        # Show photo preview screen with actual image
        def draw_photo_preview_screen(photo_path):
            try:
                if OLED_AVAILABLE and os.path.exists(photo_path):
                    print(f"Displaying captured photo: {photo_path}")
                    # Clear screen first
                    Clear_Screen()
                    
                    # Load the image first, then display it
                    try:
                        from PIL import Image
                        # Load the captured photo as PIL Image
                        captured_image = Image.open(photo_path)
                        # Display the actual captured photo using the Display_Image function
                        Display_Image(captured_image)
                    except Exception as load_error:
                        print(f"Could not load image for display: {load_error}")
                        # Fallback to text preview if image loading fails
                        elements_to_draw = [
                            ('text', (10, 20, "PHOTO PREVIEW", font), {'fill': 'white'}),
                            ('text', (15, 40, "Image captured", font), {'fill': 'green'}),
                            ('text', (10, 60, "Load failed", font), {'fill': 'yellow'}),
                            ('text', (15, 80, "File saved OK", font), {'fill': 'green'})
                        ]
                        Draw_All_Elements(elements_to_draw)
                else:
                    # Fallback for when OLED not available or file doesn't exist
                    elements_to_draw = [
                        ('text', (10, 20, "PHOTO PREVIEW", font), {'fill': 'white'}),
                        ('text', (15, 40, "Image captured", font), {'fill': 'green'}),
                        ('text', (10, 60, "OLED preview", font), {'fill': 'yellow'}),
                        ('text', (15, 80, "not available", font), {'fill': 'yellow'})
                    ]
                    Draw_All_Elements(elements_to_draw)
                    
            except Exception as img_error:
                print(f"Image preview error: {img_error}")
                # Fallback to text preview
                elements_to_draw = [
                    ('text', (10, 20, "PHOTO PREVIEW", font), {'fill': 'white'}),
                    ('text', (15, 40, "Image captured", font), {'fill': 'green'}),
                    ('text', (10, 60, "Preview failed", font), {'fill': 'yellow'}),
                    ('text', (15, 80, "File saved OK", font), {'fill': 'green'})
                ]
                Draw_All_Elements(elements_to_draw)
        
        # Show photo failed screen
        def draw_photo_failed_screen():
            elements_to_draw = [
                ('text', (10, 15, "PHOTO CAPTURE", font), {'fill': 'white'}),
                ('text', (15, 35, "FAILED", font), {'fill': 'red'}),
                ('text', (10, 55, "Using mock", font), {'fill': 'yellow'}),
                ('text', (15, 70, "evidence", font), {'fill': 'yellow'}),
                ('text', (15, 90, "Continuing...", font), {'fill': 'white'})
            ]
            
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
        
        # Show capture screen
        draw_photo_capture_screen()
        
        # Create evidences directory if it doesn't exist
        os.makedirs("evidences", exist_ok=True)
        
        # Generate photo filename with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        photo_filename = f"evidence_{timestamp}.jpg"
        photo_path = os.path.join("evidences", photo_filename)
        
        if picam2 and CAMERA_AVAILABLE:
            try:
                # Capture actual photo
                time.sleep(1)  # Brief delay to show capture screen
                picam2.capture_file(photo_path)
                print(f"Photo captured: {photo_path}")
                
                # Show photo preview with actual image
                draw_photo_preview_screen(photo_path)
                time.sleep(3)  # Show preview for 3 seconds
                
                return True, photo_path
            except Exception as e:
                print(f"Camera capture failed: {e}")
                draw_photo_failed_screen()
                time.sleep(2)
        else:
            # Show capture delay for mock camera
            time.sleep(1)
            draw_photo_failed_screen()
            time.sleep(1)
        
        # Fallback: create a placeholder file
        try:
            with open(photo_path, 'w') as f:
                f.write(f"Mock evidence photo - {timestamp}")
            print(f"Mock photo created: {photo_path}")
            
            # Show mock photo preview (no actual image to display)
            elements_to_draw = [
                ('text', (10, 20, "MOCK PREVIEW", font), {'fill': 'yellow'}),
                ('text', (15, 40, "No camera", font), {'fill': 'red'}),
                ('text', (10, 60, "Mock file", font), {'fill': 'yellow'}),
                ('text', (15, 80, "created", font), {'fill': 'yellow'})
            ]
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
            time.sleep(2)  # Show mock preview for 2 seconds
            
            return True, photo_path
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
            "Parking in No Parking Zones",
            "Unauthorized Parking in designated Parking spots"
        ]
        selected_index = 0
        
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        
        def draw_menu():
            """Draw the violation selection menu"""
            elements_to_draw = []
            elements_to_draw.append(('text', (5, 5, "SELECT VIOLATION:", font), {'fill': 'white'}))
            
            # Draw both violation options
            for i, violation in enumerate(violations):
                y_pos = 25 + (i * 20)
                
                if i == selected_index:
                    # Highlight selected option
                    elements_to_draw.append(('rectangle', (3, y_pos - 2, 125, 18), {'fill': 'yellow'}))
                    # Split long text for display
                    if len(violation) > 20:
                        lines = violation.split()
                        mid = len(lines) // 2
                        line1 = " ".join(lines[:mid])
                        line2 = " ".join(lines[mid:])
                        elements_to_draw.append(('text', (5, y_pos, line1[:18], font), {'fill': 'black'}))
                        elements_to_draw.append(('text', (5, y_pos + 10, line2[:18], font), {'fill': 'black'}))
                    else:
                        elements_to_draw.append(('text', (5, y_pos, violation[:20], font), {'fill': 'black'}))
                else:
                    # Split long text for display
                    if len(violation) > 20:
                        lines = violation.split()
                        mid = len(lines) // 2
                        line1 = " ".join(lines[:mid])
                        line2 = " ".join(lines[mid:])
                        elements_to_draw.append(('text', (5, y_pos, line1[:18], font), {'fill': 'white'}))
                        elements_to_draw.append(('text', (5, y_pos + 10, line2[:18], font), {'fill': 'white'}))
                    else:
                        elements_to_draw.append(('text', (5, y_pos, violation[:20], font), {'fill': 'white'}))
            
            # Draw instructions
            elements_to_draw.append(('text', (5, 90, "UP/DOWN: Navigate", font), {'fill': 'cyan'}))
            elements_to_draw.append(('text', (5, 105, "CENTER: Select", font), {'fill': 'cyan'}))
            
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
            print(f"⚠️ Warning: This RFID has {uid_info['previous_violations']} previous violations")
        
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
            print(f"✅ Parking violation recorded successfully! ID: {result['evidence_id']}")
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
            print(f"❌ Failed to record violation: {result['error']}")
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
            db_status = "✓ Saved" if result["ok"] else "✗ Failed"
            
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
            
            summary_elements = [
                ('text', (5, 5, "VIOLATION LOG", font), {'fill': 'white'}),
                ('text', (5, 18, f"ID: {display_id}", font), {'fill': 'green'}),
                ('text', (5, 30, f"UID: {display_uid}", font), {'fill': 'cyan'}),
                ('text', (5, 42, "Violation:", font), {'fill': 'white'}),
                ('text', (5, 52, violation_line1, font), {'fill': 'yellow'}),
            ]
            
            # Add second line of violation if needed
            if violation_line2:
                summary_elements.append(('text', (5, 62, violation_line2, font), {'fill': 'yellow'}))
                db_y_pos = 77
            else:
                db_y_pos = 67
            
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
        print(f"  🆔 Violation ID: {result.get('evidence_id', 'N/A')}")
        print(f"  ✅ RFID UID: {scanned_uid}")
        print(f"  ✅ Photo: {photo_path}")
        print(f"  ✅ Violation: {selected_violation}")
        print(f"  ✅ Location: Campus Parking Area")
        print(f"  ✅ Device: HANDHELD_01")
        print(f"  ✅ Database: {'Recorded' if result['ok'] else 'Failed'}")
        print(f"  📊 Storage: {result.get('storage_method', 'unknown')}")
        
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