from pathlib import Path
import sys
import json

# Locate the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Add Application to the Python path
sys.path.insert(0, str(PROJECT_ROOT / "Application"))

from AudioTranscription import AudioTranscriber


def main():

    #audio_file = PROJECT_ROOT / "Tests" / "jfk.mp3"
    audio_file = PROJECT_ROOT / "Tests" / "Recording.m4a"

    with AudioTranscriber() as transcriber:

        result = transcriber.transcribe(audio_file)

    print(json.dumps(result, indent=4))


if __name__ == "__main__":
    main()