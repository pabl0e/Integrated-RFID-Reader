from db_module import *
from longrange_rfid_module import run_rfid_read  # Import the existing RFID reader function
from display_gui import CarInfoDisplay  # Import the CarInfoDisplay class
import threading

def main():
    """Main function to run the application"""
    # Create an instance of CarInfoDisplay (initialize the GUI)
    display = CarInfoDisplay()  # This line initializes the GUI display

    # Run the RFID reader in a separate thread and pass the display object
    rfid_thread = threading.Thread(target=run_rfid_read, args=(display,))  # Pass display to run_rfid_read
    rfid_thread.daemon = True  # This allows the thread to exit when the program ends
    rfid_thread.start()

    # Start the GUI event loop
    display.run()  # This starts the Tkinter event loop and keeps the GUI running

if __name__ == "__main__":
    main()