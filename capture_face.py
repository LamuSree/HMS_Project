import cv2
import os

username = input("Enter username: ")

path = "dataset/" + username

os.makedirs(path, exist_ok=True)

cam = cv2.VideoCapture(0)

count = 0

while count < 30:

    ret, frame = cam.read()

    cv2.imshow("Capture Face", frame)

    cv2.imwrite(f"{path}/{count}.jpg", frame)

    count += 1

    if cv2.waitKey(500) == 27:
        break

cam.release()
cv2.destroyAllWindows()

print("Face dataset created successfully")