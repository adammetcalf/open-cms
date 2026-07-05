cmake_minimum_required(VERSION 3.20)

project(AudioTranscription LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(FFMPEG REQUIRED)

add_subdirectory(third_party/whisper.cpp)

add_library(AudioTranscription SHARED
    src/audiotranscription.cpp
    src/decode.cpp
)

target_compile_definitions(AudioTranscription
    PRIVATE
        AUDIOTRANSCRIPTION_EXPORTS
)

target_include_directories(AudioTranscription
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
    PRIVATE
        ${FFMPEG_INCLUDE_DIRS}
)

target_link_libraries(AudioTranscription
    PRIVATE
        whisper
        ${FFMPEG_LIBRARIES}
)

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/models/ggml-tiny.bin")
    add_custom_command(TARGET AudioTranscription POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${CMAKE_CURRENT_SOURCE_DIR}/models/ggml-tiny.bin"
            "$<TARGET_FILE_DIR:AudioTranscription>/ggml-tiny.bin"
    )
endif()