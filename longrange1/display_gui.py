import tkinter as tk
import sys

class CarInfoDisplay:
    def __init__(self):
        # Initialize the main window
        print("CarInfoDisplay: Initializing application")
        self.root = tk.Tk()
        self.setup_window()
        self.setup_styles()

        # Initialize StringVars without initial data
        self.sticker_status_var = tk.StringVar(value='')
        self.user_id_var = tk.StringVar(value='')  # User ID StringVar
        self.student_name_var = tk.StringVar(value='')  # Student Name StringVar
        self.make_var = tk.StringVar(value='')
        self.model_var = tk.StringVar(value='')
        self.color_var = tk.StringVar(value='')
        self.vehicle_type_var = tk.StringVar(value='')
        self.license_plate_var = tk.StringVar(value='')

        # Store references to the value labels to update their colors directly
        self.sticker_status_label = None
        self.user_id_label = None
        self.student_name_label = None
        self.make_label = None
        self.model_label = None
        self.color_label = None
        self.vehicle_type_label = None
        self.license_plate_label = None

        # Create widgets. They will now display empty values initially
        self.create_widgets()

    def setup_window(self):
        """Configure the main window properties"""
        self.root.title("Vehicle Registration Display")
        self.root.geometry("1920x1080")
        self.root.configure(bg='#ffffff')  # White background
        self.root.attributes('-fullscreen', True)  # Fullscreen
        self.root.bind('<Escape>', self.toggle_fullscreen)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

    def setup_styles(self):
        """Define text styles and colors for the display"""
        self.title_font = ('Arial', 50, 'bold')  # Decreased font size by 5
        self.label_font = ('Arial', 39, 'bold')  # Decreased font size by 5
        self.value_font = ('Arial', 41, 'normal')  # Decreased font size by 5
        self.status_font = ('Arial', 45, 'bold')  # Decreased font size by 5

        self.bg_color = '#ffffff'
        self.title_color = '#355E3B'
        self.label_color = '#355E3B'
        self.value_color = '#355E3B'
        self.accent_color = '#FFD700'
        self.registered_color = '#00ff00'
        self.unregistered_color = '#ff0000'

    def create_widgets(self):
        """Create and arrange all GUI elements"""
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.grid(row=0, column=0, sticky='nsew', padx=50, pady=50)

        for i in range(8):
            main_frame.grid_rowconfigure(i, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=2)

        title_label = tk.Label(
            main_frame,
            text="VEHICLE REGISTRATION INFORMATION",
            font=self.title_font,
            fg=self.title_color,
            bg=self.bg_color
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 40), sticky='ew')

        # Create information display rows, linking to StringVars
        self.sticker_status_label = self.create_info_row(main_frame, 1, "Sticker Status:", self.sticker_status_var, is_status=True)
        self.user_id_label = self.create_info_row(main_frame, 2, "User ID:", self.user_id_var)
        self.student_name_label = self.create_info_row(main_frame, 3, "Student Name:", self.student_name_var)
        self.make_label = self.create_info_row(main_frame, 4, "Make:", self.make_var)
        self.model_label = self.create_info_row(main_frame, 5, "Model:", self.model_var)
        self.color_label = self.create_info_row(main_frame, 6, "Color:", self.color_var)
        self.vehicle_type_label = self.create_info_row(main_frame, 7, "Vehicle Type:", self.vehicle_type_var)
        self.license_plate_label = self.create_info_row(main_frame, 8, "License Plate:", self.license_plate_var)

        # Removed instructions label to free up space for the important information

    def create_info_row(self, parent, row, label_text, textvariable, is_status=False):
        """Create a row displaying a label and its corresponding textvariable"""
        label = tk.Label(
            parent,
            text=label_text,
            font=self.label_font,
            fg=self.label_color,
            bg=self.bg_color,
            anchor='w'  # Align the label to the left for better readability
        )
        label.grid(row=row, column=0, sticky='w', padx=(0, 30), pady=15)

        initial_color = self.value_color
        initial_font = self.value_font
        if is_status:
            initial_font = self.status_font
            if textvariable.get().lower() == 'active':
                initial_color = self.registered_color
            elif textvariable.get() != '':
                initial_color = self.unregistered_color

        value_label = tk.Label(
            parent,
            textvariable=textvariable,
            font=initial_font,
            fg=initial_color,
            bg=self.bg_color,
            anchor='w'
        )
        value_label.grid(row=row, column=1, sticky='w', pady=15)
        return value_label

    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode"""
        current_state = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not current_state)

    def update_status_color(self, status):
        """Update the sticker status label color"""
        status_text = status.lower()
        if status_text == 'renewed':
            self.sticker_status_label.config(fg=self.registered_color)
        elif status_text == 'expired':
            self.sticker_status_label.config(fg=self.unregistered_color)
        else:  # Blank or invalid status
            self.sticker_status_label.config(fg=self.value_color)

    def update_car_info(self, new_data):
        """Method to update car information programmatically."""
        if 'sticker_status' in new_data:
            self.sticker_status_var.set(new_data['sticker_status'])
            self.update_status_color(new_data['sticker_status'])  # Update status label color
        if 'user_id' in new_data:
            self.user_id_var.set(new_data['user_id'])
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

        print("Display updated via StringVars.")

    def run(self):
        """Start the GUI application"""
        print("Starting Car Information Display...")
        print("Press ESC to exit fullscreen mode")
        print("Close window or Ctrl+C to exit application")

        try:
            # Start the tkinter main loop
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nApplication terminated by user")
            sys.exit(0)
