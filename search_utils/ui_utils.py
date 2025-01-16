import tkinter as tk
from tkinter import ttk,filedialog,Menu
from threading import Thread
import queue
from search_utils.searchengine_utils import ImageSearchEngine
from PIL import ImageTk
import shutil
from PIL import Image
import os

class ScrollableImageFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Pack widgets
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

class ImageThumbnail(ttk.Frame):
    def __init__(self, parent, image_path, similarity_score):
        super().__init__(parent)
        
        try:
            # Load and resize image
            image = Image.open(image_path)
            image.thumbnail((200, 200))  # Resize image to thumbnail
            photo = ImageTk.PhotoImage(image)
            
            # Create and pack widgets
            self.label = ttk.Label(self, image=photo)
            self.label.image = photo  # Keep a reference
            self.label.pack()
            
            # Add score and filename labels
            score_label = ttk.Label(self, text=f"Score: {similarity_score:.2f}")
            score_label.pack()
            
            filename_label = ttk.Label(self, text=os.path.basename(image_path))
            filename_label.pack()
            
            # Store image path for context menu
            self.image_path = image_path
            
            # Bind context menu
            self.label.bind("<Button-3>", self.show_context_menu)
            
        except Exception as e:
            error_label = ttk.Label(self, text="Error loading image")
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
    
    def copy_file(self, path):
        dest = filedialog.askdirectory(title="Choose destination for copy")
        if dest:
            shutil.copy2(path, dest)
    
    def cut_file(self, path):
        dest = filedialog.askdirectory(title="Choose destination for move")
        if dest:
            shutil.move(path, dest)
            self.start_search()  # Refresh results

class SearchGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Image Search System")
        self.master.geometry("1024x768")
        
        self.search_engine = ImageSearchEngine()
        self.result_queue = queue.Queue()
        
        # Main container
        self.main_container = ttk.Frame(self.master)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        self.create_widgets()
        self.start_initial_scan()
        
    def create_widgets(self):
        # Progress frame
        self.progress_frame = ttk.Frame(self.main_container, padding="5")
        self.progress_frame.pack(fill=tk.X)
        
        self.progress_label = ttk.Label(self.progress_frame, text="Initializing...")
        self.progress_label.pack(fill=tk.X)
        
        # Search frame
        search_frame = ttk.Frame(self.main_container, padding="5")
        search_frame.pack(fill=tk.X)
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        search_button = ttk.Button(search_frame, text="Search", command=self.start_search)
        search_button.pack(side=tk.LEFT)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(self.main_container)
        scrollbar = ttk.Scrollbar(self.main_container, orient="vertical", command=self.canvas.yview)
        
        # Frame to hold results
        self.results_frame = ttk.Frame(self.canvas)
        
        # Configure canvas
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # Create window inside canvas
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.results_frame, anchor="nw")
        
        # Pack scrolling components
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def start_initial_scan(self):
        Thread(target=self.initial_scan_thread).start()
    
    def initial_scan_thread(self):
        def update_progress(message):
            self.result_queue.put((message, "progress"))
            self.master.after(100, self.check_queue)
        
        try:
            self.search_engine.scan_system(callback=update_progress)
            self.result_queue.put(("System scan complete", "info"))
        except Exception as e:
            self.result_queue.put((f"Error scanning system: {e}", "error"))
        self.master.after(100, self.check_queue)
    
    def start_search(self):
        query = self.search_var.get()
        if query:
            # Clear existing results
            for widget in self.results_frame.winfo_children():
                widget.destroy()
            self.progress_label.config(text=f"Searching for: {query}")
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
                self.progress_label.config(text=message)
        except queue.Empty:
            pass
    
    def display_results(self, results):
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        # Configure grid columns
        max_cols = 4
        for i in range(max_cols):
            self.results_frame.grid_columnconfigure(i, weight=1)

        # Display results in grid using ImageThumbnail
        for idx, (path, similarity) in enumerate(results):
            row = idx // max_cols
            col = idx % max_cols

            thumbnail = ImageThumbnail(self.results_frame, path, similarity)
            thumbnail.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            