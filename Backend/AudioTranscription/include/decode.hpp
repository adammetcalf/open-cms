#pragma once

#include <string>
#include <vector>

namespace decode
{
    // Decodes an audio/video file such as .mp4, .m4a, .wav, .mp3, etc.
    // Returns 16 kHz mono float PCM samples in range approximately [-1.0, 1.0],
    // suitable for whisper_full().
    std::vector<float> DecodeAudioToMono16k(const std::string& inputPath);
}
