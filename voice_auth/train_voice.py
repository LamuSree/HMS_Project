import os
import numpy as np
import librosa
from sklearn.svm import SVC
import pickle

X = []
y = []

dataset_path = "voice_dataset"


def extract_feature(file_path):

    # Load audio
    y_audio, sr = librosa.load(file_path, sr=None)

    # Extract 13 MFCC features
    mfcc = librosa.feature.mfcc(y=y_audio, sr=sr, n_mfcc=13)

    # Convert to single feature vector
    feature = np.mean(mfcc.T, axis=0)

    return feature


# Read dataset
for user in os.listdir(dataset_path):

    user_path = os.path.join(dataset_path, user)

    if os.path.isdir(user_path):

        for file in os.listdir(user_path):

            if file.endswith(".wav"):

                file_path = os.path.join(user_path, file)

                feature = extract_feature(file_path)

                X.append(feature)
                y.append(user)

print("Training samples:", len(X))


# Train SVM model
model = SVC(kernel="linear", probability=True)

model.fit(X, y)


# Save trained model
with open("voice_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("Voice model trained successfully")