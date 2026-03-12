import cv2
import os
import numpy as np

dataset_path = "dataset"

faces = []
labels = []
label_map = {}

label_id = 0

for user in os.listdir(dataset_path):

    user_path = os.path.join(dataset_path, user)

    label_map[label_id] = user

    for img in os.listdir(user_path):

        img_path = os.path.join(user_path, img)

        image = cv2.imread(img_path, 0)

        faces.append(image)

        labels.append(label_id)

    label_id += 1

recognizer = cv2.face.LBPHFaceRecognizer_create()

recognizer.train(faces, np.array(labels))

recognizer.save("face_model.yml")

print("Face model trained successfully")