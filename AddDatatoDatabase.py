import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import os

def initialize_firebase():
    """Initialize Firebase connection"""
    try:
        # Check if Firebase is already initialized
        if firebase_admin._apps:
            print("Firebase already initialized")
            return True
            
        # Check if service account key exists
        if not os.path.exists("serviceAccountKey.json"):
            print("Error: serviceAccountKey.json not found!")
            print("Please download your Firebase service account key and save it as 'serviceAccountKey.json'")
            return False
        
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': "https://attendancesystem-335f9-default-rtdb.firebaseio.com/"
        })
        print("Firebase initialized successfully!")
        return True
        
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        return False

def add_sample_data():
    """Add sample student data to database"""
    try:
        ref = db.reference('Students')
        
        # Sample student data
        data = {
            "321654": {
                "name": "Rana Ram",
                "major": "CSE",
                "starting_year": 2021,
                "total_attendance": 0,  # Start with 0 attendance
                "CGPA": "8.4",
                "year": 4,
                "last_attendance_time": "2024-01-01 00:00:00"
            },
            "852741": {
                "name": "Emily Blunt",
                "major": "Economics",
                "starting_year": 2021,
                "total_attendance": 0,
                "CGPA": "8.0",
                "year": 1,
                "last_attendance_time": "2024-01-01 00:00:00"
            },
            "963852": {
                "name": "Elon Musk",
                "major": "Physics",
                "starting_year": 2020,
                "total_attendance": 0,
                "CGPA": "9.0",
                "year": 2,
                "last_attendance_time": "2024-01-01 00:00:00"
            }
        }
        
        # Add each student to database
        for student_id, student_info in data.items():
            ref.child(student_id).set(student_info)
            print(f"Added student: {student_info['name']} (ID: {student_id})")
        
        print("\nAll sample data added successfully!")
        return True
        
    except Exception as e:
        print(f"Error adding data to database: {e}")
        return False

def add_custom_student():
    """Add a custom student to the database"""
    try:
        print("\n--- Add New Student ---")
        student_id = input("Enter Student ID: ").strip()
        if not student_id:
            print("Student ID cannot be empty!")
            return False
        
        name = input("Enter Student Name: ").strip()
        if not name:
            print("Student name cannot be empty!")
            return False
            
        major = input("Enter Major/Department: ").strip() or "Not Specified"
        
        try:
            starting_year = int(input("Enter Starting Year: ").strip() or "2024")
            year = int(input("Enter Current Year (1-4): ").strip() or "1")
            cgpa = input("Enter CGPA: ").strip() or "0.0"
        except ValueError:
            print("Invalid input for year or CGPA!")
            return False
        
        # Create student data
        student_data = {
            "name": name,
            "major": major,
            "starting_year": starting_year,
            "total_attendance": 0,
            "CGPA": cgpa,
            "year": year,
            "last_attendance_time": "2024-01-01 00:00:00"
        }
        
        # Add to database
        ref = db.reference('Students')
        ref.child(student_id).set(student_data)
        
        print(f"\nStudent added successfully!")
        print(f"ID: {student_id}")
        print(f"Name: {name}")
        print(f"Major: {major}")
        
        return True
        
    except Exception as e:
        print(f"Error adding custom student: {e}")
        return False

def view_all_students():
    """View all students in database"""
    try:
        ref = db.reference('Students')
        students = ref.get()
        
        if not students:
            print("No students found in database!")
            return
        
        print("\n--- All Students in Database ---")
        print(f"{'ID':<10} {'Name':<20} {'Major':<15} {'Year':<5} {'Attendance':<12} {'CGPA':<6}")
        print("-" * 80)
        
        for student_id, student_info in students.items():
            print(f"{student_id:<10} {student_info.get('name', 'N/A'):<20} "
                  f"{student_info.get('major', 'N/A'):<15} {student_info.get('year', 'N/A'):<5} "
                  f"{student_info.get('total_attendance', 0):<12} {student_info.get('CGPA', 'N/A'):<6}")
        
    except Exception as e:
        print(f"Error viewing students: {e}")

def main():
    """Main function"""
    print("=== Smart Attendance System - Database Setup ===")
    
    # Initialize Firebase
    if not initialize_firebase():
        return
    
    while True:
        print("\nOptions:")
        print("1. Add sample data (3 demo students)")
        print("2. Add custom student")
        print("3. View all students")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            if add_sample_data():
                print("\nSample data added! You can now run EncodeGenerator.py")
                print("Make sure you have corresponding images in the 'Images' folder:")
                print("- 321654.png (Rana Ram)")
                print("- 852741.png (Emily Blunt)")  
                print("- 963852.png (Elon Musk)")
        
        elif choice == '2':
            if add_custom_student():
                print(f"\nDon't forget to add the student's photo in the 'Images' folder!")
        
        elif choice == '3':
            view_all_students()
        
        elif choice == '4':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice! Please enter 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()