import cv2
import numpy as np

class ModernDashboard:
    """Renders a dynamic, high-end dashboard UI for the attendance system."""
    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.bg_color = (15, 15, 15) # Darker Gray
        self.accent_color = (0, 255, 150) # Neon Greenish
        
    def create_base(self):
        """Create the background canvas."""
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        canvas[:] = self.bg_color
        
        # Draw Side Panel Background (The info zone)
        cv2.rectangle(canvas, (800, 0), (self.width, self.height), (25, 25, 25), cv2.FILLED)
        
        # Draw Header
        cv2.putText(canvas, "NEXUS AI | ATTENDANCE COMMAND", (40, 50), 
                    cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
        cv2.line(canvas, (40, 65), (450, 65), self.accent_color, 1)
        
        return canvas

    def draw_camera(self, canvas, frame):
        """Overlay the camera frame."""
        if frame is None: return canvas
        
        # Standard camera size
        frame_res = cv2.resize(frame, (640, 480))
        
        # Center the camera in the left zone
        x, y = 80, 120
        canvas[y:y+480, x:x+640] = frame_res
        
        # Cyber-border
        cv2.rectangle(canvas, (x-2, y-2), (x+642, y+482), self.accent_color, 1)
        return canvas

    def draw_student_card(self, canvas, student_data, status="IDLE"):
        """Render the profile card."""
        panel_x = 840
        
        if student_data and student_data.get('info'):
            info = student_data['info']
            img = student_data.get('img')
            
            # Profile Photo
            if img is not None:
                img_res = cv2.resize(img, (200, 200))
                iy = 100
                canvas[iy:iy+200, panel_x+20:panel_x+220] = img_res
                cv2.rectangle(canvas, (panel_x+20, iy), (panel_x+220, iy+200), self.accent_color, 1)
            
            # Details
            ty = 360
            cv2.putText(canvas, str(info.get('name', 'N/A')).upper(), (panel_x, ty), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)
            
            details = [
                f"ID: {info.get('id', 'N/A')}",
                f"MAJOR: {info.get('major', 'N/A')}",
                f"YEAR: {info.get('year', 'N/A')}",
                f"TOTAL: {info.get('total_attendance', 0)}",
                f"CGPA: {info.get('CGPA', 'N/A')}"
            ]
            
            for i, text in enumerate(details):
                cv2.putText(canvas, text, (panel_x, ty + 60 + (i*40)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        else:
            cv2.putText(canvas, "SYSTEM READY", (panel_x + 30, 360), 
                        cv2.FONT_HERSHEY_DUPLEX, 0.7, (80, 80, 80), 1)
            
        # Status Badge
        cv2.putText(canvas, f"MODE: {status}", (40, 680), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.accent_color, 1)
        
        return canvas

    def draw_face_overlay(self, canvas, results):
        """Draw high-tech brackets."""
        for res in results:
            y1, x2, y2, x1 = [v * 4 for v in res['bbox']]
            cx, cy = 80 + x1, 120 + y1
            cw, ch = x2 - x1, y2 - y1
            
            # Stylish brackets
            l, th = 20, 2
            # TL
            cv2.line(canvas, (cx, cy), (cx + l, cy), self.accent_color, th)
            cv2.line(canvas, (cx, cy), (cx, cy + l), self.accent_color, th)
            # TR
            cv2.line(canvas, (cx + cw, cy), (cx + cw - l, cy), self.accent_color, th)
            cv2.line(canvas, (cx + cw, cy), (cx + cw, cy + l), self.accent_color, th)
            # BL
            cv2.line(canvas, (cx, cy + ch), (cx + l, cy + ch), self.accent_color, th)
            cv2.line(canvas, (cx, cy + ch), (cx, cy + ch - l), self.accent_color, th)
            # BR
            cv2.line(canvas, (cx + cw, cy + ch), (cx + cw - l, cy + ch), self.accent_color, th)
            cv2.line(canvas, (cx + cw, cy + ch), (cx + cw, cy + ch - l), self.accent_color, th)
            
        return canvas

