# Audio Transcription

This is a bit of code designed to be callable from the backend for the purposes of transcribing audio. The intended application is to deal with voice notes from people on the ground.

The purpose of this library is to accept an audio file, process this audio file and return a transcription. For convencience, the `Application` directory contains the python file `AudioTranscription.py`, as well as the compiled Windows Dlls/Linux so files necessary to run. The c++ found in this `Backend/AudioTranscription` directory is all the code used to build these dlls. 

A virtual environment (.venv) has been used to manage the python packages required. If you need to create this:

```
py -m venv .venv
```

Or, if one is already created and you need to activate it (Windows):
```
.\.venv\Scripts\Activate.ps1
```

Or in Linux:
```
.\.venv\Scripts\Activate.sh
```

Currently there are no python requirements. However, in case there exist some in future a `requirements.txt` has been created. To use this (on startup when launching the virtual environment):

```
pip install -r requirements.txt
```

## dependencies
- Whisper
- FFmpeg

## Whisper
This library uses `Whisper`, from OpenAI. This is an open source automatic speech recognition model, trained on many hundreds of thousands of hours of audio.

`Whisper` is composed of 2 components: The inference engine (whisper.cpp) and the model. The model is available in various sizes with the obvious tradeoff between model size, and model speed and accuracy. This implentation is using the tiny model as a start point, but later we may updgrade to a larger model.

whisper.cpp has been added as a git submodule.

This ensures that everyone builds from the same dependency version. `Whisper` has been placed into the dir `third_party/whisper.cpp/`

## FFmpeg

`Whisper` expects 16 kHz mono PCM audio. FFmpeg can be used to convert any common audio file into the typ required by `Whisper`. FFmpeg has been installed using vcpkg (a package manager for C++).

On Windows:
```
vcpkg install ffmpeg:x64-windows
```

## setup scripts
Because the models may be large, and already exist in someone else's repo I have not directly downloaded and included them in this project. Instead I have included a powershell script (for windows) `.\setup.ps1` and a shell script (for linux) `.\setup.sh` that will download the defined model. This keeps this repo lightweight.

These scripts perfrom the following:
1. Init the existing submodule for whisper.cpp
2. create the dir models/
3. download the configured model, which is currently 'tiny'.
4. copy this model into the dir models/

After running the script the project is ready to build without further configuration.

Windows:
Temporarily allow scripts in vscode terminal (if necessary):
```
Set-ExecutionPolicy -Scope Process Bypass
```
Download the model:
```
\.setup.ps1
```

## Building the dll

The dlls have been built, as is standard, using CMake:
```
cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=C:/Workspace/vcpkg/scripts/buildsystems/vcpkg.cmake
cmake --build build --config Release
```


