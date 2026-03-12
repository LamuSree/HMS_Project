import cv2
import os

def recognize_user(username):

    # Load trained model
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("trainer.yml")

    # Load face detector
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    cam = cv2.VideoCapture(0)

    print("Look at the camera for face verification...")

    ret, frame = cam.read()
    cam.release()

    if not ret:
        return False

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5
    )

    if len(faces) == 0:
        print("No face detected")
        return False

    for (x, y, w, h) in faces:

        face_img = gray[y:y+h, x:x+w]

        label, confidence = recognizer.predict(face_img)

        print("Label:", label)
        print("Confidence:", confidence)

        # Lower confidence = better match
        if confidence < 80:
            return True

    return False