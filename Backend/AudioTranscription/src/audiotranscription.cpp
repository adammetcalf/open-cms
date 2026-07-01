#include "AudioTranscription.hpp"
#include "decode.hpp"

#include <filesystem>
#include <fstream>
#include <mutex>
#include <vector>

#include "whisper.h"

namespace fs = std::filesystem;

namespace
{
    whisper_context* g_context = nullptr;
    std::mutex g_mutex;
}

extern "C"
AUDIOTRANSCRIPTION_API int Initialise(const char* modelPath)
{
    if (modelPath == nullptr)
    {
        return 1;
    }

    std::lock_guard<std::mutex> lock(g_mutex);

    if (g_context != nullptr)
    {
        whisper_free(g_context);
        g_context = nullptr;
    }

    whisper_context_params ctxParams =
        whisper_context_default_params();

    g_context =
        whisper_init_from_file_with_params(
            modelPath,
            ctxParams);

    if (g_context == nullptr)
    {
        return 2;
    }

    return 0;
}

extern "C"
AUDIOTRANSCRIPTION_API int TranscribeFile(
    const char* inputFile,
    const char* outputFile)
{
    if (inputFile == nullptr || outputFile == nullptr)
    {
        return 1;
    }

    std::lock_guard<std::mutex> lock(g_mutex);

    if (g_context == nullptr)
    {
        return 2;
    }

    try
    {
        std::vector<float> pcm =
            AudioTranscription::DecodeAudioToMono16k(inputFile);

        if (pcm.empty())
        {
            return 3;
        }

        whisper_full_params params =
            whisper_full_default_params(
                WHISPER_SAMPLING_GREEDY);

        params.print_progress = false;
        params.print_special = false;
        params.print_realtime = false;
        params.print_timestamps = false;

        params.translate = false;
        params.language = "en";
        params.n_threads = 4;

        int result =
            whisper_full(
                g_context,
                params,
                pcm.data(),
                static_cast<int>(pcm.size()));

        if (result != 0)
        {
            return 4;
        }

        fs::path outPath(outputFile);

        if (outPath.has_parent_path())
        {
            fs::create_directories(outPath.parent_path());
        }

        std::ofstream out(outputFile);

        if (!out)
        {
            return 5;
        }

        const int n =
            whisper_full_n_segments(g_context);

        for (int i = 0; i < n; ++i)
        {
            out << whisper_full_get_segment_text(g_context, i);
        }

        return 0;
    }
    catch (...)
    {
        return 99;
    }
}

extern "C"
AUDIOTRANSCRIPTION_API void Shutdown()
{
    std::lock_guard<std::mutex> lock(g_mutex);

    if (g_context != nullptr)
    {
        whisper_free(g_context);
        g_context = nullptr;
    }
}