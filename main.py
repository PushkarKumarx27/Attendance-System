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
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': "https://attendancesystem-335f9-default-rtdb.firebaseio.com/"
    })

# ==========================================
# 2. Thread-safe Queues and Caches
# ==========================================
frame_queue = queue.Queue(maxsize=1)        # Latest frame from camera
result_queue = queue.Queue(maxsize=1)       # Face detection results
db_task_queue = queue.Queue()               # Tasks for database thread

student_cache = {}                          # Cached student info and images
attendance_cooldown = {}                    # To prevent duplicate marking (e.g., 30s cooldown)
COOLDOWN_SECONDS = 30

# Lock for shared resources
cache_lock = threading.Lock()
app_active = True

# ==========================================
# 3. Helper Classes & Threads
# ==========================================

class CameraThread(threading.Thread):
    """Continuously captures frames from the camera to ensure zero lag."""
    def __init__(self, camera_index=0):
        super().__init__(daemon=True)
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(3, 640)
        self.cap.set(4, 480)
        if not self.cap.isOpened():
            print(f"Error: Camera {camera_index} failed to open.")

    def run(self):
        global app_active
        while app_active:
            success, img = self.cap.read()
            if success:
                # Keep only the latest frame
                if not frame_queue.empty():
                    try:
                        frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                frame_queue.put(img)
            else:
                time.sleep(0.1)
        self.cap.release()

class FaceProcessingThread(threading.Thread):
    """Handles heavy face recognition processing."""
    def __init__(self, encode_file='EncodeFile.p'):
        super().__init__(daemon=True)
        print("Loading Encode File ...")
        try:
            with open(encode_file, 'rb') as f:
                self.encodeListKnown, self.studentIds = pickle.load(f)
            print("Encode File Loaded")
        except FileNotFoundError:
            print(f"Error: {encode_file} not found!")
            self.encodeListKnown, self.studentIds = [], []

    def run(self):
        global app_active
        while app_active:
            if not frame_queue.empty():
                img = frame_queue.get()
                
                # Pre-process frame (resize for speed)
                imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
                imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
                
                faceCurFrame = face_recognition.face_locations(imgS)
                encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)
                
                found_matches = []
                for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
                    matches = face_recognition.compare_faces(self.encodeListKnown, encodeFace)
                    faceDis = face_recognition.face_distance(self.encodeListKnown, encodeFace)
                    
                    if len(faceDis) > 0:
                        matchIndex = np.argmin(faceDis)
                        if matches[matchIndex] and faceDis[matchIndex] < 0.50:
                            student_id = self.studentIds[matchIndex]
                            found_matches.append({
                                'id': student_id,
                                'bbox': faceLoc  # y1, x2, y2, x1
                            })
                
                # Push results back to UI
                if not result_queue.empty():
                    try:
                        result_queue.get_nowait()
                    except queue.Empty:
                        pass
                result_queue.put(found_matches)
            else:
                time.sleep(0.01)

class DatabaseThread(threading.Thread):
    """Handles Firebase operations and image loading asynchronously."""
    def run(self):
        global app_active
        while app_active:
            try:
                # Wait for a task (student_id)
                student_id = db_task_queue.get(timeout=1)
                
                with cache_lock:
                    if student_id not in student_cache:
                        print(f"Fetching data for {student_id}...")
                        # 1. Get info from Firebase
                        student_info = db.reference(f'Students/{student_id}').get()
                        
                        # 2. Get image from disk
                        img_path = f'Images/{student_id}.png'
                        img_student = None
                        if os.path.exists(img_path):
                            img_student = cv2.imread(img_path)
                        
                        # Cache it
                        student_cache[student_id] = {
                            'info': student_info,
                            'img': img_student,
                            'last_seen': datetime.now()
                        }
                    
                    # 3. Mark attendance logic (with cooldown)
                    current_time = datetime.now()
                    last_marked = attendance_cooldown.get(student_id)
                    
                    if last_marked is None or (current_time - last_marked).total_seconds() > COOLDOWN_SECONDS:
                        ref = db.reference(f'Students/{student_id}')
                        if student_cache[student_id]['info']:
                            student_cache[student_id]['info']['total_attendance'] += 1
                            ref.child('total_attendance').set(student_cache[student_id]['info']['total_attendance'])
                            ref.child('last_attendance_time').set(current_time.strftime("%Y-%m-%d %H:%M:%S"))
                            attendance_cooldown[student_id] = current_time
                            print(f"Attendance marked for: {student_cache[student_id]['info']['name']}")
                
                db_task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Database error: {e}")

