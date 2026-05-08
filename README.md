# 🎯 Smart Attendance System with Real-Time Face Recognition

An advanced, high-performance automated attendance system leveraging **Computer Vision** and **Cloud Infrastructure**. This system utilizes a **Multi-threaded Producer-Consumer architecture** to ensure smooth real-time performance and integrates with **Firebase Realtime Database** for scalable cloud storage.

---

## 🌟 Key Features

- ⚡ **Multi-threaded Pipeline:** Separate threads for Camera Capture, Face Recognition, and Database I/O to maintain high FPS and zero UI lag.
- ☁️ **Firebase Cloud Integration:** Real-time data synchronization for student profiles and attendance records.
- 🧠 **Dlib-based Recognition:** High-accuracy face detection and 128D encoding comparison using `face_recognition`.
- 📊 **Smart Caching:** Local memory cache for student data and images to minimize network latency and API calls.
- 📝 **Auto-Attendance Logging:** Automated timestamping and attendance incrementing with a configurable cooldown to prevent duplicates.
- 📈 **Export Capability:** Generates a detailed CSV session summary upon exit.

---

## 🛠️ Tech Stack

- **Language:** Python 3.12+
- **Computer Vision:** OpenCV, face_recognition (dlib), cvzone
- **Cloud Backend:** Firebase Realtime Database, Firebase Admin SDK
- **Concurrency:** Python Threading & Queueing API
- **Data Handling:** NumPy, Pickle, CSV

---

## 📂 Project Structure

```
Attendance-System/
│
├── main.py                # Main application with multi-threaded pipeline
├── EncodeGenerator.py     # Script to generate face encodings from images
├── AddDatatoDatabase.py   # Database management and student profile setup
├── Images/                # Input student photos (format: ID.png)
├── Resources/             # UI assets (Background and Mode overlays)
├── EncodeFile.p           # Generated binary encoding file
├── requirements.txt       # Project dependencies
└── README.md              # Documentation
```

---

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/smart-attendance-system.git
   cd smart-attendance-system
   ```

2. **Set up Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Firebase Setup:**
   - Create a project on [Firebase Console](https://console.firebase.google.com/).
   - Enable **Realtime Database**.
   - Generate a `serviceAccountKey.json` and place it in the root directory.

4. **Initialize Data:**
   - Add student images to the `Images/` folder (e.g., `321654.png`).
   - Run `python AddDatatoDatabase.py` to populate the cloud database.
   - Run `python EncodeGenerator.py` to generate face encodings.

5. **Run Application:**
   ```bash
   python main.py
   ```

---

## 🏗️ Architecture Detail

This project implements a **Producer-Consumer pattern** to solve the common issue of UI freezing in real-time video applications:

1. **Camera Thread:** Continuously captures frames from hardware.
2. **Face Processing Thread:** Performs CPU-intensive face recognition on a separate thread.
3. **Database Worker Thread:** Handles all network I/O with Firebase asynchronously.
4. **UI Thread:** Renders the interface at maximum speed using non-blocking queues.

---

## 📈 Future Roadmap

- [ ] **Edge Deployment:** Optimization for Raspberry Pi / Jetson Nano.
- [ ] **Liveness Detection:** Anti-spoofing mechanism to prevent photo-based bypass.
- [ ] **Web Dashboard:** Interactive React-based dashboard for administrators.

---

## 👨‍💻 Contributors
- **Pushkar Kumar** - Core Developer
- **Rana Ram** - Backend & Architecture

---

## 📜 License
This project is licensed under the MIT License - see the LICENSE file for details.
