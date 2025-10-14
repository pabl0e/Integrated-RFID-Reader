#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Complete Parking Enforcement System - Direct Execution
1. Takes photo of violation
2. Allows selection of violation type
No subprocess calls to avoid GPIO conflicts
"""

import sys
import time
import os
from PIL import ImageFont
from handheld_rfid_module import scan_rfid_for_enforcement
from handheld_db_module import store_evidence

# Add path to OLED module - try multiple possible locations
possible_oled_paths = [
    # Try relative paths first
    './test-code/oled',
    '../test-code/oled',
    '../../test-code/oled',
    # Try absolute paths for your specific setup
    'd:/Thesis/pi-zero-hq-cam/camera/software/test-code/oled',
    '/home/binslibal/Projects/pi-zero-hq-cam/camera/software/test-code/oled',
    '/home/binslibal/Projects/pi-zero-hq-cam/camera/software/test-code/progress',
    # Try current directory
    '.',
]

# Add each path that exists to sys.path
for path in possible_oled_paths:
    if os.path.exists(path):
        sys.path.append(path)
        print(f"Added to path: {path}")

# Test OLED import
try:
    from OLED import Clear_Screen, Draw_All_Elements, Display_Image
    print("OLED module imported successfully")
    OLED_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import OLED module: {e}")
    print("Creating mock OLED functions for testing...")
    OLED_AVAILABLE = False
    
    # Create mock functions
    def Clear_Screen():
      print("MOCK: Clearing screen")
        
    def Draw_All_Elements(elements):
        for element in elements:
            print(f"MOCK: Drawing element - Type: {element[0]}, Args: {element[1]}")
        
    def Display_Image(img):
        print("MOCK: Displaying image")

def initialize_camera():
    """Initialize and warm up the camera for instant capture"""
    try:
        from picamera2 import Picamera2
        
        print("Pre-warming camera for instant capture...")
        cameraResolution = (1024, 768)
        picam2 = Picamera2()
        
        # Use preview configuration for faster startup
        preview_config = picam2.create_preview_configuration(main={'size': cameraResolution})
        picam2.configure(preview_config)
        
        # Start camera and let it warm up
        picam2.start()
        time.sleep(1)  # Allow camera to fully initialize
        
        print("Camera pre-warmed and ready!")
        return picam2
        
    except ImportError:
        print("Camera library not available")
        return None
    except Exception as e:
        print(f"Camera initialization error: {e}")
        return None

def run_photo_capture(picam2=None):
    """Run photo capture with pre-warmed camera"""
    print("=== PHOTO CAPTURE ===")
    
    try:
        from PIL import Image
        
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        
        displayTime = 2  # Reduced display time for faster workflow

        print("Camera ready for instant capture...")
        
        # Show camera ready message
        elements_to_draw = [('text', (10, 50, "Taking a picture!", font), {'fill': 'green'})]
        if OLED_AVAILABLE:
            Clear_Screen()
            Draw_All_Elements(elements_to_draw)
        else:
            Draw_All_Elements(elements_to_draw)

        print("Taking photo...")

        # INSTANT CAMERA CAPTURE (camera already running)
        try:
            if picam2 is None:
                # Fallback if camera wasn't pre-started
                from picamera2 import Picamera2
                cameraResolution = (1024, 768)
                picam2 = Picamera2()
                preview_config = picam2.create_preview_configuration(main={'size': cameraResolution})
                picam2.configure(preview_config)
                picam2.start()
                time.sleep(0.5)
            
            # Instant capture since camera is already running
            print("Capturing photo instantly...")
            image_array = picam2.capture_array()
            
            # Keep camera running for potential future captures
            # Don't stop the camera here
            
            # Convert to PIL Image and ensure RGB format for JPEG
            photo = Image.fromarray(image_array)
            
            # Convert RGBA to RGB if necessary (JPEG doesn't support alpha channel)
            if photo.mode == 'RGBA':
                photo = photo.convert('RGB')
            elif photo.mode not in ['RGB', 'L']:  # Handle other modes
                photo = photo.convert('RGB')
                
            print("Photo captured!")
            
            # Create evidences directory and save (optimized)
            evidences_dir = "evidences"
            os.makedirs(evidences_dir, exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            photo_filename = f"evidence_{timestamp}.jpg"
            photo_path = os.path.join(evidences_dir, photo_filename)
            
            # Save with optimized JPEG quality for speed
            photo.save(photo_path, "JPEG", quality=85, optimize=True)
            print(f"Evidence saved: {photo_filename}")
            
            # Display the captured photo on OLED for preview
            print(f"Displaying captured photo for {displayTime} seconds...")
            if OLED_AVAILABLE:
                Display_Image(photo)
            time.sleep(displayTime)
            
        except ImportError:
            print("Camera library not available. Using fallback message...")
            elements_to_draw = [
                ('text', (10, 50, "No Camera", font), {'fill': 'red'}),
                ('text', (10, 70, "Available", font), {'fill': 'red'})
            ]
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
            time.sleep(displayTime)
            
        except Exception as e:
            print(f"Camera error: {e}")
            print("Camera functionality failed.")
            elements_to_draw = [
                ('text', (10, 40, "Camera Error", font), {'fill': 'red'}),
                ('text', (10, 60, str(e)[:12], font), {'fill': 'red'})
            ]
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
            time.sleep(displayTime)

        # Quick confirmation message
        elements_to_draw = [
            ('text', (10, 30, "Photo Captured!", font), {'fill': 'green'}),
            ('text', (10, 50, "Evidence Saved", font), {'fill': 'cyan'})
        ]
        if OLED_AVAILABLE:
            Clear_Screen()
            Draw_All_Elements(elements_to_draw)
        else:
            Draw_All_Elements(elements_to_draw)
        time.sleep(1)  # Reduced from 3 seconds to 1 second

        print("Photo capture completed.")
        return True, photo_path  # Return both success status and photo path
        
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
            DOWN_PIN = 27   # GPIO 27 (Pin 13) - Changed from GPIO 24
            CENTER_PIN = 17 # GPIO 17 (Pin 11) - Changed from GPIO 18
            BACK_PIN = 26   # GPIO 26 (Pin 37)
            
            # Initialize GPIO only once
            try:
                # Check if GPIO is already set up by trying to read a pin
                try:
                    GPIO.setmode(GPIO.BCM)  # This will fail if already set
                except:
                    # GPIO already initialized, just continue
                    pass
                    
                GPIO.setup([UP_PIN, DOWN_PIN, CENTER_PIN, BACK_PIN], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                print("GPIO buttons initialized successfully")
                
            except Exception as gpio_error:
                print(f"GPIO setup error: {gpio_error}")
                # Try to clean up and reinitialize
                try:
                    GPIO.cleanup()
                    GPIO.setmode(GPIO.BCM)
                    GPIO.setup([UP_PIN, DOWN_PIN, CENTER_PIN, BACK_PIN], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                    print("GPIO reinitialized successfully")
                except Exception as reinit_error:
                    print(f"GPIO reinitialization failed: {reinit_error}")
                    GPIO_AVAILABLE = False
            
        except ImportError:
            print("RPi.GPIO not available, using keyboard input fallback")
            GPIO_AVAILABLE = False
        
        violations = [
            "Student in Faculty Area",
            "No Parking Zone",
            "Expired Permit",
            "Handicap Violation"
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
            
            # Draw violation options
            for i, violation in enumerate(violations):
                y_pos = 25 + (i * 15)
                if y_pos > 100:  # Don't draw if it goes off screen
                    break
                    
                if i == selected_index:
                    # Highlight selected option
                    elements_to_draw.append(('rectangle', (3, y_pos - 2, 125, 12), {'fill': 'yellow'}))
                    elements_to_draw.append(('text', (5, y_pos, f"{i+1}. {violation[:15]}", font), {'fill': 'black'}))
                else:
                    elements_to_draw.append(('text', (5, y_pos, f"{i+1}. {violation[:15]}", font), {'fill': 'white'}))
            
            # Draw instructions
            elements_to_draw.append(('text', (5, 110, "UP/DOWN:Nav CENTER:Select", font), {'fill': 'cyan'}))
            
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
        
        def check_buttons():
            """Check button states and return button pressed"""
            if not GPIO_AVAILABLE:
                return None
                
            if GPIO.input(UP_PIN) == GPIO.HIGH:
                time.sleep(0.2)  # Debounce
                return "UP"
            elif GPIO.input(DOWN_PIN) == GPIO.HIGH:
                time.sleep(0.2)  # Debounce
                return "DOWN"
            elif GPIO.input(CENTER_PIN) == GPIO.HIGH:
                time.sleep(0.2)  # Debounce
                return "CENTER"
            elif GPIO.input(BACK_PIN) == GPIO.HIGH:
                time.sleep(0.2)  # Debounce
                return "BACK"
            return None
        
        # Main selection loop
        print("Use buttons to navigate and select violation...")
        draw_menu()
        
        while True:
            if GPIO_AVAILABLE:
                # Use button input
                button = check_buttons()
                
                if button == "UP":
                    selected_index = (selected_index - 1) % len(violations)
                    print(f"Selected: {violations[selected_index]}")
                    draw_menu()
                    
                elif button == "DOWN":
                    selected_index = (selected_index + 1) % len(violations)
                    print(f"Selected: {violations[selected_index]}")
                    draw_menu()
                    
                elif button == "CENTER":
                    print(f"Confirmed selection: {violations[selected_index]}")
                    break
                    
                elif button == "BACK":
                    print("Selection cancelled")
                    return False
                    
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                
            else:
                # Fallback to keyboard input for testing
                print("\nCurrent selection:", violations[selected_index])
                print("Controls: w(UP), s(DOWN), enter(SELECT), q(BACK)")
                key = input("Enter command: ").lower().strip()
                
                if key == 'w':
                    selected_index = (selected_index - 1) % len(violations)
                    draw_menu()
                elif key == 's':
                    selected_index = (selected_index + 1) % len(violations)
                    draw_menu()
                elif key == '' or key == 'enter':
                    break
                elif key == 'q':
                    print("Selection cancelled")
                    return False
        
        # Show selection confirmation
        selected_violation = violations[selected_index]
        elements_to_draw = [
            ('text', (10, 20, "SELECTED:", font), {'fill': 'green'})
        ]
        
        # Display selected violation
        violation_lines = selected_violation.split()
        for i, word in enumerate(violation_lines):
            y_pos = 40 + (i * 15)
            if y_pos < 100:  # Keep within screen bounds
                elements_to_draw.append(('text', (10, y_pos, word, font), {'fill': 'yellow'}))
        
        elements_to_draw.append(('text', (10, 100, "Violation Recorded", font), {'fill': 'green'}))

        if OLED_AVAILABLE:
            Clear_Screen()
            Draw_All_Elements(elements_to_draw)
        else:
            Draw_All_Elements(elements_to_draw)
        
        time.sleep(3)
        
        # Save violation data to evidences directory
        evidences_dir = "evidences"
        os.makedirs(evidences_dir, exist_ok=True)
        
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        violation_code = selected_violation.upper().replace(" ", "_")
        violation_data = f"{timestamp}: {violation_code}\n"
        
        try:
            log_path = os.path.join(evidences_dir, "violations_log.txt")
            with open(log_path, "a") as f:
                f.write(violation_data)
            print(f"Violation logged: {violation_code}")
        except Exception as e:
            print(f"Error saving violation: {e}")
        
        print("Violation selection completed.")
        return selected_violation  # Return the selected violation type
        
    except Exception as e:
        print(f"Violation selector error: {e}")
        return None

def show_main_menu_with_camera():
    """Show main menu and wait for center button press with camera pre-warmed"""
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
            
            # Initialize GPIO
            try:
                try:
                    GPIO.setmode(GPIO.BCM)
                except:
                    pass
                GPIO.setup([CENTER_PIN], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
                print("GPIO center button initialized")
            except Exception as gpio_error:
                print(f"GPIO setup error: {gpio_error}")
                GPIO_AVAILABLE = False
            
        except ImportError:
            print("RPi.GPIO not available, using keyboard input fallback")
            GPIO_AVAILABLE = False
        
        # Initialize camera early while showing main menu
        print("Initializing camera system...")
        picam2 = initialize_camera()
        
        def draw_main_menu():
            """Draw the main menu"""
            camera_status = "Camera Ready" if picam2 else "Camera Error"
            status_color = 'green' if picam2 else 'red'
            
            elements_to_draw = [
                ('text', (10, 10, "PARKING ENFORCEMENT", font), {'fill': 'white'}),
                ('text', (10, 30, "SYSTEM", font), {'fill': 'white'}),
                ('text', (10, 50, camera_status, font), {'fill': status_color}),
                ('text', (10, 70, "Press CENTER to start", font), {'fill': 'cyan'}),
                ('text', (10, 85, "enforcement process:", font), {'fill': 'cyan'}),
                ('text', (10, 100, "RFID->Photo->Violation", font), {'fill': 'yellow'})
            ]
            
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
        
        def check_center_button():
            """Check center button state"""
            if not GPIO_AVAILABLE:
                return False
            if GPIO.input(CENTER_PIN) == GPIO.HIGH:
                time.sleep(0.2)  # Debounce
                return True
            return False
        
        # Show main menu with camera status
        draw_main_menu()
        print("Camera pre-warmed. Press CENTER button for instant capture...")
        
        # Wait for center button press
        while True:
            if GPIO_AVAILABLE:
                if check_center_button():
                    print("CENTER button pressed! Starting instant capture...")
                    break
                time.sleep(0.1)
            else:
                # Fallback to keyboard input
                print("Press ENTER to start enforcement (or 'q' to quit):")
                key = input().lower().strip()
                if key == '' or key == 'enter':
                    break
                elif key == 'q':
                    # Clean up camera before exit
                    if picam2:
                        try:
                            picam2.stop()
                        except:
                            pass
                    return None, False
        
        return picam2, True
        
    except Exception as e:
        print(f"Main menu error: {e}")
        return None, False

def run_rfid_scanner():
    """Run RFID scanning step with display feedback"""
    print("=== RFID SCANNER ===")
    
    try:
        from PIL import ImageFont
        
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        
        # Show scanning message
        elements_to_draw = [
            ('text', (10, 30, "RFID SCANNING", font), {'fill': 'white'}),
            ('text', (10, 50, "Present RFID tag", font), {'fill': 'yellow'}),
            ('text', (10, 70, "to scanner...", font), {'fill': 'yellow'})
        ]
        if OLED_AVAILABLE:
            Clear_Screen()
            Draw_All_Elements(elements_to_draw)
        else:
            Draw_All_Elements(elements_to_draw)
        
        # Scan for RFID
        scanned_uid = scan_rfid_for_enforcement()
        
        if scanned_uid:
            # Show success message
            elements_to_draw = [
                ('text', (10, 20, "RFID DETECTED", font), {'fill': 'green'}),
                ('text', (10, 40, f"UID: {scanned_uid[:8]}...", font), {'fill': 'white'}),
                ('text', (10, 60, "Proceeding to", font), {'fill': 'cyan'}),
                ('text', (10, 80, "photo capture...", font), {'fill': 'cyan'})
            ]
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
            time.sleep(2)
            return scanned_uid
        else:
            # Show failure message
            elements_to_draw = [
                ('text', (10, 30, "NO RFID DETECTED", font), {'fill': 'red'}),
                ('text', (10, 50, "Please try again", font), {'fill': 'yellow'})
            ]
            if OLED_AVAILABLE:
                Clear_Screen()
                Draw_All_Elements(elements_to_draw)
            else:
                Draw_All_Elements(elements_to_draw)
            time.sleep(3)
            return None
            
    except Exception as e:
        print(f"RFID scanner error: {e}")
        return None

def main():
    """Main enforcement workflow with RFID scanning and database storage"""
    
    # Add startup delay for proper initialization when powered via GPIO/battery
    print("System startup delay - ensuring stable initialization...")
    time.sleep(8)  # Increased delay to 8 seconds
    print("Initialization delay complete - starting system...")
    
    try:
        from PIL import ImageFont
        
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        
        # Welcome message
        elements_to_draw = [
            ('text', (10, 30, "PARKING ENFORCEMENT", font), {'fill': 'white'}),
            ('text', (10, 50, "SYSTEM", font), {'fill': 'white'}),
            ('text', (10, 80, "Initializing...", font), {'fill': 'yellow'})
        ]
        if OLED_AVAILABLE:
            Clear_Screen()
            Draw_All_Elements(elements_to_draw)
        else:
            Draw_All_Elements(elements_to_draw)
        time.sleep(1)
        
        print("=== PARKING ENFORCEMENT SYSTEM ===")
        
        # Show main menu and pre-warm camera
        picam2, should_continue = show_main_menu_with_camera()
        
        if not should_continue:
            print("System cancelled by user")
            return
        
        # Step 1: RFID Scanning
        print("Step 1: Scanning RFID tag...")
        scanned_uid = run_rfid_scanner()
        
        if not scanned_uid:
            print("RFID scanning failed. Cannot proceed without RFID.")
            return
        
        print(f"RFID UID captured: {scanned_uid}")
        
        # Step 2: Photo capture
        print("Step 2: Taking photo evidence...")
        photo_success, photo_path = run_photo_capture(picam2)
        
        if not photo_success or not photo_path:
            print("Photo capture failed. Cannot proceed without evidence photo.")
            return
        
        print(f"Photo captured: {photo_path}")
        
        # Step 3: Violation selection
        print("Step 3: Selecting violation type...")
        selected_violation = run_violation_selector()
        
        if not selected_violation:
            print("Violation selection failed.")
            return
        
        print(f"Violation selected: {selected_violation}")
        
        # Step 4: Store evidence in database
        print("Step 4: Storing evidence in database...")
        
        # Show storing message
        elements_to_draw = [
            ('text', (10, 30, "STORING EVIDENCE", font), {'fill': 'yellow'}),
            ('text', (10, 50, "Please wait...", font), {'fill': 'white'})
        ]
        if OLED_AVAILABLE:
            Clear_Screen()
            Draw_All_Elements(elements_to_draw)
        else:
            Draw_All_Elements(elements_to_draw)
        
        # Store in database
        result = store_evidence(
            rfid_uid=scanned_uid,
            photo_path=photo_path,
            violation_type=selected_violation
        )
        
        if result["ok"]:
            storage_method = result.get('storage_method', 'unknown')
            print(f"Evidence stored successfully! ID: {result['evidence_id']}")
            print(f"Storage method: {storage_method}")
            
            # Show success message with storage method
            if storage_method == "database":
                elements_to_draw = [
                    ('text', (10, 15, "STORED IN DB", font), {'fill': 'green'}),
                    ('text', (10, 35, f"ID: {result['evidence_id']}", font), {'fill': 'white'}),
                    ('text', (10, 55, "Enforcement", font), {'fill': 'cyan'}),
                    ('text', (10, 75, "Complete!", font), {'fill': 'cyan'})
                ]
            else:
                elements_to_draw = [
                    ('text', (10, 10, "STORED AS FILE", font), {'fill': 'yellow'}),
                    ('text', (10, 30, f"ID: {result['evidence_id']}", font), {'fill': 'white'}),
                    ('text', (10, 50, "DB unavailable", font), {'fill': 'orange'}),
                    ('text', (10, 70, "Complete!", font), {'fill': 'cyan'})
                ]
        else:
            print(f"Failed to store evidence: {result['error']}")
            # Show error message
            elements_to_draw = [
                ('text', (10, 30, "STORAGE ERROR", font), {'fill': 'red'}),
                ('text', (10, 50, "All methods failed", font), {'fill': 'yellow'})
            ]
        
        if OLED_AVAILABLE:
            Clear_Screen()
            Draw_All_Elements(elements_to_draw)
        else:
            Draw_All_Elements(elements_to_draw)
        
        print("\n=== ENFORCEMENT COMPLETE ===")
        print(f"Summary:")
        print(f"  RFID UID: {scanned_uid}")
        print(f"  Photo: {photo_path}")
        print(f"  Violation: {selected_violation}")
        print(f"  Database: {'Stored' if result['ok'] else 'Failed'}")
        
        time.sleep(3)
        
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
        print("\nEnforcement system interrupted.")
        sys.exit(0)