# ==========================================
# 4. Main Application
# ==========================================

def main():
    global app_active
    
    # Load UI assets
    imgBackground = cv2.imread('Resources/background.png')
    folderModePath = 'Resources/Modes'
    imgModeList = [cv2.imread(os.path.join(folderModePath, p)) for p in os.listdir(folderModePath)] if os.path.exists(folderModePath) else []
    
    # Start threads
    cam_thread = CameraThread()
    proc_thread = FaceProcessingThread()
    db_thread = DatabaseThread()
    
    cam_thread.start()
    proc_thread.start()
    db_thread.start()
    
    modeType = 0
    counter = 0
    id = -1
    
    print("Multi-threaded Attendance System Started. Press 'q' to quit.")
    
    while True:
        if not frame_queue.empty():
            img = frame_queue.get()
            
            # 1. Check for processing results
            current_results = []
            if not result_queue.empty():
                current_results = result_queue.get()
            
            # 2. Update Background
            imgBackground[162:162 + 480, 55:55 + 640] = img
            imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType] if modeType < len(imgModeList) else imgModeList[0]

            # 3. Process matches
            if current_results:
                for match in current_results:
                    id = match['id']
                    y1, x2, y2, x1 = match['bbox']
                    y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                    bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
                    imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)
                    
                    if counter == 0:
                        cvzone.putTextRect(imgBackground, "Loading", (275, 400))
                        # Signal database thread to fetch/mark
                        db_task_queue.put(id)
                        counter = 1
                        modeType = 1
            
            # 4. Handle UI Animation/States
            if counter != 0:
                if counter == 1:
                    # Check if data is in cache
                    with cache_lock:
                        if id in student_cache:
                            studentInfo = student_cache[id]['info']
                            imgStudent = student_cache[id]['img']
                            
                            if studentInfo:
                                # Update info on background
                                cv2.putText(imgBackground, str(studentInfo['total_attendance']), (861, 125),
                                           cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
                                cv2.putText(imgBackground, str(studentInfo['major']), (1006, 550),
                                           cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                                cv2.putText(imgBackground, str(id), (1006, 493),
                                           cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                                cv2.putText(imgBackground, str(studentInfo['CGPA']), (910, 625),
                                           cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                                cv2.putText(imgBackground, str(studentInfo['year']), (1025, 625),
                                           cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                                cv2.putText(imgBackground, str(studentInfo['starting_year']), (1125, 625),
                                           cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                                
                                (w, h), _ = cv2.getTextSize(studentInfo['name'], cv2.FONT_HERSHEY_COMPLEX, 1, 1)
                                offset = (414 - w) // 2
                                cv2.putText(imgBackground, str(studentInfo['name']), (808 + offset, 445),
                                           cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 50), 1)
                                
                                if imgStudent is not None:
                                    imgStudent_resized = cv2.resize(imgStudent, (216, 216))
                                    imgBackground[175:175 + 216, 909:909 + 216] = imgStudent_resized
                            
                            if counter > 2: # Give it a few frames to show "Loading"
                                modeType = 2
                        else:
                            # Still fetching...
                            modeType = 1
                
                counter += 1
                if counter >= 30: # Display for ~30 frames
                    counter = 0
                    modeType = 0
            
            cv2.imshow("Face Attendance", imgBackground)
            
        if cv2.waitKey(1) & 0xFF == ord('q'):
            app_active = False
            break

    cv2.destroyAllWindows()
    
    # Export attendance summary to CSV
    if attendance_cooldown:
        filename = f"attendance_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Student ID', 'Name', 'Total Attendance', 'Last Marked Time'])
                with cache_lock:
                    for s_id, last_time in attendance_cooldown.items():
                        info = student_cache.get(s_id, {}).get('info', {})
                        writer.writerow([
                            s_id, 
                            info.get('name', 'N/A'), 
                            info.get('total_attendance', 'N/A'),
                            last_time.strftime('%Y-%m-%d %H:%M:%S')
                        ])
            print(f"Attendance summary exported to {filename}")
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            
    print("Exiting...")

if __name__ == "__main__":
    main()
