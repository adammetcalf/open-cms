#pragma once

#ifdef _WIN32
    #ifdef AUDIOTRANSCRIPTION_EXPORTS
        #define AUDIOTRANSCRIPTION_API __declspec(dllexport)
    #else
        #define AUDIOTRANSCRIPTION_API __declspec(dllimport)
    #endif
#else
    #define AUDIOTRANSCRIPTION_API
#endif

extern "C"
{
    AUDIOTRANSCRIPTION_API int Initialise(const char* modelPath);

    AUDIOTRANSCRIPTION_API int TranscribeFile(
        const char* inputFile,
        const char* outputFile);

    AUDIOTRANSCRIPTION_API void Shutdown();
}