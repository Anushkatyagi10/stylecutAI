import json
import os
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict, Any

import cv2

from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector


# ============================================================
# FFPROBE
# ============================================================

def ffprobe_metadata(video_path: str) -> Dict[str, Any]:

    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        (
            "stream="
            "width,"
            "height,"
            "r_frame_rate,"
            "avg_frame_rate,"
            "nb_frames,"
            "codec_name,"
            "pix_fmt"
        ),
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        video_path,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)

    stream = data["streams"][0]
    fmt = data["format"]

    fps_value = (
        stream.get("avg_frame_rate")
        or stream.get("r_frame_rate")
        or "0/1"
    )

    numerator, denominator = fps_value.split("/")

    denominator = float(denominator)

    fps = (
        float(numerator) / denominator
        if denominator != 0
        else 0.0
    )

    raw_frames = stream.get("nb_frames")
    frame_count = int(raw_frames) if raw_frames and str(raw_frames).isdigit() else 0
    if frame_count <= 0:
        try:
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
        except Exception:
            pass

    duration = float(
        fmt.get("duration", 0)
    )
    if frame_count <= 0 and fps > 0 and duration > 0:
        frame_count = int(round(duration * fps))

    return {
        "duration_seconds": duration,

        "duration": duration,

        "width": int(
            stream.get("width", 0)
        ),

        "height": int(
            stream.get("height", 0)
        ),

        "fps": fps,

        "frame_count": frame_count,

        "codec": stream.get("codec_name"),

        "pixel_format": stream.get("pix_fmt"),
    }


# ============================================================
# PYSCENEDETECT
# ============================================================

def detect_scenes(
    video_path: str,
    threshold: float = 27.0,
    min_scene_len: int = 15,
) -> List[Dict[str, Any]]:

    video = open_video(video_path)

    manager = SceneManager()

    detector = ContentDetector(
        threshold=threshold,
        min_scene_len=min_scene_len,
    )

    manager.add_detector(detector)

    manager.detect_scenes(video)

    scene_list = manager.get_scene_list()

    scenes = []

    for index, (start, end) in enumerate(
        scene_list,
        start=1,
    ):

        start_seconds = start.get_seconds()
        end_seconds = end.get_seconds()

        scenes.append(
            {
                "segment_id": (
                    f"segment_{index:03d}"
                ),

                "start_time": start_seconds,

                "end_time": end_seconds,

                "duration": (
                    end_seconds - start_seconds
                ),
            }
        )

    # No cuts = entire video is one segment.
    if not scenes:

        metadata = ffprobe_metadata(
            video_path
        )

        duration = metadata[
            "duration_seconds"
        ]

        scenes.append(
            {
                "segment_id": "segment_001",
                "start_time": 0.0,
                "end_time": duration,
                "duration": duration,
            }
        )

    return scenes


# ============================================================
# OPENCV REPRESENTATIVE FRAMES
# ============================================================

def extract_representative_frames(
    video_path: str,
    output_dir: str,
    start_time: float,
    end_time: float,
    samples: int = 5,
) -> List[Dict[str, Any]]:

    output_dir = Path(output_dir)
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    cap = cv2.VideoCapture(
        video_path
    )

    if not cap.isOpened():
        raise RuntimeError(
            f"Cannot open {video_path}"
        )

    duration = end_time - start_time

    frames = []

    for i in range(samples):

        if samples == 1:
            relative = duration / 2
        else:
            relative = (
                duration * i /
                (samples - 1)
            )

        timestamp = (
            start_time + relative
        )

        cap.set(
            cv2.CAP_PROP_POS_MSEC,
            timestamp * 1000,
        )

        success, frame = cap.read()

        if not success:
            continue

        output_path = (
            output_dir /
            f"{timestamp:.3f}.jpg"
        )

        cv2.imwrite(
            str(output_path),
            frame,
        )

        frames.append(
            {
                "timestamp": timestamp,
                "path": str(output_path),
            }
        )

    cap.release()

    return frames


# ============================================================
# OPENCV MOTION ANALYSIS
# ============================================================

def analyze_motion(
    video_path: str,
    start_time: float,
    end_time: float,
    samples: int = 20,
) -> Dict[str, Any]:

    cap = cv2.VideoCapture(
        video_path
    )

    if not cap.isOpened():
        raise RuntimeError(
            f"Cannot open {video_path}"
        )

    duration = end_time - start_time

    previous = None
    scores = []

    for i in range(samples):

        timestamp = (
            start_time +
            duration * i /
            max(samples - 1, 1)
        )

        cap.set(
            cv2.CAP_PROP_POS_MSEC,
            timestamp * 1000,
        )

        success, frame = cap.read()

        if not success:
            continue

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY,
        )

        gray = cv2.resize(
            gray,
            (320, 180),
        )

        if previous is not None:

            difference = cv2.absdiff(
                previous,
                gray,
            )

            scores.append(
                float(difference.mean())
            )

        previous = gray

    cap.release()

    if not scores:

        return {
            "motion_score": 0.0,
            "motion_level": "unknown",
        }

    score = sum(scores) / len(scores)

    if score < 3:
        level = "very_low"
    elif score < 8:
        level = "low"
    elif score < 15:
        level = "medium"
    elif score < 25:
        level = "high"
    else:
        level = "very_high"

    return {
        "motion_score": round(score, 3),
        "motion_level": level,
    }


