import cv2
import face_recognition
import pickle
import numpy as np
import threading
import time

class FaceEngine:
    """Handles asynchronous face recognition and matching."""
    def __init__(self, model_path='EncodeFile.p'):
        self.known_encodings = []
        self.known_ids = []
        self.results = []
        self.lock = threading.Lock()
        self.running = True
        
        # Load pre-trained encodings
        try:
            with open(model_path, 'rb') as f:
                self.known_encodings, self.known_ids = pickle.load(f)
            print(f"Engine: Loaded {len(self.known_ids)} encodings.")
        except Exception as e:
            print(f"Engine Error: {e}")

    def process_frame(self, frame):
        """Perform recognition on a frame in a non-blocking way."""
        if frame is None: return
        
        # Pre-process
        img_small = cv2.resize(frame, (0, 0), None, 0.25, 0.25)
        img_rgb = cv2.cvtColor(img_small, cv2.COLOR_BGR2RGB)
        
        # Recognize
        face_locs = face_recognition.face_locations(img_rgb)
        face_encodings = face_recognition.face_encodings(img_rgb, face_locs)
        
        current_results = []
        for encode, loc in zip(face_encodings, face_locs):
            matches = face_recognition.compare_faces(self.known_encodings, encode)
            distances = face_recognition.face_distance(self.known_encodings, encode)
            
            if len(distances) > 0:
                match_idx = np.argmin(distances)
                if matches[match_idx] and distances[match_idx] < 0.50:
                    current_results.append({
                        'id': self.known_ids[match_idx],
                        'bbox': loc # (top, right, bottom, left)
                    })
        
        with self.lock:
            self.results = current_results

    def get_results(self):
        with self.lock:
            return self.results.copy()
