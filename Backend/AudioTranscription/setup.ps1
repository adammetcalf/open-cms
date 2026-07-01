$ErrorActionPreference = "Stop"

$ModelName = "tiny"

$ModuleRoot = $PSScriptRoot
$WhisperDir = Join-Path $ModuleRoot "third_party\whisper.cpp"
$ModelsDir = Join-Path $ModuleRoot "models"
$LocalModelPath = Join-Path $ModelsDir "ggml-$ModelName.bin"

New-Item -ItemType Directory -Force -Path $ModelsDir | Out-Null

if (-not (Test-Path $WhisperDir)) {
    throw "whisper.cpp submodule directory not found: $WhisperDir"
}

Write-Host "Initialising/updating whisper.cpp submodule..."
Push-Location $ModuleRoot
try {
    git submodule update --init --recursive -- third_party/whisper.cpp
}
finally {
    Pop-Location
}

if (-not (Test-Path $LocalModelPath)) {
    Write-Host "Downloading Whisper model: $ModelName"

    Push-Location $WhisperDir
    try {
        .\models\download-ggml-model.cmd $ModelName
    }
    finally {
        Pop-Location
    }

    $DownloadedModelPath = Join-Path $WhisperDir "ggml-$ModelName.bin"

    if (-not (Test-Path $DownloadedModelPath)) {
        throw "Expected downloaded model not found: $DownloadedModelPath"
    }

    Copy-Item $DownloadedModelPath $LocalModelPath -Force

    Write-Host "Model copied to: $LocalModelPath"
}
else {
    Write-Host "Model already exists: $LocalModelPath"
}

Write-Host "Setup complete."