# ============================================================
# FFMPEG SEGMENT EXTRACTION
# ============================================================

def extract_segment(
    video_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
):

    duration = end_time - start_time

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start_time),
        "-i",
        video_path,
        "-t",
        str(duration),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c",
        "copy",
        output_path,
    ]

    subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
    )


# ============================================================
# FFMPEG RUN
# ============================================================

def run_ffmpeg(
    command: List[str],
    cwd: str | Path | None = None,
):

    if command and command[0] == "ffmpeg" and shutil.which("ffmpeg") is None:
        try:
            import imageio_ffmpeg
        except ImportError as exc:
            raise FileNotFoundError(
                "FFmpeg is not available on PATH. Install FFmpeg or "
                "the imageio-ffmpeg package."
            ) from exc

        command = [imageio_ffmpeg.get_ffmpeg_exe(), *command[1:]]

    subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        cwd=cwd,
    )


# ============================================================
# AUTOMATED SUBTITLING
# ============================================================

@contextmanager
def _ffmpeg_on_path():
    """Expose the bundled FFmpeg as ``ffmpeg`` for Whisper subprocesses."""

    if shutil.which("ffmpeg") is not None:
        yield
        return

    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise FileNotFoundError(
            "Whisper requires FFmpeg on PATH. Install FFmpeg or "
            "the imageio-ffmpeg package."
        ) from exc

    ffmpeg_executable = Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve()
    with tempfile.TemporaryDirectory(prefix="stylecut_ffmpeg_bin_") as bin_dir:
        bin_dir_path = Path(bin_dir)
        (bin_dir_path / "ffmpeg").symlink_to(ffmpeg_executable)
        previous_path = os.environ.get("PATH", "")
        os.environ["PATH"] = (
            str(bin_dir_path)
            + (os.pathsep + previous_path if previous_path else "")
        )
        try:
            yield
        finally:
            os.environ["PATH"] = previous_path

def extract_audio_from_video(
    video_path: str | Path,
    output_audio_path: str | Path | None = None,
) -> Path:
    """Extract the first audio stream as 16 kHz mono PCM WAV for Whisper."""

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if output_audio_path is None:
        output_audio_path = video_path.with_suffix(".wav")
    output_audio_path = Path(output_audio_path)
    output_audio_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-map",
        "0:a:0",
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_audio_path),
    ]
    run_ffmpeg(command)
    return output_audio_path


def _format_srt_timestamp(seconds: float) -> str:
    """Format seconds as the ``HH:MM:SS,mmm`` timestamp used by SRT."""

    milliseconds = max(0, round(float(seconds) * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return (
        f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},"
        f"{milliseconds:03d}"
    )


def _format_ass_timestamp(seconds: float) -> str:
    centiseconds = max(0, round(float(seconds) * 100))
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"


def _srt_timestamp_to_seconds(timestamp: str) -> float:
    timestamp = timestamp.strip().replace(".", ",")
    hours, minutes, seconds_and_ms = timestamp.split(":")
    seconds, milliseconds = seconds_and_ms.split(",", 1)
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(milliseconds.ljust(3, "0")[:3]) / 1000
    )


def _escape_ass_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\n", "\\N")
    )


def _write_animated_ass(
    subtitles_path: Path,
    ass_path: Path,
    frame_width: int,
    frame_height: int,
) -> None:
    """Convert word-timed SRT cues to the reference's upper-center pop style."""

    subtitle_text = subtitles_path.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\r?\n\s*\r?\n", subtitle_text.strip())
    # The reference uses bold white sans text around 3.5% of frame height,
    # centered near 33% height, with a restrained dark edge and word pop.
    font_size = max(18, round(frame_height * 0.035))
    center_x = frame_width // 2
    top_y = round(frame_height * 0.33)

    events = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_index = next(
            (index for index, line in enumerate(lines) if "-->" in line),
            None,
        )
        if timing_index is None:
            continue

        start_text, end_text = lines[timing_index].split("-->", 1)
        start = _srt_timestamp_to_seconds(start_text)
        end = max(start + 0.06, _srt_timestamp_to_seconds(end_text))
        caption = " ".join(lines[timing_index + 1:]).strip()
        if not caption:
            continue

        letters = re.sub(r"[^A-Za-z]", "", caption)
        emphasized = len(letters) > 1 and letters.isupper()
        cue_font_size = round(font_size * (1.3 if emphasized else 1.0))
        pop_from = 55 if emphasized else 75
        overrides = (
            f"\\an8\\pos({center_x},{top_y})\\fs{cue_font_size}"
            f"\\fscx{pop_from}\\fscy{pop_from}"
            "\\t(0,120,\\fscx110\\fscy110)"
            "\\t(120,200,\\fscx100\\fscy100)"
        )
        events.append(
            f"Dialogue: 0,{_format_ass_timestamp(start)},"
            f"{_format_ass_timestamp(end)},Caption,,0,0,0,,"
            f"{{{overrides}}}{_escape_ass_text(caption)}"
        )

    ass_header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {frame_width}\n"
        f"PlayResY: {frame_height}\n"
        "ScaledBorderAndShadow: yes\n"
        "WrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Caption,Arial,{font_size},&H00FFFFFF,&H00FFFFFF,"
        "&H70000000,&H00000000,-1,0,0,0,100,100,0,0,1,0.6,1.5,"
        "8,10,10,0,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
    )
    ass_path.write_text(
        ass_header + "\n".join(events) + ("\n" if events else ""),
        encoding="utf-8",
    )


