#!/usr/bin/env python
import serial
import RPi.GPIO as GPIO # Not directly used in this snippet, but kept as in original
import os
import sys
import time
# import string # 'string' module is rarely needed directly in modern Python, kept for consistency if original script uses it elsewhere
from subprocess import Popen # Not directly used in this snippet, but kept for consistency if original script uses it elsewhere

# --- Serial Port Configuration ---
# Based on "FM-503 command format.pdf":
# Baud Rate: 38400 (default)
# Data Bits: 8 bit
# Stop Bits: 1 bit
# Parity Bit: none
try:
    ser = serial.Serial(
            port='/dev/ttyUSB0', # Ensure this is the correct serial port for your RFID reader
            baudrate=38400,      # Confirmed from FM-503 documentation
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1            # Timeout for read operations (seconds)
    )
    print(f"Successfully opened serial port {ser.port} at {ser.baudrate} baud.")
except serial.SerialException as e:
    print(f"Error opening serial port: {e}")
    print("Please ensure the RFID reader is connected, the port name is correct, and user permissions (e.g., 'dialout' group) are set.")
    sys.exit(1) # Exit the script if the serial port cannot be opened

print("Waiting for RFID tag...")

# --- FM503 Command Definitions ---
# Commands start with <LF> (0x0A) and end with <CR> (0x0D).
# Responses start with <LF> (0x0A), followed by the command character, and end with <CR><LF> (0x0D 0x0A).

# Command to display reader firmware version: V
COMMAND_GET_VERSION = b'\x0A' + b'V' + b'\x0D'

# Command to display reader ID: S
COMMAND_GET_READER_ID = b'\x0A' + b'S' + b'\x0D'

# Command to display tag EPC ID (single-tag read): Q
# Response: <LF>Q<none or EPC><CR><LF>
COMMAND_SINGLE_TAG_EPC = b'\x0A' + b'Q' + b'\x0D'

# Command for Multi-TAG read EPC: U
# Response: <LF>U<none or EPC><CR><LF>
# 'none': no tag in RF field
# 'EPC': PC+EPC+CRC16 (ASCII hexadecimal characters)
COMMAND_MULTI_TAG_EPC = b'\x0A' + b'U' + b'\x0D'

# --- Main Loop for RFID Reading ---
while True:
    try:
        # Clear input buffer before sending a command to ensure we read fresh responses
        ser.flushInput()

        # 1. Send the Multi-TAG read EPC command (U)
        # This command will prompt the reader to scan for and return EPCs of tags in the field.
        print(f"\nSending Multi-TAG read EPC command (U): {COMMAND_MULTI_TAG_EPC.hex()}")
        ser.write(COMMAND_MULTI_TAG_EPC)

        # 2. Wait a moment for the reader to process the command and send a response.
        # A short delay is often necessary for the hardware to respond.
        time.sleep(0.1)

        # 3. Read the response from the RFID reader.
        # We expect the response to end with <CR><LF> (0x0D 0x0A).
        # Read a maximum number of bytes, or until the terminator.
        # For simplicity, we'll read all available bytes after a short delay,
        # but for ROBUST parsing, a read_until(b'\x0D\x0A') might be better if available
        # and if the response length is variable.
        # Given the documentation, responses are usually short, so reading inWaiting() should be fine.
        response_data = ser.read(ser.inWaiting())

        if response_data:
            print(f"Received raw response: {response_data.hex()}")

            # 4. Parse the response based on FM503 protocol
            # Expected response format: <LF><CMD_CHAR><DATA><CR><LF>
            # For 'U' command, it's <LF>U<EPC_DATA><CR><LF> or <LF>U<CR><LF> for no tag.

            # Check for minimum response length (0x0A, 'U', 0x0D, 0x0A = 4 bytes)
            if len(response_data) >= 4 and \
               response_data[0] == 0x0A and \
               response_data[1] == ord('U') and \
               response_data[-2:] == b'\x0D\x0A':

                # Extract the data part between the command character and <CR><LF>
                # The data starts from index 2 (after 0x0A and 'U') up to the last 2 bytes (<CR><LF>)
                epc_data_bytes = response_data[2:-2]

                if epc_data_bytes:
                    # The document states EPC data is ASCII format (hex characters)
                    try:
                        tag_id = epc_data_bytes.decode('ascii').strip()
                        if tag_id == "none": # As specified in the document for no tag
                            print("No tag detected in RF field.")
                        else:
                            # The tag_id will be PC+EPC+CRC16 as ASCII hex characters
                            # print(f"Tag detected! EPC (PC+EPC+CRC16): {tag_id}") # Commented out this line
                            # Parse PC, Actual EPC, and CRC16
                            pc = tag_id[0:4]
                            actual_epc = tag_id[4:-4]
                            crc16 = tag_id[-4:]
                            print(f"Detected EPC: {actual_epc}") # Modified to only show Actual EPC

                            # --- Your application logic here ---
                            # e.g., play a video based on tag_id
                            # if tag_id == "YOUR_TAG_ID_1":
                            #    Popen(["omxplayer", movie1])
                            # elif tag_id == "YOUR_TAG_ID_2":
                            #    Popen(["omxplayer", movie2])
                            # else:
                            #    print("Unknown tag.")

                    except UnicodeDecodeError:
                        print("Error decoding EPC data. It might not be ASCII hex characters as expected.")
                else:
                    print("Received 'U' response with no data (likely 'none' for no tag).")
            else:
                print("Received unexpected response format for 'U' command.")
        else:
            print("No response received from reader within timeout.")

        time.sleep(0.5) # Add a delay to prevent flooding the serial port and CPU

    except serial.SerialException as e:
        print(f"Serial communication error: {e}")
        print("Attempting to close and re-open serial port...")
        ser.close()
        time.sleep(5) # Wait before retrying to give the system time
        try:
            ser.open()
            print("Serial port re-opened successfully.")
        except serial.SerialException as e_reopen:
            print(f"Failed to re-open serial port: {e_reopen}")
            print("Exiting script due to persistent serial port issues.")
            sys.exit(1) # Exit if unable to recover serial connection
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1) # Exit on other unexpected errors
