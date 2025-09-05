#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2022 Richard Hull and contributors
# See LICENSE.rst for details.
# PYTHON_ARGCOMPLETE_OK

"""
Capture photo with picamera and display it on a screen.

Requires picamera to be installed.
"""

import io
import sys
import time

from PIL import Image


from demo_opts import get_device

try:
    from picamera2 import Picamera2
except ImportError:
    print("The picamera2 library is not installed. Install it using 'pip install picamera2'.")
    sys.exit()


def main():

    cameraResolution = (1024, 768)
    displayTime = 5
    countdownTime = 5

    picam2 = Picamera2()
    config = picam2.create_still_configuration(main={'size': cameraResolution})
    picam2.configure(config)

    print("Starting camera preview...")
    picam2.start()
    time.sleep(2)

    # --- Start of Added Countdown ---
    print("Get ready to smile! Taking a picture in...")
    for i in range(countdownTime, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    # --- End of Added Countdown ---

    print("Capturing photo...")
    image_array = picam2.capture_array()

    print("Stopping camera preview...")
    picam2.stop()

    print(f"Displaying photo for {displayTime} seconds...")

    # Convert numpy array to PIL Image
    photo = Image.fromarray(image_array)

    # Resize to device size if needed
    if photo.size != device.size:
        photo = photo.resize(device.size)

    # display on screen for a few seconds
    device.display(photo.convert(device.mode))
    time.sleep(displayTime)

    print("Done.")


if __name__ == "__main__":
    try:
        device = get_device()
        main()
    except KeyboardInterrupt:
        pass
