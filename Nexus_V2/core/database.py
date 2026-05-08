import os
import cv2
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import threading

class CloudSync:
    """Manages Firebase connectivity and student data caching."""
    def __init__(self, key_path='serviceAccountKey.json', db_url=None):
        self.cache = {}
        self.attendance_log = {}
        self.lock = threading.Lock()
        self.COOLDOWN = 60 # Seconds
        
        # Initialize Firebase
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred, {'databaseURL': db_url})
                print("Database: Firebase Connection Established.")
        except Exception as e:
            print(f"Database Init Error: {e}")

    def get_student_data(self, student_id):
        """Fetch student info and image, using cache when possible."""
        with self.lock:
            if student_id in self.cache:
                return self.cache[student_id]
        
        # Fetch from Firebase
        info = None
        try:
            print(f"Database: Syncing profile for {student_id}...")
            ref = db.reference(f'Students/{student_id}')
            info = ref.get()
        except Exception as e:
            print(f"Database Fetch Error: {e}")
        
        # Load Image (Path relative to Root)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        img_path = os.path.join(base_dir, 'Images', f'{student_id}.png')
        img = cv2.imread(img_path) if os.path.exists(img_path) else None
        
        data = {'info': info, 'img': img}
        with self.lock:
            self.cache[student_id] = data
        return data

    def mark_attendance(self, student_id):
        """Update attendance count in Firebase with cooldown protection."""
        now = datetime.now()
        
        with self.lock:
            last_marked = self.attendance_log.get(student_id)
            if last_marked and (now - last_marked).total_seconds() < self.COOLDOWN:
                return False, "Already marked"

        # Update Firebase
        try:
            ref = db.reference(f'Students/{student_id}')
            student_cache_item = self.get_student_data(student_id)
            data = student_cache_item.get('info')
            
            if data:
                new_total = data.get('total_attendance', 0) + 1
                ref.child('total_attendance').set(new_total)
                ref.child('last_attendance_time').set(now.strftime("%Y-%m-%d %H:%M:%S"))
                
                # Update local cache and log
                with self.lock:
                    self.cache[student_id]['info']['total_attendance'] = new_total
                    self.attendance_log[student_id] = now
                return True, "Success"
            else:
                return False, "Student not in DB"
        except Exception as e:
            print(f"Database Update Error: {e}")
            return False, "Sync Error"
