import os
import pickle
import numpy as np
import cv2
import face_recognition
import cvzone
from datetime import datetime, timedelta
from firebase_admin import credentials, db
import firebase_admin
import time

# Initialize Firebase only if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': "https://attendancesystem-335f9-default-rtdb.firebaseio.com/"
    })

# Camera setup with error checking
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open camera. Trying camera index 1...")
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: No camera found. Please check your camera connection.")
        exit()

cap.set(3, 640)  # Width
cap.set(4, 480)  # Height

# Check if background image exists
background_path = 'Resources/background.png'
if os.path.exists(background_path):
    imgBackground = cv2.imread(background_path)
else:
    # Create a simple background if file doesn't exist
    imgBackground = np.zeros((720, 1280, 3), dtype=np.uint8)
    imgBackground[:] = (50, 50, 50)  # Dark gray background
    print("Background image not found. Using default background.")

# Importing the mode images into a list
folderModePath = 'Resources/Modes'
imgModeList = []
if os.path.exists(folderModePath):
    modePathList = os.listdir(folderModePath)
    for path in modePathList:
        imgModeList.append(cv2.imread(os.path.join(folderModePath, path)))
else:
    # Create default mode images if folder doesn't exist
    print("Mode images folder not found. Creating default mode images.")
    for i in range(4):
        mode_img = np.zeros((633, 414, 3), dtype=np.uint8)
        mode_img[:] = (100, 100, 100)
        cv2.putText(mode_img, f"Mode {i}", (150, 300), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        imgModeList.append(mode_img)

# Load the encoding file
print("Loading Encode File ...")
try:
    with open('EncodeFile.p', 'rb') as file:
        encodeListKnownWithIds = pickle.load(file)
    encodeListKnown, studentIds = encodeListKnownWithIds
    print("Encode File Loaded")
except FileNotFoundError:
    print("Error: EncodeFile.p not found. Please run EncodeGenerator.py first.")
    exit()

# Lecture management variables
LECTURE_DURATION = 60  # 60 minutes
RECHECK_INTERVAL = 30  # 30 minutes
lecture_start_time = None
lecture_active = False
last_recheck_time = None

# Attendance tracking variables
modeType = 0
counter = 0
id = -1
imgStudent = []
attendance_session = {}

def start_lecture():
    """Start a new lecture session"""
    global lecture_start_time, lecture_active, last_recheck_time, attendance_session
    lecture_start_time = datetime.now()
    lecture_active = True
    last_recheck_time = lecture_start_time
    attendance_session = {}
    print(f"Lecture started at {lecture_start_time.strftime('%H:%M:%S')}")
    return True

def is_lecture_time():
    """Check if we're within lecture hours (9 AM to 6 PM)"""
    current_hour = datetime.now().hour
    return 9 <= current_hour <= 18

def should_recheck_attendance():
    """Check if it's time for attendance recheck"""
    global last_recheck_time
    if not lecture_active or last_recheck_time is None:
        return False
    
    time_since_last_check = (datetime.now() - last_recheck_time).total_seconds() / 60
    return time_since_last_check >= RECHECK_INTERVAL

def end_lecture():
    """End the current lecture session"""
    global lecture_active, lecture_start_time
    if lecture_active:
        lecture_end_time = datetime.now()
        duration = (lecture_end_time - lecture_start_time).total_seconds() / 60
        print(f"Lecture ended. Duration: {duration:.1f} minutes")
        print(f"Students attended: {list(attendance_session.keys())}")
        lecture_active = False
    return True

def mark_attendance(student_id):
    """Mark attendance for a student"""
    global last_recheck_time, attendance_session
    
    try:
        # Get student info from database
        studentInfo = db.reference(f'Students/{student_id}').get()
        if not studentInfo:
            print(f"Student {student_id} not found in database")
            return False
        
        current_time = datetime.now()
        
        # Check if this is a recheck or first attendance
        if student_id in attendance_session:
            # This is a recheck
            last_attendance = attendance_session[student_id]['last_seen']
            time_diff = (current_time - last_attendance).total_seconds() / 60
            
            if time_diff >= RECHECK_INTERVAL - 5:  # 5 minute tolerance
                attendance_session[student_id]['rechecks'] += 1
                attendance_session[student_id]['last_seen'] = current_time
                print(f"Recheck attendance for {studentInfo['name']} - Recheck #{attendance_session[student_id]['rechecks']}")
        else:
            # First time attendance
            attendance_session[student_id] = {
                'first_seen': current_time,
                'last_seen': current_time,
                'rechecks': 0,
                'name': studentInfo['name']
            }
            
            # Update database only for first attendance
            ref = db.reference(f'Students/{student_id}')
            studentInfo['total_attendance'] += 1
            ref.child('total_attendance').set(studentInfo['total_attendance'])
            ref.child('last_attendance_time').set(current_time.strftime("%Y-%m-%d %H:%M:%S"))
            print(f"First attendance marked for {studentInfo['name']}")
        
        # Update last recheck time if this was a scheduled recheck
        if should_recheck_attendance():
            last_recheck_time = current_time
            
        return True
        
    except Exception as e:
        print(f"Error marking attendance: {e}")
        return False

# Main loop
print("Smart Attendance System Started")
print("Press 's' to start lecture, 'e' to end lecture, 'q' to quit")

while True:
    success, img = cap.read()
    
    if not success or img is None:
        print("Failed to capture image from camera")
        time.sleep(0.1)
        continue
    
    # Ensure image is in correct format
    if len(img.shape) != 3 or img.shape[2] != 3:
        print("Invalid image format from camera")
        continue
    
    # Resize and convert image for face recognition
    imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
    
    # Check if image is valid after conversion
    if imgS is None or imgS.size == 0:
        continue
    
    try:
        faceCurFrame = face_recognition.face_locations(imgS)
        encodeCurFrame = face_recognition.face_encodings(imgS, faceCurFrame)
    except Exception as e:
        print(f"Face recognition error: {e}")
        continue
    
    # Update background display
    if imgBackground.shape[0] >= 642 and imgBackground.shape[1] >= 695:
        imgBackground[162:162 + 480, 55:55 + 640] = img
    
    # Display mode image
    if len(imgModeList) > modeType and imgBackground.shape[0] >= 677 and imgBackground.shape[1] >= 1222:
        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
    
    # Display lecture status
    status_text = ""
    if lecture_active:
        elapsed_time = (datetime.now() - lecture_start_time).total_seconds() / 60
        status_text = f"Lecture Active - {elapsed_time:.1f} min"
        if elapsed_time >= LECTURE_DURATION:
            status_text += " (OVERTIME)"
    else:
        if is_lecture_time():
            status_text = "Ready - Press 's' to start lecture"
        else:
            status_text = "Outside lecture hours (9 AM - 6 PM)"
    
    cv2.putText(imgBackground, status_text, (50, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Display attendance count
    if lecture_active:
        count_text = f"Students Present: {len(attendance_session)}"
        cv2.putText(imgBackground, count_text, (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Process faces only during active lecture
    if faceCurFrame and lecture_active:
        for encodeFace, faceLoc in zip(encodeCurFrame, faceCurFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
            
            matchIndex = np.argmin(faceDis)
            
            if matches[matchIndex] and faceDis[matchIndex] < 0.50:  # Confidence threshold
                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
                imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)
                id = studentIds[matchIndex]
                
                if counter == 0:
                    cvzone.putTextRect(imgBackground, "Loading", (275, 400))
                    cv2.imshow("Face Attendance", imgBackground)
                    cv2.waitKey(1)
                    counter = 1
                    modeType = 1
        
        if counter != 0:
            if counter == 1:
                # Mark attendance
                if mark_attendance(id):
                    # Get the Image from local storage
                    img_path = f'Images/{id}.png'
                    if os.path.exists(img_path):
                        imgStudent = cv2.imread(img_path)
                    else:
                        # Create placeholder image if student image not found
                        imgStudent = np.zeros((216, 216, 3), dtype=np.uint8)
                        imgStudent[:] = (100, 100, 100)
                        cv2.putText(imgStudent, "No Image", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                else:
                    modeType = 3
                    counter = 0
                    if len(imgModeList) > modeType:
                        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
            
            if modeType != 3:
                if 10 < counter < 20:
                    modeType = 2
                
                if len(imgModeList) > modeType:
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
                
                if counter <= 10 and id in attendance_session:
                    # Get student info for display
                    try:
                        studentInfo = db.reference(f'Students/{id}').get()
                        if studentInfo:
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
                            
                            if imgStudent is not None and imgStudent.size > 0:
                                try:
                                    imgStudent_resized = cv2.resize(imgStudent, (216, 216))
                                    imgBackground[175:175 + 216, 909:909 + 216] = imgStudent_resized
                                except:
                                    pass
                    except Exception as e:
                        print(f"Error displaying student info: {e}")
                
                counter += 1
                
                if counter >= 20:
                    counter = 0
                    modeType = 0
                    imgStudent = []
                    if len(imgModeList) > modeType:
                        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
    else:
        modeType = 0
        counter = 0
    
    cv2.imshow("Face Attendance", imgBackground)
    
    # Handle keyboard input
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('s') and not lecture_active:
        start_lecture()
    elif key == ord('e') and lecture_active:
        end_lecture()

# Cleanup
cap.release()
cv2.destroyAllWindows()
print("System shutdown complete")
print ("Final attendance session data:")
for id, info in attendance_session.items():
    print(f"ID: {id}, Name: {info['name']}, Attendance: {info['total_attendance']}")
    




























































































