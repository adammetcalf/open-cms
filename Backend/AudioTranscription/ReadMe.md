# Audio Transcription

This is a bit of code designed to be callable from the backend.

The purpose of this library is to accept an audio file, process this audio file and return a transcription.

## Whisper
This library uses 'Whisper', from OpenAI. This is an open source automatic speech recognition model, trained on many hundreds of thousands of hours of audio.

Whisper is composed of 2 components: The inference engine (whisper.cpp) and the model. The model is available in various sizes with the obvious tradeoff between model size, and model speed and accuracy. This implentation is using the tiny model as a start point, but later we may updgrade to a larger model.

whisper.cpp has been added as a git submodule.

This ensures that everyone builds from the same dependency version. Whisper has been placed into the dir 'third_party/whisper.cpp/


## setup scripts
Because the models may be large, and already exist in someone else's repo I have not directly downloaded and included them in this project. Instead I have included a powershell script (for windows) `.\setup.ps1` and a shell script (for linux) `.\setup.sh` that will download the defined model. This keeps the repo lightweight.

These scripts perfrom the following:
1. Init the existing submodule for whisper.cpp
2. create the dir models/
3. download the configured model, which is currently 'tiny'.
4. copy this model into the dir models/

After running the script the project is ready to build without further configuration.


