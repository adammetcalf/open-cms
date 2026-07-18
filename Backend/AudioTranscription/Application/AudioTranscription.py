from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AudioTranscriptionError(RuntimeError):
    """Raised when transcription or metadata extraction fails."""


class AudioTranscriber:
    """Cross-platform wrapper around the native AudioTranscription library."""

    INITIALISE_ERRORS = {
        1: "The model path was null",
        2: "Whisper failed to initialise the model",
    }

    TRANSCRIPTION_ERRORS = {
        1: "The input or output path was null",
        2: "Whisper has not been initialised",
        3: "The decoded audio contained no samples",
        4: "Whisper transcription failed",
        5: "The transcription output file could not be opened",
        99: "An unexpected native exception occurred",
    }

    RECORDING_DATE_TAGS = (
        "creation_time",
        "date",
        "recording_time",
        "recorded_date",
        "encoded_date",
        "originaldate",
        "original_date",
        "date_recorded",
    )

    def __init__(
        self,
        model_filename: str | None = None,
    ) -> None:
        self.application_directory = Path(__file__).resolve().parent
        self.model_directory = self.application_directory / "model"

        self.platform_name = self._detect_platform()
        self.native_directory = (
            self.application_directory / self.platform_name
        )

        self.library_path = self._find_native_library()
        self.model_path = self._find_model(model_filename)
        self.ffprobe_path = self._find_ffprobe()

        self._library: ctypes.CDLL | None = None
        self._dll_directory_handle: Any = None
        self._initialised = False

        self._load_library()
        self._configure_functions()
        self._initialise_model()

    @staticmethod
    def _detect_platform() -> str:
        system = platform.system().lower()

        if system == "windows":
            return "windows"

        if system == "linux":
            return "linux"

        raise AudioTranscriptionError(
            f"Unsupported operating system: {platform.system()}"
        )

    def _find_native_library(self) -> Path:
        if not self.native_directory.is_dir():
            raise AudioTranscriptionError(
                f"Native library directory does not exist: "
                f"{self.native_directory}"
            )

        if self.platform_name == "windows":
            possible_names = (
                "AudioTranscription.dll",
                "audiotranscription.dll",
            )
        else:
            possible_names = (
                "libAudioTranscription.so",
                "libaudiotranscription.so",
                "AudioTranscription.so",
                "audiotranscription.so",
            )

        for filename in possible_names:
            candidate = self.native_directory / filename

            if candidate.is_file():
                return candidate.resolve()

        expected = ", ".join(possible_names)

        raise AudioTranscriptionError(
            f"Native transcription library was not found in "
            f"'{self.native_directory}'. Expected one of: {expected}"
        )

    def _find_model(
        self,
        model_filename: str | None,
    ) -> Path:
        if not self.model_directory.is_dir():
            raise AudioTranscriptionError(
                f"Model directory does not exist: "
                f"{self.model_directory}"
            )

        if model_filename is not None:
            requested_model = (
                self.model_directory / model_filename
            ).resolve()

            if not requested_model.is_file():
                raise AudioTranscriptionError(
                    f"Requested model was not found: {requested_model}"
                )

            return requested_model

        models = sorted(
            path.resolve()
            for path in self.model_directory.glob("*.bin")
            if path.is_file()
        )

        if not models:
            raise AudioTranscriptionError(
                f"No .bin model was found in: "
                f"{self.model_directory}"
            )

        if len(models) > 1:
            model_names = ", ".join(
                model.name for model in models
            )

            raise AudioTranscriptionError(
                "Multiple Whisper models were found. Pass "
                f"model_filename to select one: {model_names}"
            )

        return models[0]

    def _find_ffprobe(self) -> str:
        if self.platform_name == "windows":
            local_names = (
                "ffprobe.exe",
                "bin/ffprobe.exe",
            )
        else:
            local_names = (
                "ffprobe",
                "bin/ffprobe",
            )

        for relative_name in local_names:
            candidate = self.native_directory / relative_name

            if candidate.is_file():
                return str(candidate.resolve())

        system_ffprobe = shutil.which("ffprobe")

        if system_ffprobe is not None:
            return system_ffprobe

        raise AudioTranscriptionError(
            "ffprobe was not found in the platform directory "
            "or on the system PATH"
        )

    def _load_library(self) -> None:
        try:
            if self.platform_name == "windows":
                if hasattr(os, "add_dll_directory"):
                    self._dll_directory_handle = (
                        os.add_dll_directory(
                            str(self.native_directory)
                        )
                    )

                self._library = ctypes.CDLL(
                    str(self.library_path)
                )

            else:
                self._library = ctypes.CDLL(
                    str(self.library_path),
                    mode=ctypes.RTLD_GLOBAL,
                )

        except OSError as exc:
            raise AudioTranscriptionError(
                f"Failed to load native library "
                f"'{self.library_path}': {exc}"
            ) from exc

    def _configure_functions(self) -> None:
        if self._library is None:
            raise AudioTranscriptionError(
                "The native library is not loaded"
            )

        try:
            self._library.Initialise.argtypes = [
                ctypes.c_char_p,
            ]
            self._library.Initialise.restype = ctypes.c_int

            self._library.TranscribeFile.argtypes = [
                ctypes.c_char_p,
                ctypes.c_char_p,
            ]
            self._library.TranscribeFile.restype = ctypes.c_int

            self._library.Shutdown.argtypes = []
            self._library.Shutdown.restype = None

        except AttributeError as exc:
            raise AudioTranscriptionError(
                "The native library does not export Initialise, "
                "TranscribeFile and Shutdown"
            ) from exc

    def _initialise_model(self) -> None:
        if self._library is None:
            raise AudioTranscriptionError(
                "The native library is not loaded"
            )

        result = self._library.Initialise(
            os.fsencode(self.model_path)
        )

        if result != 0:
            message = self.INITIALISE_ERRORS.get(
                result,
                "Unknown initialisation error",
            )

            raise AudioTranscriptionError(
                f"Initialise failed with code {result}: {message}"
            )

        self._initialised = True

    def transcribe(
        self,
        audio_path: str | Path,
    ) -> dict[str, Any]:
        """Transcribe an audio file and return structured data."""

        path = Path(audio_path).expanduser().resolve()

        if not path.is_file():
            raise FileNotFoundError(
                f"Audio file not found: {path}"
            )

        if not self._initialised or self._library is None:
            raise AudioTranscriptionError(
                "The Whisper model is not initialised"
            )

        metadata = self._extract_metadata(path)

        with tempfile.TemporaryDirectory(
            prefix="audio_transcription_"
        ) as temporary_directory:
            output_path = (
                Path(temporary_directory) / "transcription.txt"
            )

            result = self._library.TranscribeFile(
                os.fsencode(path),
                os.fsencode(output_path),
            )

            if result != 0:
                message = self.TRANSCRIPTION_ERRORS.get(
                    result,
                    "Unknown transcription error",
                )

                raise AudioTranscriptionError(
                    f"TranscribeFile failed with code "
                    f"{result}: {message}"
                )

            try:
                transcription_text = output_path.read_text(
                    encoding="utf-8"
                ).strip()
            except OSError as exc:
                raise AudioTranscriptionError(
                    f"Failed to read transcription output: {exc}"
                ) from exc

        return {
            "metadata": metadata,
            "transcription": {
                "text": transcription_text,
                "model": self.model_path.name,
            },
        }

    def transcribe_json(
        self,
        audio_path: str | Path,
        indent: int | None = 2,
    ) -> str:
        """Transcribe an audio file and return a JSON string."""

        return json.dumps(
            self.transcribe(audio_path),
            indent=indent,
            ensure_ascii=False,
        )

    def save_json(
        self,
        audio_path: str | Path,
        output_path: str | Path,
        indent: int | None = 2,
    ) -> Path:
        """Transcribe an audio file and save the result as JSON."""

        destination = Path(output_path).expanduser().resolve()
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        result = self.transcribe(audio_path)

        destination.write_text(
            json.dumps(
                result,
                indent=indent,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return destination

    def _extract_metadata(
        self,
        audio_path: Path,
    ) -> dict[str, Any]:
        command = [
            self.ffprobe_path,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(audio_path),
        ]

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
        except OSError as exc:
            raise AudioTranscriptionError(
                f"Failed to execute ffprobe: {exc}"
            ) from exc

        if process.returncode != 0:
            error = (
                process.stderr.strip()
                or "Unknown ffprobe error"
            )

            raise AudioTranscriptionError(
                f"ffprobe failed: {error}"
            )

        try:
            probe_data = json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            raise AudioTranscriptionError(
                "ffprobe returned invalid JSON"
            ) from exc

        streams = probe_data.get("streams", [])
        format_data = probe_data.get("format", {})

        audio_stream = next(
            (
                stream
                for stream in streams
                if stream.get("codec_type") == "audio"
            ),
            None,
        )

        if audio_stream is None:
            raise AudioTranscriptionError(
                f"No audio stream found in: {audio_path}"
            )

        file_stat = audio_path.stat()

        format_tags = self._normalise_tags(
            format_data.get("tags", {})
        )

        stream_tags = self._normalise_tags(
            audio_stream.get("tags", {})
        )

        recorded_at, recorded_at_tag = (
            self._find_recording_date(
                format_tags,
                stream_tags,
            )
        )

        return {
            "file": {
                "path": str(audio_path),
                "name": audio_path.name,
                "extension": audio_path.suffix.lower(),
                "size_bytes": file_stat.st_size,
                "filesystem_created_at": self._timestamp_to_iso(
                    file_stat.st_ctime
                ),
                "filesystem_modified_at": self._timestamp_to_iso(
                    file_stat.st_mtime
                ),
            },
            "audio": {
                "codec": audio_stream.get("codec_name"),
                "codec_long_name": audio_stream.get(
                    "codec_long_name"
                ),
                "sample_rate_hz": self._to_int(
                    audio_stream.get("sample_rate")
                ),
                "channels": self._to_int(
                    audio_stream.get("channels")
                ),
                "channel_layout": audio_stream.get(
                    "channel_layout"
                ),
                "sample_format": audio_stream.get(
                    "sample_fmt"
                ),
                "bit_rate_bps": self._to_int(
                    audio_stream.get("bit_rate")
                    or format_data.get("bit_rate")
                ),
                "duration_seconds": self._to_float(
                    audio_stream.get("duration")
                    or format_data.get("duration")
                ),
            },
            "recording": {
                "recorded_at": recorded_at,
                "recorded_at_source": (
                    "embedded_metadata"
                    if recorded_at is not None
                    else None
                ),
                "recorded_at_tag": recorded_at_tag,
            },
            "format": {
                "name": format_data.get("format_name"),
                "long_name": format_data.get(
                    "format_long_name"
                ),
                "tags": format_data.get("tags", {}),
            },
        }

    def _find_recording_date(
        self,
        format_tags: dict[str, Any],
        stream_tags: dict[str, Any],
    ) -> tuple[str | None, str | None]:
        combined_tags = {
            **stream_tags,
            **format_tags,
        }

        for tag_name in self.RECORDING_DATE_TAGS:
            value = combined_tags.get(tag_name)

            if value:
                return str(value), tag_name

        return None, None

    @staticmethod
    def _normalise_tags(
        tags: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            str(key).lower(): value
            for key, value in tags.items()
        }

    @staticmethod
    def _timestamp_to_iso(
        timestamp: float,
    ) -> str:
        return datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc,
        ).isoformat()

    @staticmethod
    def _to_int(
        value: Any,
    ) -> int | None:
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_float(
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def close(self) -> None:
        """Release the native Whisper context."""

        if self._initialised and self._library is not None:
            self._library.Shutdown()
            self._initialised = False

        if self._dll_directory_handle is not None:
            self._dll_directory_handle.close()
            self._dll_directory_handle = None

    def __enter__(self) -> "AudioTranscriber":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


if __name__ == "__main__":
    audio_file = input("Audio file: ").strip()

    try:
        with AudioTranscriber() as transcriber:
            print(
                transcriber.transcribe_json(audio_file)
            )

    except (
        AudioTranscriptionError,
        FileNotFoundError,
    ) as exc:
        print(f"Error: {exc}")