def generate_srt_subtitles(
    audio_path: str | Path,
    output_srt_path: str | Path | None = None,
    model_name: str = "base",
) -> Path:
    """Transcribe audio with OpenAI Whisper and save timestamped SRT captions."""

    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if output_srt_path is None:
        output_srt_path = audio_path.with_suffix(".srt")
    output_srt_path = Path(output_srt_path)
    output_srt_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import whisper
    except ImportError as exc:
        raise ImportError(
            "OpenAI Whisper is required for subtitle transcription. "
            "Install it with `pip install openai-whisper`."
        ) from exc

    with _ffmpeg_on_path():
        model = whisper.load_model(model_name)
        transcription = model.transcribe(
            str(audio_path),
            verbose=False,
            word_timestamps=True,
        )

    timed_captions = []
    for segment in transcription.get("segments", []):
        words = segment.get("words") or []
        word_captions = [
            (
                max(0.0, float(word.get("start", segment.get("start", 0.0)))),
                str(word.get("word", "")).strip(),
                word,
            )
            for word in words
        ]
        word_captions = [entry for entry in word_captions if entry[1]]

        if word_captions:
            for start, text, word in word_captions:
                end = max(start + 0.06, float(word.get("end", start)))
                timed_captions.append((start, end, text))
            continue

        text = str(segment.get("text", "")).strip()
        if text:
            start = max(0.0, float(segment.get("start", 0.0)))
            end = max(start + 0.06, float(segment.get("end", start)))
            timed_captions.append((start, end, text))

    subtitle_entries = [
            "\n".join(
                (
                    str(index),
                    f"{_format_srt_timestamp(start)} --> "
                    f"{_format_srt_timestamp(end)}",
                    text,
                )
            )
        for index, (start, end, text) in enumerate(timed_captions, start=1)
    ]

    with output_srt_path.open("w", encoding="utf-8") as srt_file:
        if subtitle_entries:
            srt_file.write("\n\n".join(subtitle_entries) + "\n")

    return output_srt_path


def burn_subtitles_to_video(
    video_path: str | Path,
    subtitles_path: str | Path,
    output_video_path: str | Path,
) -> Path:
    """Render word-timed captions using the reference's upper-center style."""

    video_path = Path(video_path)
    subtitles_path = Path(subtitles_path)
    output_video_path = Path(output_video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not subtitles_path.exists():
        raise FileNotFoundError(f"Subtitle file not found: {subtitles_path}")
    if video_path.resolve() == output_video_path.resolve():
        raise ValueError("Input and output video paths must be different.")

    output_video_path.parent.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video to inspect subtitle layout: {video_path}")
    frame_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    capture.release()

    # Use a fixed subtitle filename and generate an animated ASS rendition so
    # arbitrary input paths need no filter escaping and per-word pop effects render.
    with tempfile.TemporaryDirectory(prefix="stylecut_subtitles_") as filter_dir:
        filter_dir_path = Path(filter_dir)
        local_subtitles_path = filter_dir_path / "subtitles.srt"
        shutil.copyfile(subtitles_path, local_subtitles_path)
        local_ass_path = filter_dir_path / "subtitles.ass"
        _write_animated_ass(
            local_subtitles_path,
            local_ass_path,
            frame_width,
            frame_height,
        )

        subtitle_filter = "subtitles=filename=subtitles.ass"
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path.resolve()),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            subtitle_filter,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(output_video_path.resolve()),
        ]
        run_ffmpeg(command, cwd=filter_dir_path)

    return output_video_path


def add_subtitles_to_video_pipeline(
    video_path: str | Path,
    output_video_path: str | Path | None = None,
    model_name: str = "base",
) -> Path:
    """Extract, transcribe, and hardsub a video, cleaning temporary files."""

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if output_video_path is None:
        output_video_path = video_path.with_name(
            f"{video_path.stem}_subtitled{video_path.suffix or '.mp4'}"
        )
    output_video_path = Path(output_video_path)

    with tempfile.TemporaryDirectory(prefix="stylecut_transcription_") as temp_dir:
        temp_dir_path = Path(temp_dir)
        audio_path = temp_dir_path / "audio.wav"
        subtitles_path = temp_dir_path / "subtitles.srt"

        extract_audio_from_video(video_path, audio_path)
        generate_srt_subtitles(audio_path, subtitles_path, model_name=model_name)
        burn_subtitles_to_video(video_path, subtitles_path, output_video_path)

    return output_video_path
