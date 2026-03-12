import cv2
import os
import numpy as np

dataset_path = "dataset"

faces = []
labels = []
label_map = {}
current_label = 0

# Read dataset folders
for person in os.listdir(dataset_path):

    person_path = os.path.join(dataset_path, person)

    if not os.path.isdir(person_path):
        continue

    label_map[current_label] = person

    for img in os.listdir(person_path):

        img_path = os.path.join(person_path, img)

        image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

        faces.append(image)
        labels.append(current_label)

    current_label += 1

# Train recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()

recognizer.train(faces, np.array(labels))

recognizer.save("trainer.yml")

print("Training completed successfully!")