import sounddevice as sd
from scipy.io.wavfile import write
import librosa
import pickle
import numpy as np
import os

def extract_feature(file_path):
    
    # Load audio
    y, sr = librosa.load(file_path, sr=None)

    # Extract 13 MFCC features
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)

    # Take mean of MFCC values
    feature = np.mean(mfcc.T, axis=0)

    return feature


def verify_voice(username):

    print("Speak for verification...")

    fs = 44100
    duration = 3

    # Record voice
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()

    # Save temporary audio
    write("test_voice.wav", fs, recording)

    # Extract features
    features = extract_feature("test_voice.wav")

    # Load trained model
    model = pickle.load(open("voice_model.pkl", "rb"))

    # Predict user
    prediction = model.predict([features])

    # Prediction probability
    probability = model.predict_proba([features])
    confidence = max(probability[0]) * 100

    print("Predicted voice:", prediction[0])
    print("Expected user:", username)
    print("Confidence:", confidence)

    # Verification decision
    if str(prediction[0]).lower() == str(username).lower() and confidence >= 50:
        print("Voice verification result: True")
        return True
    else:
        print("Voice verification result: False")
        return False


if __name__ == "__main__":
    
    username = input("Enter username: ")
    
    result = verify_voice(username)

    print("Verification:", result)