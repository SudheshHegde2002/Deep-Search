import customtkinter as ctk
from tkinter import filedialog, Menu
from threading import Thread
import queue
from search_utils.searchengine_utils import ImageSearchEngine
from PIL import Image, ImageTk
import shutil
import os

# Set appearance and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ScrollableImageFrame(ctk.CTkScrollableFrame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

class ImageThumbnail(ctk.CTkFrame):
    def __init__(self, parent, image_path, similarity_score):
        super().__init__(parent)
        
        try:
            # Load and resize image
            image = Image.open(image_path)
            image.thumbnail((200, 200))  # Resize image to thumbnail
            photo = ctk.CTkImage(light_image=image, size=(200, 200))
            
            # Create and grid widgets
            self.image_label = ctk.CTkLabel(self, image=photo, text="")
            self.image_label.image = photo  # Keep a reference
            self.image_label.pack(pady=5)
            
            # Add score and filename labels with modern styling
            score_label = ctk.CTkLabel(self, text=f"Score: {similarity_score:.2f}", 
                                       font=("Helvetica", 12, "bold"))
            score_label.pack(pady=(0, 5))
            
            filename_label = ctk.CTkLabel(self, text=os.path.basename(image_path), 
                                          font=("Helvetica", 10))
            filename_label.pack(pady=(0, 5))
            
            # Store image path for context menu
            self.image_path = image_path
            
            # Bind context menu
            self.image_label.bind("<Button-3>", self.show_context_menu)
            
        except Exception as e:
            error_label = ctk.CTkLabel(self, text="Error loading image")
            error_label.pack()
    
    def show_context_menu(self, event):
        menu = Menu(self, tearoff=0)
        menu.add_command(label="Open", command=self.open_image)
        menu.add_command(label="Open File Location", command=self.open_location)
        menu.add_command(label="Copy", command=self.copy_file)
        menu.add_command(label="Cut", command=self.cut_file)
        menu.post(event.x_root, event.y_root)
    
    def open_image(self):
        os.startfile(self.image_path)
    
    def open_location(self):
        os.startfile(os.path.dirname(self.image_path))
    
    def copy_file(self):
        dest = filedialog.askdirectory(title="Choose destination for copy")
        if dest:
            shutil.copy2(self.image_path, dest)
    
    def cut_file(self):
        dest = filedialog.askdirectory(title="Choose destination for move")
        if dest:
            shutil.move(self.image_path, dest)

class SearchGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Modern Image Search System")
        
        # Use native window chrome so the app appears in the taskbar
        self.master.overrideredirect(False)
        
        # Create a frame to simulate window with custom border
        self.window_frame = ctk.CTkFrame(master, corner_radius=0)
        self.window_frame.pack(fill="both", expand=True)
        
        # Add custom close button
        self.create_title_bar()
        
        # Main content container
        self.main_container = ctk.CTkFrame(self.window_frame, corner_radius=0)
        self.main_container.pack(fill="both", expand=True, padx=0, pady=0)
        
        self.search_engine = ImageSearchEngine()
        self.result_queue = queue.Queue()
        
        self.create_widgets()
        # Reflect loaded index state in the progress label on startup
        if getattr(self.search_engine, 'image_paths', None):
            try:
                self.progress_label.configure(
                    text=f"Loaded existing image database ({len(self.search_engine.image_paths)} images)"
                )
            except Exception:
                pass
        
        # Make window draggable
        self.make_draggable()

    def create_title_bar(self):
        title_bar = ctk.CTkFrame(self.window_frame, height=30, corner_radius=0)
        title_bar.pack(fill="x", side="top")
        title_bar.pack_propagate(False)
        
        control_frame = ctk.CTkFrame(title_bar, fg_color="transparent")
        control_frame.grid(row=0, column=1, sticky="e", padx=5)
        
        #Minimize button
        minimize_button = ctk.CTkButton(control_frame, text="—", width=30, height=30, 
                                        command=self.minimize_window, 
                                        fg_color="transparent", 
                                        hover_color="gray")
        minimize_button.grid(row=0, column=0, padx=2)
        # Maximize/Restore button

        self.maximize_button = ctk.CTkButton(control_frame, text="☐", width=30, height=30, 
                                             command=self.toggle_maximize, 
                                             fg_color="transparent", 
                                             hover_color="gray")
        self.maximize_button.grid(row=0, column=1, padx=2)
        # Close button
        close_button = ctk.CTkButton(control_frame, text="X", width=30, height=30, 
                                     command=self.master.quit, 
                                     fg_color="transparent", 
                                     hover_color="red")
        close_button.grid(row=0, column=2, padx=2)
       

    def make_draggable(self):
        def start_move(event):
            self.master.x = event.x
            self.master.y = event.y
        
        def stop_move(event):
            self.master.x = None
            self.master.y = None
        
        def do_move(event):
            deltax = event.x - self.master.x
            deltay = event.y - self.master.y
            x = self.master.winfo_x() + deltax
            y = self.master.winfo_y() + deltay
            self.master.geometry(f"+{x}+{y}")
        
        # Bind dragging to title bar
        for widget in self.window_frame.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                widget.bind("<ButtonPress-1>", start_move)
                widget.bind("<ButtonRelease-1>", stop_move)
                widget.bind("<B1-Motion>", do_move)

    def minimize_window(self):
        self.master.iconify()
    
    def toggle_maximize(self):
        if not self.is_maximized:
            # Store current window geometry before maximizing
            self.previous_geometry = self.master.geometry()
            self.master.attributes('-fullscreen', True)
            self.maximize_button.configure(text="❐")  # Change to restore icon
        else:
            self.master.attributes('-fullscreen', False)
            # Restore previous geometry if it exists
            if hasattr(self, 'previous_geometry'):
                self.master.geometry(self.previous_geometry)
            self.maximize_button.configure(text="☐")  # Change back to maximize icon
        
        self.is_maximized = not self.is_maximized
        
    def create_widgets(self):
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(2, weight=1)
        
        # Progress frame
        self.progress_frame = ctk.CTkFrame(self.main_container)
        self.progress_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.progress_label = ctk.CTkLabel(self.progress_frame, 
                                           text="Initializing...",
                                           font=("Helvetica", 12))
        self.progress_label.pack(fill="x", padx=10, pady=5)
        
        # Search frame with improved layout
        search_frame = ctk.CTkFrame(self.main_container)
        search_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        search_frame.grid_columnconfigure(0, weight=1)
        
        # Search entry with rounded corners and placeholder
        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, 
                                    textvariable=self.search_var,
                                    placeholder_text="Search images...",
                                    font=("Helvetica", 14))
        search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        # Search button with dark color matching UI
        search_button = ctk.CTkButton(search_frame, 
                                      text="Search", 
                                      command=self.start_search,
                                      font=("Helvetica", 12, "bold"),
                                      fg_color="transparent",
                                      border_width=1,
                                      corner_radius=10)
        search_button.grid(row=0, column=1, sticky="e")

        # Index button to let user pick a folder to index (no auto full system scan)
        index_button = ctk.CTkButton(search_frame,
                                     text="Index Folder",
                                     command=self.index_folder,
                                     font=("Helvetica", 12),
                                     fg_color="transparent",
                                     border_width=1,
                                     corner_radius=10)
        index_button.grid(row=0, column=2, sticky="e", padx=(10, 0))

        # Load Index button to let user pick an existing .pkl index
        load_button = ctk.CTkButton(search_frame,
                                    text="Load Index",
                                    command=self.load_index,
                                    font=("Helvetica", 12),
                                    fg_color="transparent",
                                    border_width=1,
                                    corner_radius=10)
        load_button.grid(row=0, column=3, sticky="e", padx=(10, 0))
        
        # Scrollable results frame
        self.results_frame = ctk.CTkScrollableFrame(self.main_container, 
                                                    orientation="vertical")
        self.results_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)

    def index_folder(self):
        folder = filedialog.askdirectory(title="Select folder to index")
        if not folder:
            return
        # Create a per-folder database filename
        folder_name = os.path.basename(folder.rstrip("/\\")) or "index"
        data_file = f"image_search_data_{folder_name}.pkl"
        self.progress_label.configure(text=f"Indexing: {folder}")
        
        def run_index():
            def update_progress(message):
                self.result_queue.put((message, "progress"))
                self.master.after(100, self.check_queue)
            try:
                self.search_engine.scan_system(callback=update_progress,
                                               root_dirs=[folder],
                                               data_file=data_file)
                self.result_queue.put((f"Indexing complete: {data_file}", "progress"))
            except Exception as e:
                self.result_queue.put((f"Error indexing: {e}", "error"))
            self.master.after(100, self.check_queue)
        Thread(target=run_index).start()

    def load_index(self):
        file_path = filedialog.askopenfilename(
            title="Select index file",
            filetypes=[("Pickle files", "*.pkl"), ("All files", "*.*")]
        )
        if not file_path:
            return
        ok = self.search_engine.load_database(file_path)
        if ok:
            self.progress_label.configure(
                text=f"Loaded existing image database ({len(self.search_engine.image_paths)} images)"
            )
        else:
            self.progress_label.configure(text="Failed to load index file")
    
    def start_search(self):
        query = self.search_var.get()
        if query:
            # Clear existing results
            for widget in self.results_frame.winfo_children():
                widget.destroy()
            
            self.progress_label.configure(text=f"Searching for: {query}")
            Thread(target=self.search_thread, args=(query,)).start()
    
    def search_thread(self, query):
        try:
            results = self.search_engine.search(query)
            self.result_queue.put((results, "results"))
        except Exception as e:
            self.result_queue.put((f"Error searching: {e}", "error"))
        self.master.after(100, self.check_queue)
    
    def check_queue(self):
        try:
            message, msg_type = self.result_queue.get_nowait()
            if msg_type == "results":
                self.display_results(message)
            elif msg_type == "progress":
                self.progress_label.configure(text=message)
            elif msg_type == "error":
                self.progress_label.configure(text=message)
        except queue.Empty:
            pass
    
    def display_results(self, results):
        # Configure grid for results
        max_cols = 4
        for idx, (path, similarity) in enumerate(results):
            row = idx // max_cols
            col = idx % max_cols

            thumbnail = ImageThumbnail(self.results_frame, path, similarity)
            thumbnail.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
