#!/usr/bin/env bash
set -e

MODEL_NAME="tiny"

MODULE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHISPER_DIR="$MODULE_ROOT/third_party/whisper.cpp"
MODELS_DIR="$MODULE_ROOT/models"
LOCAL_MODEL_PATH="$MODELS_DIR/ggml-$MODEL_NAME.bin"

mkdir -p "$MODELS_DIR"

if [ ! -d "$WHISPER_DIR" ]; then
    echo "whisper.cpp submodule directory not found: $WHISPER_DIR"
    exit 1
fi

echo "Initialising/updating whisper.cpp submodule..."
cd "$MODULE_ROOT"
git submodule update --init --recursive -- third_party/whisper.cpp

if [ ! -f "$LOCAL_MODEL_PATH" ]; then
    echo "Downloading Whisper model: $MODEL_NAME"

    cd "$WHISPER_DIR"
    bash ./models/download-ggml-model.sh "$MODEL_NAME"

    DOWNLOADED_MODEL_PATH="$WHISPER_DIR/models/ggml-$MODEL_NAME.bin"

    if [ ! -f "$DOWNLOADED_MODEL_PATH" ]; then
        echo "Expected downloaded model not found: $DOWNLOADED_MODEL_PATH"
        exit 1
    fi

    cp "$DOWNLOADED_MODEL_PATH" "$LOCAL_MODEL_PATH"

    echo "Model copied to: $LOCAL_MODEL_PATH"
else
    echo "Model already exists: $LOCAL_MODEL_PATH"
fi

echo "Setup complete."