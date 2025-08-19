import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from pathlib import Path
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
        self.data_file = "image_search_data.pkl"
        
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

    def scan_system(self, callback=None):
        image_extensions = {'.jpg', '.jpeg', '.png','.gif'}
        
        # Check if we have existing data
        if os.path.exists(self.data_file):
            with open(self.data_file, 'rb') as f:
                saved_data = pickle.load(f)
                self.image_paths = saved_data['paths']
                self.image_features = saved_data['features']
            if callback:
                callback("Loaded existing image database")
            return

        drives = self.get_system_drives()
        
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = []
            
            for drive in drives:
                if callback:
                    callback(f"Scanning drive: {drive}")
                
                for path in Path(drive).rglob('*'):
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
        with open(self.data_file, 'wb') as f:
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