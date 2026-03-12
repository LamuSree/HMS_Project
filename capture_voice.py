import sounddevice as sd
from scipy.io.wavfile import write
import os
import time

def record_voice(username):

    path = os.path.join("voice_dataset", username)
    os.makedirs(path, exist_ok=True)

    fs = 44100
    duration = 3

    print("\nRecording 10 voice samples")
    print("Say the same sentence each time\n")

    for i in range(1, 11):

        print(f"Sample {i} - Speak now...")

        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
        sd.wait()

        filename = os.path.join(path, f"voice{i}.wav")

        write(filename, fs, recording)

        print(f"Saved: {filename}\n")

        time.sleep(1)  # small pause between recordings

    print("\nVoice dataset created successfully!")


if __name__ == "__main__":

    username = input("Enter username: ")

    record_voice(username)