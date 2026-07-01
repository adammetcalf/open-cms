#include "decode.hpp"

#include <stdexcept>
#include <string>
#include <vector>
#include <memory>

// exposed as C functions to avoid C++ name mangling issues with FFmpeg headers
extern "C"
{
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/channel_layout.h>
#include <libavutil/samplefmt.h>
#include <libavutil/opt.h>
#include <libswresample/swresample.h>
}

namespace
{
    constexpr int TARGET_SAMPLE_RATE = 16000;

    struct AVFormatContextDeleter
    {
        void operator()(AVFormatContext* ctx) const
        {
            if (ctx)
            {
                avformat_close_input(&ctx);
            }
        }
    };

    static void ThrowOnError(int errorCode, const std::string& message)
    {
        if (errorCode >= 0)
        {
            return;
        }

        char errorBuffer[AV_ERROR_MAX_STRING_SIZE] = {};
        av_strerror(errorCode, errorBuffer, sizeof(errorBuffer));
        throw std::runtime_error(message + ": " + errorBuffer);
    }

    static AVChannelLayout GetMonoLayout()
    {
        AVChannelLayout layout{};
        av_channel_layout_default(&layout, 1);
        return layout;
    }

    static AVChannelLayout GetDecoderChannelLayout(const AVCodecContext* codecContext)
    {
        AVChannelLayout layout{};

        if (codecContext->ch_layout.nb_channels > 0)
        {
            ThrowOnError(
                av_channel_layout_copy(&layout, &codecContext->ch_layout),
                "Failed to copy decoder channel layout"
            );
        }
        else
        {
            av_channel_layout_default(&layout, codecContext->channels);
        }

        return layout;
    }
}

namespace decode
{
    std::vector<float> DecodeAudioToMono16k(const std::string& inputPath)
    {
        AVFormatContext* rawFormatContext = nullptr;
        ThrowOnError(
            avformat_open_input(&rawFormatContext, inputPath.c_str(), nullptr, nullptr),
            "Failed to open input file"
        );

        std::unique_ptr<AVFormatContext, AVFormatContextDeleter> formatContext(rawFormatContext);

        ThrowOnError(
            avformat_find_stream_info(formatContext.get(), nullptr),
            "Failed to read stream info"
        );

        const int audioStreamIndex = av_find_best_stream(
            formatContext.get(),
            AVMEDIA_TYPE_AUDIO,
            -1,
            -1,
            nullptr,
            0
        );

        if (audioStreamIndex < 0)
        {
            throw std::runtime_error("No audio stream found in input file");
        }

        AVStream* audioStream = formatContext->streams[audioStreamIndex];
        const AVCodec* decoder = avcodec_find_decoder(audioStream->codecpar->codec_id);

        if (!decoder)
        {
            throw std::runtime_error("No suitable audio decoder found");
        }

        AVCodecContext* codecContext = avcodec_alloc_context3(decoder);
        if (!codecContext)
        {
            throw std::runtime_error("Failed to allocate codec context");
        }

        ThrowOnError(
            avcodec_parameters_to_context(codecContext, audioStream->codecpar),
            "Failed to copy codec parameters"
        );

        ThrowOnError(
            avcodec_open2(codecContext, decoder, nullptr),
            "Failed to open audio decoder"
        );

        AVChannelLayout inputLayout = GetDecoderChannelLayout(codecContext);
        AVChannelLayout outputLayout = GetMonoLayout();

        SwrContext* swrContext = nullptr;
        ThrowOnError(
            swr_alloc_set_opts2(
                &swrContext,
                &outputLayout,
                AV_SAMPLE_FMT_FLT,
                TARGET_SAMPLE_RATE,
                &inputLayout,
                codecContext->sample_fmt,
                codecContext->sample_rate,
                0,
                nullptr
            ),
            "Failed to allocate resampler"
        );

        ThrowOnError(swr_init(swrContext), "Failed to initialise resampler");

        AVPacket* packet = av_packet_alloc();
        AVFrame* frame = av_frame_alloc();

        if (!packet || !frame)
        {
            av_packet_free(&packet);
            av_frame_free(&frame);
            swr_free(&swrContext);
            av_channel_layout_uninit(&inputLayout);
            av_channel_layout_uninit(&outputLayout);
            avcodec_free_context(&codecContext);
            throw std::runtime_error("Failed to allocate FFmpeg packet/frame");
        }

        std::vector<float> outputSamples;

        auto receiveFrames = [&]()
        {
            while (true)
            {
                int receiveResult = avcodec_receive_frame(codecContext, frame);

                if (receiveResult == AVERROR(EAGAIN) || receiveResult == AVERROR_EOF)
                {
                    break;
                }

                ThrowOnError(receiveResult, "Failed while decoding audio frame");

                const int maxOutputSamples = static_cast<int>(
                    av_rescale_rnd(
                        swr_get_delay(swrContext, codecContext->sample_rate) + frame->nb_samples,
                        TARGET_SAMPLE_RATE,
                        codecContext->sample_rate,
                        AV_ROUND_UP
                    )
                );

                std::vector<float> converted(static_cast<size_t>(maxOutputSamples));
                uint8_t* outputData[] =
                {
                    reinterpret_cast<uint8_t*>(converted.data())
                };

                const int convertedSamples = swr_convert(
                    swrContext,
                    outputData,
                    maxOutputSamples,
                    const_cast<const uint8_t**>(frame->extended_data),
                    frame->nb_samples
                );

                ThrowOnError(convertedSamples, "Failed to resample audio");

                converted.resize(static_cast<size_t>(convertedSamples));
                outputSamples.insert(outputSamples.end(), converted.begin(), converted.end());

                av_frame_unref(frame);
            }
        };

        while (av_read_frame(formatContext.get(), packet) >= 0)
        {
            if (packet->stream_index == audioStreamIndex)
            {
                ThrowOnError(
                    avcodec_send_packet(codecContext, packet),
                    "Failed to send packet to decoder"
                );

                receiveFrames();
            }

            av_packet_unref(packet);
        }

        ThrowOnError(avcodec_send_packet(codecContext, nullptr), "Failed to flush decoder");
        receiveFrames();

        av_packet_free(&packet);
        av_frame_free(&frame);
        swr_free(&swrContext);
        av_channel_layout_uninit(&inputLayout);
        av_channel_layout_uninit(&outputLayout);
        avcodec_free_context(&codecContext);

        if (outputSamples.empty())
        {
            throw std::runtime_error("Decoded audio contained no samples");
        }

        return outputSamples;
    }
}
