import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from pathlib import Path
import sys
import os
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from pathlib import Path
import pickle
import string
from concurrent.futures import ThreadPoolExecutor

class ImageSearchEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        
        self.image_paths = []
        self.image_features = []
        # Resolve database path based on launch context
        if getattr(sys, 'frozen', False):
            # When running as an exe, look next to the exe
            base_dir = os.path.dirname(sys.executable)
            self.data_file = os.path.abspath(os.path.join(base_dir, "image_search_data.pkl"))
        else:
            # When running from source, look in the project root (one level above this file)
            project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
            self.data_file = os.path.join(project_root, "image_search_data.pkl")
        
        # Load existing database if present
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'rb') as f:
                    saved_data = pickle.load(f)
                    self.image_paths = saved_data.get('paths', [])
                    self.image_features = saved_data.get('features', [])
        except Exception:
            # Ignore load errors; start without an index
            self.image_paths = []
            self.image_features = []

    def load_database(self, file_path):
        """Load an existing index database from a specified pkl file."""
        try:
            if not os.path.exists(file_path):
                return False
            with open(file_path, 'rb') as f:
                saved_data = pickle.load(f)
            self.image_paths = saved_data.get('paths', [])
            self.image_features = saved_data.get('features', [])
            # Update default data_file to this path for subsequent saves
            self.data_file = file_path
            return bool(self.image_paths) and bool(self.image_features)
        except Exception:
            return False
        
    def get_system_drives(self):
        """Get all available drives on Windows"""
        drives = []
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drives.append(drive)
        return drives
        
    def process_image(self, path):
        """Process a single image and return its features"""
        try:
            image = Image.open(path).convert('RGB')
            inputs = self.processor(images=image, return_tensors="pt", padding=True)
            image_features = self.model.get_image_features(**inputs.to(self.device))
            return str(path), image_features.detach().cpu()
        except Exception:
            return None

    def scan_system(self, callback=None, root_dirs=None, data_file=None):
        image_extensions = {'.jpg', '.jpeg', '.png','.gif'}
        
        # Decide output database file
        target_data_file = data_file if data_file else self.data_file
        
        # If a database already exists at target path, load and return
        if os.path.exists(target_data_file):
            with open(target_data_file, 'rb') as f:
                saved_data = pickle.load(f)
                self.image_paths = saved_data['paths']
                self.image_features = saved_data['features']
            if callback:
                callback("Loaded existing image database")
            return

        # Require explicit roots; do NOT scan entire system by default
        if not root_dirs:
            if callback:
                callback("No folders provided to index.")
            return
        
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = []
            
            for root in root_dirs:
                if callback:
                    callback(f"Scanning folder: {root}")
                
                for path in Path(root).rglob('*'):
                    if path.suffix.lower() in image_extensions:
                        futures.append(executor.submit(self.process_image, path))
            
            total = len(futures)
            processed = 0
            
            for future in futures:
                result = future.result()
                if result:
                    path, features = result
                    self.image_paths.append(path)
                    self.image_features.append(features)
                
                processed += 1
                if callback and processed % 10 == 0:
                    callback(f"Processed {processed}/{total} images")

        # Save the data
        with open(target_data_file, 'wb') as f:
            pickle.dump({
                'paths': self.image_paths,
                'features': self.image_features
            }, f)
        
        if callback:
            callback("Scanning complete")

    def search(self, query, top_k=30):
        text_inputs = self.processor(text=[query], return_tensors="pt", padding=True)
        text_features = self.model.get_text_features(**text_inputs.to(self.device))
        
        similarities = []
        for image_feature in self.image_features:
            similarity = torch.nn.functional.cosine_similarity(
                text_features.cpu(), image_feature, dim=1
            )
            similarities.append(similarity.item())
        
        top_indices = sorted(range(len(similarities)), 
                           key=lambda i: similarities[i], 
                           reverse=True)[:top_k]
        
        return [(self.image_paths[i], similarities[i]) for i in top_indices]