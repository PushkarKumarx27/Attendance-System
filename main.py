import os
import pickle
import numpy as np
import cv2
import face_recognition
import cvzone
from datetime import datetime
from firebase_admin import credentials, db
import firebase_admin
import threading
import queue
import time
import csv

# ==========================================
# 1. Firebase Initialization
# ==========================================
def init_firebase():
    if not firebase_admin._apps:
        try:
            if os.path.exists("serviceAccountKey.json"):
                cred = credentials.Certificate("serviceAccountKey.json")
                firebase_admin.initialize_app(cred, {
                    'databaseURL': "https://attendancesystem-335f9-default-rtdb.firebaseio.com/"
                })
                return True
            else:
                return False
        except Exception:
            return False
    return True

# ==========================================
# 2. Global State (Thread-Safe)
# ==========================================
class AttendanceSystemState:
    def __init__(self):
        self.raw_frame = None
        self.processed_results = []
        self.is_running = True
        self.lock = threading.Lock()
        
        self.student_cache = {}         # {id: {info, img}}
        self.attendance_log = {}        # {id: timestamp}
        
        self.active_id = -1
        self.ui_mode = 0                # 0: Active, 1: Loading, 2: Info, 3: Success
        self.animation_counter = 0

state = AttendanceSystemState()
db_queue = queue.Queue()
COOLDOWN = 60 

# ==========================================
# 3. Background Threads
# ==========================================

class VideoStreamThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.cap = cv2.VideoCapture(0)
        self.cap.set(3, 640)
        self.cap.set(4, 480)

    def run(self):
        while state.is_running:
            success, frame = self.cap.read()
            if success:
                with state.lock:
                    state.raw_frame = frame
            else:
                time.sleep(0.1)
        self.cap.release()

class AIProcessorThread(threading.Thread):
    def __init__(self, model_path='EncodeFile.p'):
        super().__init__(daemon=True)
        self.known_encodings = []
        self.known_ids = []
        try:
            with open(model_path, 'rb') as f:
                data = pickle.load(f)
                self.known_encodings, self.known_ids = data
        except Exception:
            pass

    def run(self):
        while state.is_running:
            frame = None
            with state.lock:
                if state.raw_frame is not None:
                    frame = state.raw_frame.copy()
            
            if frame is not None:
                small_frame = cv2.resize(frame, (0, 0), None, 0.25, 0.25)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                face_locs = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locs)
                
                matches_found = []
                for encode, loc in zip(face_encodings, face_locs):
                    distances = face_recognition.face_distance(self.known_encodings, encode)
                    if len(distances) > 0:
                        best_match_idx = np.argmin(distances)
                        if distances[best_match_idx] < 0.50:
                            matches_found.append({'id': self.known_ids[best_match_idx], 'bbox': loc})
                
                with state.lock:
                    state.processed_results = matches_found
            
            time.sleep(0.01)

class CloudSyncThread(threading.Thread):
    def run(self):
        while state.is_running:
            try:
                s_id = db_queue.get(timeout=1)
                
                now = datetime.now()
                with state.lock:
                    last_seen = state.attendance_log.get(s_id)
                    is_cached = s_id in state.student_cache
                
                if last_seen and (now - last_seen).total_seconds() < COOLDOWN:
                    db_queue.task_done()
                    continue

                if not is_cached:
                    info = db.reference(f'Students/{s_id}').get()
                    img_path = f'Images/{s_id}.png'
                    img = cv2.imread(img_path) if os.path.exists(img_path) else None
                    with state.lock:
                        state.student_cache[s_id] = {'info': info, 'img': img}

                ref = db.reference(f'Students/{s_id}')
                with state.lock:
                    student_data = state.student_cache[s_id]['info']
                
                if student_data:
                    student_data['total_attendance'] += 1
                    ref.child('total_attendance').set(student_data['total_attendance'])
                    ref.child('last_attendance_time').set(now.strftime("%Y-%m-%d %H:%M:%S"))
                    with state.lock:
                        state.attendance_log[s_id] = now
                
                db_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                pass

# ==========================================
# 4. Minimalist UI Components
# ==========================================

def render_interface(background, frame, results, modes):
    # Place camera feed
    background[162:162+480, 55:55+640] = frame
    
    # Logic for active student display
    active_student = None
    with state.lock:
        if state.active_id != -1 and state.active_id in state.student_cache:
            active_student = state.student_cache[state.active_id]

    # Draw right panel
    if active_student and state.animation_counter > 5:
        # Show Student Success Mode
        background[44:44+633, 808:808+414] = modes[2] # Info mode
        
        info = active_student['info']
        student_img = active_student['img']
        
        # Overlay student details
        if info:
            cv2.putText(background, str(info['name']), (900, 445), cv2.FONT_HERSHEY_COMPLEX, 0.7, (50, 50, 50), 2)
            cv2.putText(background, str(state.active_id), (1006, 493), cv2.FONT_HERSHEY_COMPLEX, 0.5, (100, 100, 100), 1)
            cv2.putText(background, str(info['major']), (1006, 550), cv2.FONT_HERSHEY_COMPLEX, 0.5, (100, 100, 100), 1)
            cv2.putText(background, str(info['total_attendance']), (861, 125), cv2.FONT_HERSHEY_COMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(background, str(info['CGPA']), (910, 625), cv2.FONT_HERSHEY_COMPLEX, 0.6, (50, 50, 50), 1)
            cv2.putText(background, str(info['year']), (1025, 625), cv2.FONT_HERSHEY_COMPLEX, 0.6, (50, 50, 50), 1)
            cv2.putText(background, str(info['starting_year']), (1125, 625), cv2.FONT_HERSHEY_COMPLEX, 0.6, (50, 50, 50), 1)

            if student_img is not None:
                img_res = cv2.resize(student_img, (216, 216))
                background[175:175+216, 909:909+216] = img_res
    else:
        # Show default/active mode
        mode_idx = state.ui_mode if state.ui_mode < len(modes) else 0
        background[44:44+633, 808:808+414] = modes[mode_idx]

    # Draw face boxes
    for match in results:
        y1, x2, y2, x1 = [v * 4 for v in match['bbox']]
        cvzone.cornerRect(background, (55+x1, 162+y1, x2-x1, y2-y1), l=20, t=3, rt=1, colorR=(0, 255, 0))

    return background

# ==========================================
# 5. Main Loop
# ==========================================

def main():
    if not init_firebase(): return

    bg_img = cv2.imread('Resources/background.png')
    mode_folder = 'Resources/Modes'
    modes = [cv2.imread(os.path.join(mode_folder, p)) for p in sorted(os.listdir(mode_folder))] if os.path.exists(mode_folder) else []
    
    VideoStreamThread().start()
    AIProcessorThread().start()
    CloudSyncThread().start()

    while True:
        with state.lock:
            frame = state.raw_frame.copy() if state.raw_frame is not None else None
            results = state.processed_results.copy()
        
        if frame is not None:
            if results and state.animation_counter == 0:
                state.active_id = results[0]['id']
                state.animation_counter = 1
                state.ui_mode = 1 # Loading
                db_queue.put(state.active_id)

            if state.animation_counter != 0:
                state.animation_counter += 1
                if state.animation_counter > 40:
                    state.animation_counter = 0
                    state.ui_mode = 0
                    state.active_id = -1

            display = render_interface(bg_img.copy(), frame, results, modes)
            cv2.imshow("Smart Attendance System", display)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            state.is_running = False
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
