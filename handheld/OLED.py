# -*- coding: UTF-8 -*-

from luma.core.interface.serial import spi
from luma.oled.device import ssd1351
from luma.core.render import canvas
from PIL import Image, ImageDraw, ImageFont
import time
import RPi.GPIO as GPIO

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Define the BCM GPIO pins for your display
RST_PIN = 25
DC_PIN = 24

# Define display constants
SSD1351_WIDTH = 128
SSD1351_HEIGHT = 128

# Create the serial interface using the hardware SPI bus.
serial = spi(
    device=0,
    port=0,
    gpio_DC=DC_PIN,
    gpio_RST=RST_PIN,
    bgr=True
)

# Create the display device instance.
device = ssd1351(serial, width=SSD1351_WIDTH, height=SSD1351_HEIGHT)

def Clear_Screen():
    """Clears the display."""
    device.clear()

def Display_Image(img):
    """Displays a PIL Image object on the screen."""
    image = img.convert("RGB").resize(device.size)
    
    # Fix color space - swap R and B channels since bgr=True is set
    r, g, b = image.split()
    corrected_image = Image.merge("RGB", (b, g, r))
    
    device.display(corrected_image)

def Draw_All_Elements(elements):
    """
    Draws a list of elements on the display in a single canvas.
    Each element is a tuple: (type, args, kwargs)
    e.g., ('text', (x, y, text, font), {'fill': 'white'})
    e.g., ('rectangle', (x, y, w, h), {'fill': 'yellow'})
    """
    with canvas(device) as draw:
        for element in elements:
            type = element[0]
            args = element[1]
            kwargs = element[2]
            
            if type == 'text':
                x, y, text, font = args
                draw.text((x, y), text, font=font, **kwargs)
            elif type == 'rectangle':
                x, y, w, h = args
                draw.rectangle((x, y, x + w, y + h), **kwargs)

def Invert(v):
    """Inverts the display colors."""
    device.invert_display(v)

if __name__ == "__main__":
    # This block will run only when you execute OLED.py directly.
    # It demonstrates how to use the functions defined above.

    print("Clearing screen...")
    Clear_Screen()
    time.sleep(1)
    
    # Create a list of elements to draw
    elements_to_draw = []
    
    # Load a default font. You can change this to a font file on your system.
    try:
        font = ImageFont.load_default()
    except ImportError:
        font = None
        print("Pillow font support not available, cannot draw text.")
    
    if font:
        print("Drawing a colored rectangle and text...")
        elements_to_draw.append(('rectangle', (10, 10, 50, 50), {'fill': 'red'}))
        elements_to_draw.append(('text', (10, 70, "Hello, Pi!", font), {'fill': 'yellow'}))
        
    Draw_All_Elements(elements_to_draw)
    time.sleep(2)
    
    print("Example finished.")