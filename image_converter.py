import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:
    import sys
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Missing Dependency", "The 'Pillow' library is required.\nPlease install it using: pip install Pillow")
    sys.exit(1)

import sys

# Increase the limit for large images to avoid DecompressionBombError
Image.MAX_IMAGE_PIXELS = None

# Compatibility for older Pillow versions
try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
except (AttributeError, NameError):
    RESAMPLE_LANCZOS = Image.LANCZOS


class ImageConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Converter (2100w x 1400h)")
        self.root.geometry("500x350") 
        self.root.configure(padx=20, pady=20)
        
        # Variables
        self.input_folder_var = tk.StringVar()
        self.output_folder_var = tk.StringVar()
        self.bg_color_var = tk.StringVar(value="black")
        self.resize_mode_var = tk.StringVar(value="pad")
        self.status_var = tk.StringVar(value="Ready to process...")
        
        # Target specs (Width 2100, Height 1400 based on '1400px by 2100px (Height by Width)')
        self.TARGET_W = 2100
        self.TARGET_H = 1400
        
        # Create Widgets directly in __init__ for better attribute tracking
        # Input Folder
        tk.Label(self.root, text="Input Folder:").grid(row=0, column=0, sticky="w", pady=5)
        tk.Entry(self.root, textvariable=self.input_folder_var, width=40).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Browse", command=self.browse_input).grid(row=0, column=2, pady=5)
        
        # Output Folder
        tk.Label(self.root, text="Output Folder:").grid(row=1, column=0, sticky="w", pady=5)
        tk.Entry(self.root, textvariable=self.output_folder_var, width=40).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(self.root, text="Browse", command=self.browse_output).grid(row=1, column=2, pady=5)
        
        # Mode
        tk.Label(self.root, text="Resize Mode:").grid(row=2, column=0, sticky="w", pady=5)
        mode_frame = tk.Frame(self.root)
        mode_frame.grid(row=2, column=1, sticky="w", pady=5)
        tk.Radiobutton(mode_frame, text="Pad (Add Borders)", variable=self.resize_mode_var, value="pad").pack(side="left")
        tk.Radiobutton(mode_frame, text="Crop (Fill to Edge)", variable=self.resize_mode_var, value="crop").pack(side="left")
        
        # Background Color (for Pad mode)
        tk.Label(self.root, text="Pad Color:").grid(row=3, column=0, sticky="w", pady=5)
        color_frame = tk.Frame(self.root)
        color_frame.grid(row=3, column=1, sticky="w", pady=5)
        tk.Radiobutton(color_frame, text="Black", variable=self.bg_color_var, value="black").pack(side="left")
        tk.Radiobutton(color_frame, text="White", variable=self.bg_color_var, value="white").pack(side="left")
        
        # Progress Bar
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate")
        self.progress.grid(row=4, column=0, columnspan=3, pady=20)
        
        # Status Label
        tk.Label(self.root, textvariable=self.status_var).grid(row=5, column=0, columnspan=2, sticky="w")
        
        # Convert Button
        self.convert_btn = tk.Button(self.root, text="Start Conversion", command=self.start_conversion, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.convert_btn.grid(row=5, column=2, pady=10)

        
    def browse_input(self):
        folder = filedialog.askdirectory()
        if folder:
            self.input_folder_var.set(os.path.normpath(folder))
            current_out = self.output_folder_var.get()
            if not current_out or current_out.endswith("converted"):
                self.output_folder_var.set(os.path.normpath(os.path.join(folder, "converted")))
                
    def browse_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder_var.set(os.path.normpath(folder))
            
    def start_conversion(self):
        input_folder = os.path.normpath(self.input_folder_var.get().strip())
        output_folder = os.path.normpath(self.output_folder_var.get().strip())
        
        if not input_folder or not os.path.exists(input_folder):
            messagebox.showerror("Error", "Please select a valid input folder.")
            return
            
        if not output_folder:
            messagebox.showerror("Error", "Please specify an output folder.")
            return
            
        try:
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create output directory:\n{e}")
            return
        

        self.convert_btn.config(state="disabled")
        self.status_var.set("Scanning for images...")
        
        # Fetch options in main thread
        mode = self.resize_mode_var.get()
        bg_color_name = self.bg_color_var.get()
        bg_color = (0, 0, 0) if bg_color_name == "black" else (255, 255, 255)
        
        # Run conversion in a separate thread so GUI doesn't freeze
        thread_args = (input_folder, output_folder, mode, bg_color)
        threading.Thread(target=self.process_images, args=thread_args, daemon=True).start()

        
    def process_images(self, input_folder, output_folder, mode, bg_color):
        valid_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        
        try:
            all_files = os.listdir(input_folder)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Could not read input folder:\n{e}"))
            self.root.after(0, lambda: self.convert_btn.config(state="normal"))
            return

        files = [f for f in all_files if os.path.splitext(f.lower())[1] in valid_extensions 
                 and "_converted" not in f]
        
        if not files:
            self.root.after(0, lambda: self.status_var.set("No valid images found."))
            self.root.after(0, lambda: self.convert_btn.config(state="normal"))
            return
            
        total_files = len(files)
        self.root.after(0, lambda: self.progress.configure(maximum=total_files, value=0))
        
        success_count = 0
        error_count = 0
        
        for i, filename in enumerate(files):
            input_path = os.path.join(input_folder, filename)
            name, ext = os.path.splitext(filename)
            
            # Normalize extension to lowercase for output consistency
            out_ext = ext.lower() if ext.lower() in {".jpg", ".jpeg", ".png"} else ".jpg"
            output_path = os.path.join(output_folder, f"{name}_converted{out_ext}")
            
            try:
                with Image.open(input_path) as img:
                    # 1. Correct orientation from EXIF
                    img = ImageOps.exif_transpose(img)
                    
                    # 2. Handle transparency before converting to RGB
                    if img.mode in ("RGBA", "LA", "P"):
                        # Create a background of the chosen color
                        canvas = Image.new("RGBA", img.size, bg_color + (255,))
                        # If P mode, ensure it's RGBA for proper masking
                        img = img.convert("RGBA")
                        canvas.paste(img, (0, 0), img)
                        img = canvas.convert("RGB")
                    elif img.mode != "RGB":
                        img = img.convert("RGB")
                        
                    new_img = None
                    if mode == "pad":
                        # Resize preserving aspect ratio to fit inside TARGET_W x TARGET_H
                        img.thumbnail((self.TARGET_W, self.TARGET_H), RESAMPLE_LANCZOS)
                        
                        # Create a new background image and paste the resized image into the center
                        new_img = Image.new("RGB", (self.TARGET_W, self.TARGET_H), bg_color)
                        paste_x = (self.TARGET_W - img.width) // 2
                        paste_y = (self.TARGET_H - img.height) // 2
                        new_img.paste(img, (paste_x, paste_y))
                        
                    elif mode == "crop":
                        # Resize and crop to fill TARGET_W x TARGET_H entirely
                        new_img = ImageOps.fit(img, (self.TARGET_W, self.TARGET_H), RESAMPLE_LANCZOS)
                    
                    if new_img:
                        if out_ext in {".jpg", ".jpeg"}:
                            new_img.save(output_path, "JPEG", quality=95, optimize=True)
                        else:
                            new_img.save(output_path, optimize=True)
                        success_count += 1
                    else:
                        error_count += 1
                        
            except (UnidentifiedImageError, OSError, Exception) as e:
                print(f"Error processing {filename}: {e}")
                error_count += 1
                
            self.root.after(0, lambda current=i+1: self.progress.configure(value=current))
            self.root.after(0, lambda current=i+1, name=filename: self.status_var.set(f"Processed {current}/{total_files}: {name}"))
            
        final_msg = f"Done! Successfully converted {success_count} images."
        if error_count > 0:
            final_msg += f" ({error_count} failed.)"

            
        self.root.after(0, lambda: self.status_var.set(final_msg))
        self.root.after(0, lambda: self.convert_btn.config(state="normal"))
        self.root.after(0, lambda: messagebox.showinfo("Conversion Complete", final_msg))

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageConverterApp(root)
    root.mainloop()

