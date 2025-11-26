import tkinter as tk
from tkinter import font as tkfont
import sys
from PIL import Image, ImageTk
import io
from PIL import Image, ImageTk, ImageDraw

class CarInfoDisplay:
    def __init__(self):
        print("CarInfoDisplay: Initializing application")
        self.root = tk.Tk()
        self._resize_job = None

        # layout constants
        self.pad = 40
        self.left_col_w = 520  # reserved width for the photo column

        self.setup_window()
        self.setup_styles()

        # StringVars
        self.sticker_status_var = tk.StringVar(value='')
        self.usc_id_var        = tk.StringVar(value='')
        self.student_name_var  = tk.StringVar(value='')
        self.make_var          = tk.StringVar(value='')
        self.model_var         = tk.StringVar(value='')
        self.color_var         = tk.StringVar(value='')
        self.vehicle_type_var  = tk.StringVar(value='')
        self.license_plate_var = tk.StringVar(value='')

        self.sticker_status_label = None
        self._profile_photo = None

        self.create_widgets()

        # initial blank photo + initial title fit
        self.update_profile_picture(None)
        self.fit_title_to_width()

        # refit on window resize
        self.root.bind("<Configure>", self.on_resize)

    # ---------- window & styles ----------
    def setup_window(self):
        self.root.title("Vehicle Registration Display")
        self.root.geometry("1920x1080")            # 16:9
        self.root.configure(bg='#ffffff')
        self.root.attributes('-fullscreen', True)  # ESC toggles
        self.root.bind('<Escape>', self.toggle_fullscreen)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

    def setup_styles(self):
        # base sizes (title will auto-fit)
        self.title_family = 'Arial'
        self.title_size_max = 64
        self.title_size_min = 34

        self.label_font  = ('Arial', 39, 'bold')
        self.value_font  = ('Arial', 41, 'normal')
        self.status_font = ('Arial', 45, 'bold')

        self.bg_color        = '#ffffff'
        self.title_color     = '#355E3B'
        self.label_color     = '#355E3B'
        self.value_color     = '#355E3B'
        self.registered_color   = '#00ff00'
        self.unregistered_color = '#ff0000'

    # ---------- layout ----------
    def create_widgets(self):
        """
        Grid (3 columns):
          col 0: left photo
          col 1: labels
          col 2: values
        """
        self.main = tk.Frame(self.root, bg=self.bg_color)
        self.main.grid(row=0, column=0, sticky='nsew', padx=self.pad, pady=self.pad)

        self.main.grid_columnconfigure(0, weight=1, minsize=self.left_col_w)
        self.main.grid_columnconfigure(1, weight=1)
        self.main.grid_columnconfigure(2, weight=2)
        for r in range(9):
            self.main.grid_rowconfigure(r, weight=1)

        # Left: profile picture
        self.profile_image_label = tk.Label(self.main, bg=self.bg_color, bd=1, relief='solid')
        self.profile_image_label.grid(row=0, column=0, rowspan=9, sticky='nsew', padx=(0, 30))

        # Title across columns 1–2
        self.title_text = "VEHICLE REGISTRATION INFORMATION"
        self.title_label = tk.Label(
            self.main, text=self.title_text,
            font=(self.title_family, self.title_size_max, 'bold'),
            fg=self.title_color, bg=self.bg_color, anchor='w'
        )
        self.title_label.grid(row=0, column=1, columnspan=2, sticky='w', pady=(0, 30))

        # Info rows
        self.sticker_status_label = self.create_info_row(self.main, 1, "Sticker Status:", self.sticker_status_var, is_status=True)
        self.create_info_row(self.main, 2, "USC ID:",        self.usc_id_var)
        self.create_info_row(self.main, 3, "Full Name:",     self.student_name_var)
        self.create_info_row(self.main, 4, "Make:",          self.make_var)
        self.create_info_row(self.main, 5, "Model:",         self.model_var)
        self.create_info_row(self.main, 6, "Color:",         self.color_var)
        self.create_info_row(self.main, 7, "Vehicle Type:",  self.vehicle_type_var)
        self.create_info_row(self.main, 8, "License Plate:", self.license_plate_var)

    def create_info_row(self, parent, row, label_text, textvariable, is_status=False):
        lab = tk.Label(parent, text=label_text, font=self.label_font,
                       fg=self.label_color, bg=self.bg_color, anchor='w')
        lab.grid(row=row, column=1, sticky='w', padx=(0, 20), pady=10)

        initial_font = self.value_font
        initial_color = self.value_color
        if is_status:
            initial_font = self.status_font
            st = (textvariable.get() or '').lower()
            if st == 'renewed':
                initial_color = self.registered_color
            elif st != '':
                initial_color = self.unregistered_color

        val = tk.Label(parent, textvariable=textvariable, font=initial_font,
                       fg=initial_color, bg=self.bg_color, anchor='w')
        val.grid(row=row, column=2, sticky='w', pady=10)
        return val

    # ---------- title auto-fit ----------
    def fit_title_to_width(self):
        """Shrink the title font until it fits the middle+right columns width."""
        # Ensure geometry is updated
        self.root.update_idletasks()

        # Available width = total window - (outer pads + left column + inner gap + right pad)
        total_w = self.root.winfo_width() or 1920
        available = total_w - (2*self.pad + self.left_col_w + 30 + self.pad)
        if available <= 0:
            return

        size = self.title_size_max
        f = tkfont.Font(family=self.title_family, size=size, weight='bold')
        while f.measure(self.title_text) > available and size > self.title_size_min:
            size -= 2
            f.configure(size=size)

        self.title_label.configure(font=(self.title_family, size, 'bold'))

    def on_resize(self, _event):
        # Debounce rapid resize events
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(120, self.fit_title_to_width)

    # ---------- behavior ----------
    def toggle_fullscreen(self, event=None):
        self.root.attributes('-fullscreen', not self.root.attributes('-fullscreen'))

    def update_status_color(self, status):
        status_text = (status or "").lower()
        if status_text == 'renewed':
            self.sticker_status_label.config(fg=self.registered_color)
        elif status_text == 'expired':
            self.sticker_status_label.config(fg=self.unregistered_color)
        else:
            self.sticker_status_label.config(fg=self.value_color)

    def update_profile_picture(self, image_obj):
        """
        Accepts a pre-processed PIL Image object (not bytes).
        Converts it directly to ImageTk for display.
        """
        if image_obj:
            self._profile_photo = ImageTk.PhotoImage(image_obj)
        else:
            # Fallback: Create a blank white placeholder (very fast)
            img = Image.new('RGB', (500, 900), 'white')
            self._profile_photo = ImageTk.PhotoImage(img)

        self.profile_image_label.config(image=self._profile_photo)

    def update_car_info(self, new_data, profile_picture_bytes=None):
        if 'sticker_status' in new_data:
            self.sticker_status_var.set(new_data['sticker_status'])
            self.update_status_color(new_data['sticker_status'])
        if 'usc_id' in new_data:
            self.usc_id_var.set(new_data['usc_id'])
        if 'student_name' in new_data:
            self.student_name_var.set(new_data['student_name'])
        if 'make' in new_data:
            self.make_var.set(new_data['make'])
        if 'model' in new_data:
            self.model_var.set(new_data['model'])
        if 'color' in new_data:
            self.color_var.set(new_data['color'])
        if 'vehicle_type' in new_data:
            self.vehicle_type_var.set(new_data['vehicle_type'])
        if 'license_plate' in new_data:
            self.license_plate_var.set(new_data['license_plate'])

        # refresh image (None blanks it)
        self.update_profile_picture(profile_picture_bytes)

        # re-fit title in case DPI/geometry changed
        self.fit_title_to_width()
        print("Display updated via StringVars.")

    def run(self):
        print("Starting Car Information Display...")
        print("Press ESC to exit fullscreen mode")
        print("Close window or Ctrl+C to exit application")
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nApplication terminated by user")
            self.root.destroy() 
            sys.exit(0)

    def show_red_x(self, w=500, h=900, thickness=40):
        """Draw a large red X and display it on the left panel."""
        img = Image.new('RGB', (w, h), 'white')
        d = ImageDraw.Draw(img)
        # two diagonals
        d.line((0, 0, w, h), fill=(255, 0, 0), width=thickness)
        d.line((0, h, w, 0), fill=(255, 0, 0), width=thickness)
        self._profile_photo = ImageTk.PhotoImage(img)
        self.profile_image_label.config(image=self._profile_photo)
        