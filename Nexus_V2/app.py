import cv2
import time
import os
from core.camera import AsyncCamera
from core.recognizer import FaceEngine
from core.database import CloudSync
from core.ui import ModernDashboard

def main():
    # 0. Path Resolution
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MODEL_PATH = os.path.join(BASE_DIR, 'EncodeFile.p')
    KEY_PATH = os.path.join(BASE_DIR, 'serviceAccountKey.json')
    
    # 1. Configuration
    DB_URL = "https://attendancesystem-335f9-default-rtdb.firebaseio.com/"
    
    # 2. Initialize Modules
    cam = AsyncCamera()
    engine = FaceEngine(model_path=MODEL_PATH)
    db = CloudSync(key_path=KEY_PATH, db_url=DB_URL)
    ui = ModernDashboard()
    
    # 3. State Management
    current_student = None
    ui_status = "READY"
    display_timer = 0
    
    print("Nexus V2: Starting Orchestrator...")
    
    while True:
        # A. Capture
        frame = cam.get_frame()
        if frame is None: continue
        
        # B. Process Recognition
        engine.process_frame(frame)
        results = engine.get_results()
        
        # C. Handle Logic & Transitions
        if results and display_timer == 0:
            student_id = results[0]['id']
            ui_status = "SYNCING"
            
            # Fetch data & mark attendance
            try:
                current_student = db.get_student_data(student_id)
                success, msg = db.mark_attendance(student_id)
                
                if success:
                    ui_status = "SUCCESS"
                else:
                    ui_status = msg.upper()
            except Exception as e:
                print(f"Main Loop Error: {e}")
                ui_status = "AUTH ERROR"
                current_student = None
                
            display_timer = 1 # Start reset timer
            
        if display_timer > 0:
            display_timer += 1
            if display_timer > 100: # Show for ~100 frames
                display_timer = 0
                current_student = None
                ui_status = "READY"

        # D. Rendering Pipeline
        canvas = ui.create_base()
        canvas = ui.draw_camera(canvas, frame)
        canvas = ui.draw_face_overlay(canvas, results)
        canvas = ui.draw_student_card(canvas, current_student, ui_status)
        
        # E. Display
        cv2.imshow("NEXUS EDITION V2", canvas)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cam.release()
    cv2.destroyAllWindows()
    print("Nexus V2: Shutdown complete.")

if __name__ == "__main__":
    main()
