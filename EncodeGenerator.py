import cv2
import face_recognition
import pickle
import os

def create_images_folder():
    """Create Images folder if it doesn't exist"""
    if not os.path.exists('Images'):
        os.makedirs('Images')
        print("Created 'Images' folder. Please add student images (format: studentID.png)")
        return False
    return True

def findEncodings(imagesList):
    """Find face encodings for all images"""
    encodeList = []
    for i, img in enumerate(imagesList):
        if img is None:
            print(f"Warning: Could not load image at index {i}")
            continue
            
        try:
            # Convert BGR to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Find face encodings
            face_encodings = face_recognition.face_encodings(img_rgb)
            
            if len(face_encodings) == 0:
                print(f"Warning: No face found in image at index {i}")
                continue
            elif len(face_encodings) > 1:
                print(f"Warning: Multiple faces found in image at index {i}, using the first one")
            
            # Use the first face encoding
            encode = face_encodings[0]
            encodeList.append(encode)
            
        except Exception as e:
            print(f"Error processing image at index {i}: {e}")
            continue
    
    return encodeList

def main():
    # Check if Images folder exists
    if not create_images_folder():
        return
    
    # Get list of image files
    folderPath = 'Images'
    try:
        pathList = os.listdir(folderPath)
        pathList = [f for f in pathList if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    except FileNotFoundError:
        print("Error: Images folder not found!")
        return
    
    if not pathList:
        print("Error: No image files found in Images folder!")
        print("Please add student images with format: studentID.png (e.g., 321654.png)")
        return
    
    print(f"Found {len(pathList)} image files: {pathList}")
    
    # Load images and extract student IDs
    imgList = []
    studentIds = []
    
    for path in pathList:
        try:
            img_path = os.path.join(folderPath, path)
            img = cv2.imread(img_path)
            
            if img is None:
                print(f"Warning: Could not load image {path}")
                continue
            
            imgList.append(img)
            # Extract student ID from filename (remove extension)
            student_id = os.path.splitext(path)[0]
            studentIds.append(student_id)
            print(f"Loaded: {path} -> Student ID: {student_id}")
            
        except Exception as e:
            print(f"Error loading {path}: {e}")
            continue
    
    if not imgList:
        print("Error: No valid images could be loaded!")
        return
    
    print(f"\nProcessing {len(imgList)} images...")
    print("Student IDs:", studentIds)
    
    # Generate encodings
    print("\nEncoding Started ...")
    encodeListKnown = findEncodings(imgList)
    
    if len(encodeListKnown) != len(studentIds):
        print(f"Warning: Only {len(encodeListKnown)} out of {len(studentIds)} images were successfully encoded")
        # Remove student IDs for images that couldn't be encoded
        valid_studentIds = []
        for i, encode in enumerate(encodeListKnown):
            if i < len(studentIds):
                valid_studentIds.append(studentIds[i])
        studentIds = valid_studentIds
    
    if not encodeListKnown:
        print("Error: No face encodings could be generated!")
        return
    
    # Save encodings
    encodeListKnownWithIds = [encodeListKnown, studentIds]
    print("Encoding Complete")
    
    try:
        with open("EncodeFile.p", 'wb') as file:
            pickle.dump(encodeListKnownWithIds, file)
        print("File Saved Successfully!")
        print(f"Encoded {len(encodeListKnown)} faces for students: {studentIds}")
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    main()