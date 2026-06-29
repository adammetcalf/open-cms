# Audio Transcription

This is a bit of code designed to be callable from the backend.

The purpose of this library is to accept an audio file, process this audio file and return a transcription.

## Whisper
This library uses 'Whisper', from OpenAI. This is an open source automatic speech recognition model, trained on many hundreds of thousands of hours of audio.

Whisper is composed of 2 components: The inference engine and the model. The model is available in various sizes with the obvious playoff between model size, and model speed and accuracy.