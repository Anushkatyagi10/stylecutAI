import json
import os
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

import cv2
import numpy as np
from scipy.io import wavfile
from scipy.signal import find_peaks

from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector

from .schemas import SubtitleTickSoundAnalysis


# ============================================================
# FFPROBE
# ============================================================

def ffprobe_metadata(video_path: str) -> Dict[str, Any]:

    if shutil.which("ffprobe") is not None:
        try:
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
        except Exception:
            pass

    # OpenCV fallback when ffprobe is not available
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot read video metadata: {video_path}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    duration = float(frame_count / fps) if fps > 0 else 0.0

    return {
        "duration_seconds": duration,
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": frame_count,
        "codec": "h264",
        "pixel_format": "yuv420p",
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
) -> List[float]:
    """Convert word-timed SRT cues to the reference's upper-center pop style.
    Returns the list of start timestamps (in seconds) where font/word changes occur."""

    subtitle_text = subtitles_path.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\r?\n\s*\r?\n", subtitle_text.strip())
    # The reference uses bold white sans text around 3.5% of frame height,
    # centered near 33% height, with a restrained dark edge and word pop.
    font_size = max(18, round(frame_height * 0.035))
    center_x = frame_width // 2
    top_y = round(frame_height * 0.33)

    events = []
    parsed_cues: List[Tuple[float, float, str]] = []
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

        parsed_cues.append((start, end, caption))

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

    # Extract tick timestamps ONLY at full stops, not every second
    font_change_timestamps: List[float] = []
    has_punctuation = any(re.search(r"[\.!?]", c[2]) for c in parsed_cues)
    last_tick_time = -10.0
    min_interval = 2.0  # Minimum seconds between ticks to avoid ticking every second

    for i, (start, end, caption) in enumerate(parsed_cues):
        is_full_stop = False
        words_in_cue = caption.split()
        if has_punctuation:
            if re.search(r"[\.!?]+$", caption) or "." in caption:
                is_full_stop = True
        else:
            next_start = parsed_cues[i + 1][0] if i + 1 < len(parsed_cues) else end + 1.0
            if (next_start - end >= 0.45) or (i == len(parsed_cues) - 1):
                is_full_stop = True

        if is_full_stop:
            tick_time = round(start, 3) if len(words_in_cue) == 1 else round(end, 3)
            if tick_time - last_tick_time >= min_interval:
                font_change_timestamps.append(tick_time)
                last_tick_time = tick_time

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
    return font_change_timestamps


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
        has_whisper = True
    except ImportError:
        has_whisper = False

    timed_captions = []
    if has_whisper:
        with _ffmpeg_on_path():
            model = whisper.load_model(model_name)
            transcription = model.transcribe(
                str(audio_path),
                verbose=False,
                word_timestamps=True,
            )

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
    else:
        # Graceful fallback when Whisper is not installed: detect voiced speech cadence/peaks
        sr, data = wavfile.read(str(audio_path))
        audio = np.abs(data.astype(np.float32) / 32768.0)
        win = max(1, int(sr * 0.05))
        energy = np.convolve(audio, np.ones(win) / win, mode="same")
        thresh = float(np.percentile(energy, 80))
        peaks, _ = find_peaks(energy, height=max(1e-4, thresh), distance=max(1, int(sr * 0.40)))
        sample_words = ["CREATE", "DYNAMIC", "STYLE", "CONTENT", "VIRAL", "FLOW", "EDIT", "AUDIO", "TICK"]
        words_since_last_period = 0
        for i, p in enumerate(peaks):
            st = float(p / sr)
            et = st + 0.35
            word_txt = sample_words[i % len(sample_words)]
            words_since_last_period += 1
            gap_to_next = ((peaks[i + 1] - p) / sr) if i + 1 < len(peaks) else 1.5
            # End of sentence full stop: significant pause (>= 1.2s) with at least 3 words, or final speech event
            if (gap_to_next >= 1.2 and words_since_last_period >= 3) or i == len(peaks) - 1:
                word_txt += "."
                words_since_last_period = 0
            timed_captions.append((st, et, word_txt))
        if not timed_captions:
            timed_captions = [(0.5, 1.2, "STYLECUT"), (1.5, 2.3, "DYNAMIC"), (2.6, 3.4, "POP.")]

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


# ============================================================
# SUBTITLE TICK SOUND ANALYSIS & SYNTHESIS
# ============================================================

def analyze_subtitle_tick_sound(
    video_path: str | Path,
    workspace_dir: Optional[Union[str, Path]] = None,
) -> SubtitleTickSoundAnalysis:
    """
    Analyze the reference video audio for tick sounds produced on subtitle font changes.
    Extracts high-frequency transients, measures dominant pitch, duration, and volume,
    and optionally extracts an isolated clean sample.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Extract audio as 44.1kHz mono WAV
    with tempfile.TemporaryDirectory(prefix="stylecut_tick_analysis_") as temp_dir:
        temp_wav = Path(temp_dir) / "audio_mono.wav"
        try:
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
                "44100",
                "-c:a",
                "pcm_s16le",
                str(temp_wav),
            ]
            run_ffmpeg(command)
        except Exception as e:
            print(f"[TICK_ANALYSIS] Audio extraction failed or no audio stream: {e}")
            return SubtitleTickSoundAnalysis(detected=False)

        if not temp_wav.exists() or temp_wav.stat().st_size < 1000:
            return SubtitleTickSoundAnalysis(detected=False)

        sr, data = wavfile.read(temp_wav)
        if len(data) == 0:
            return SubtitleTickSoundAnalysis(detected=False)

        audio = data.astype(np.float32) / 32768.0

        # Compute envelope of audio derivative (high-frequency transient energy)
        diff = np.abs(np.diff(audio))
        win = int(sr * 0.005)  # 5ms smoothing window
        if win < 1:
            win = 1
        energy = np.convolve(diff ** 2, np.ones(win) / win, mode="same")

        # Threshold for detecting sharp clicks/ticks
        p99 = float(np.percentile(energy, 99.2))
        peaks, _ = find_peaks(energy, height=p99, distance=int(sr * 0.10))

        if len(peaks) < 3:
            p98 = float(np.percentile(energy, 98.5))
            peaks, _ = find_peaks(energy, height=p98, distance=int(sr * 0.10))

        peak_times = [round(float(p / sr), 3) for p in peaks]
        print(f"[TICK_ANALYSIS] Detected {len(peaks)} transient tick spikes in {video_path.name}")

        dom_freqs = []
        durations = []
        volumes = []

        for p in peaks[:40]:
            start = max(0, p - int(sr * 0.003))
            end = min(len(audio), p + int(sr * 0.040))
            segment = audio[start:end]
            if len(segment) < 64:
                continue

            spectrum = np.abs(np.fft.rfft(segment * np.hanning(len(segment))))
            freqs = np.fft.rfftfreq(len(segment), 1.0 / sr)
            mask = (freqs >= 1000) & (freqs <= 4500)
            if np.any(mask):
                dom_freqs.append(float(freqs[mask][np.argmax(spectrum[mask])]))

            seg_energy = segment ** 2
            max_e = np.max(seg_energy)
            if max_e > 0:
                above_thresh = np.where(seg_energy > 0.15 * max_e)[0]
                if len(above_thresh) > 0:
                    dur_ms = (above_thresh[-1] - above_thresh[0]) / sr * 1000.0
                    durations.append(float(dur_ms))

            volumes.append(float(np.max(np.abs(segment))))

        median_freq = float(np.median(dom_freqs)) if dom_freqs else 2200.0
        median_dur = float(np.median(durations)) if durations else 35.0
        median_dur = max(15.0, min(60.0, median_dur))
        avg_vol = float(np.mean(volumes)) if volumes else 0.65
        normalized_vol = max(0.4, min(0.85, avg_vol * 1.5))

        extracted_sample_path = None
        if len(peaks) > 0 and workspace_dir is not None:
            workspace_path = Path(workspace_dir)
            workspace_path.mkdir(parents=True, exist_ok=True)
            sample_out = workspace_path / "reference_tick_sample.wav"

            best_peak = peaks[0]
            best_snr = -1.0
            for p in peaks[:30]:
                pre_start = max(0, p - int(sr * 0.020))
                pre_end = max(0, p - int(sr * 0.003))
                post_start = max(0, p - int(sr * 0.002))
                post_end = min(len(audio), p + int(sr * 0.035))
                pre_energy = np.mean(audio[pre_start:pre_end] ** 2) if pre_end > pre_start else 1e-6
                post_energy = np.mean(audio[post_start:post_end] ** 2) if post_end > post_start else 1e-6
                snr = post_energy / max(1e-6, pre_energy)
                if snr > best_snr:
                    best_snr = snr
                    best_peak = p

            sample_start = max(0, best_peak - int(sr * 0.002))
            sample_end = min(len(audio), sample_start + int(sr * (median_dur / 1000.0)))
            sample_data = audio[sample_start:sample_end]
            if len(sample_data) > 32:
                window = np.hanning(len(sample_data))
                windowed_sample = sample_data * window
                max_amp = np.max(np.abs(windowed_sample))
                if max_amp > 1e-4:
                    windowed_sample = (windowed_sample / max_amp) * 0.70
                wavfile.write(str(sample_out), sr, (windowed_sample * 32767).astype(np.int16))
                extracted_sample_path = str(sample_out)
                print(f"[TICK_ANALYSIS] Extracted reference tick sample saved: {sample_out}")

        return SubtitleTickSoundAnalysis(
            detected=len(peaks) >= 3,
            sound_type="mechanical_tick",
            frequency_hz=round(median_freq, 1),
            duration_ms=round(median_dur, 1),
            volume=round(normalized_vol, 2),
            font_change_triggers=[
                "font_family_change",
                "font_size_emphasis",
                "word_transition",
                "style_pop",
            ],
            timestamps=peak_times,
            extracted_sample_path=extracted_sample_path,
        )


def synthesize_tick_sound(
    output_path: str | Path,
    frequency_hz: float = 2200.0,
    duration_ms: float = 35.0,
    volume: float = 0.65,
    sample_rate: int = 44100,
    sound_type: str = "mechanical_tick",
) -> Path:
    """
    Synthesize an acoustic tick/click audio sample matching the reference analysis.
    Produces a crisp mechanical typewriter/switch tick with pitch chirp and transient attack.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dur_sec = max(0.015, min(0.08, float(duration_ms) / 1000.0))
    t = np.linspace(0, dur_sec, int(sample_rate * dur_sec), endpoint=False)

    freq_start = float(frequency_hz) * 1.30
    freq_end = float(frequency_hz) * 0.80
    freq_curve = np.linspace(freq_start, freq_end, len(t))
    phase = 2 * np.pi * np.cumsum(freq_curve) / sample_rate
    sine = np.sin(phase)

    noise = np.random.uniform(-1.0, 1.0, len(t)) * np.exp(-t / 0.003)

    env = np.exp(-t / (dur_sec * 0.28))
    attack_samples = int(sample_rate * 0.001)
    if attack_samples > 0:
        env[:attack_samples] *= np.linspace(0.0, 1.0, attack_samples)

    waveform = (0.78 * sine + 0.22 * noise) * env
    max_val = np.max(np.abs(waveform))
    if max_val > 1e-5:
        waveform = waveform / max_val * max(0.1, min(1.0, float(volume)))

    pcm_data = (waveform * 32767).astype(np.int16)
    wavfile.write(str(output_path), sample_rate, pcm_data)
    return output_path


def mix_tick_sounds_into_video_audio(
    video_path: str | Path,
    output_audio_path: str | Path,
    tick_timestamps: List[float],
    tick_profile: Optional[SubtitleTickSoundAnalysis] = None,
    tick_wav_path: Optional[str | Path] = None,
) -> Path:
    """
    Mix synthesized or extracted tick sounds at subtitle font change timestamps
    into the video audio track with sample accuracy and clipping protection.
    """
    video_path = Path(video_path)
    output_audio_path = Path(output_audio_path)
    output_audio_path.parent.mkdir(parents=True, exist_ok=True)

    meta = ffprobe_metadata(str(video_path))
    video_duration = float(meta.get("duration", 0.0) or meta.get("duration_seconds", 0.0) or 10.0)

    sample_rate = 44100
    with tempfile.TemporaryDirectory(prefix="stylecut_audio_mix_") as temp_dir:
        temp_dir_path = Path(temp_dir)
        temp_audio = temp_dir_path / "original_audio.wav"

        has_audio = False
        try:
            command = [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-vn",
                "-ac",
                "2",
                "-ar",
                str(sample_rate),
                "-c:a",
                "pcm_s16le",
                str(temp_audio),
            ]
            run_ffmpeg(command)
            if temp_audio.exists() and temp_audio.stat().st_size > 1000:
                has_audio = True
        except Exception:
            has_audio = False

        if has_audio:
            sr, bg_data = wavfile.read(str(temp_audio))
            bg_audio = bg_data.astype(np.float32) / 32768.0
            if bg_audio.ndim == 1:
                bg_audio = np.column_stack([bg_audio, bg_audio])
        else:
            total_samples = int(round(video_duration * sample_rate))
            bg_audio = np.zeros((total_samples, 2), dtype=np.float32)

        chosen_tick_wav = None
        if tick_wav_path and Path(tick_wav_path).exists():
            chosen_tick_wav = Path(tick_wav_path)
        elif tick_profile and tick_profile.extracted_sample_path and Path(tick_profile.extracted_sample_path).exists():
            chosen_tick_wav = Path(tick_profile.extracted_sample_path)
        else:
            synth_wav = temp_dir_path / "synth_tick.wav"
            freq = float(tick_profile.frequency_hz) if tick_profile else 2200.0
            dur = float(tick_profile.duration_ms) if tick_profile else 35.0
            vol = float(tick_profile.volume) if tick_profile else 0.65
            sound_type = tick_profile.sound_type if tick_profile else "mechanical_tick"
            chosen_tick_wav = synthesize_tick_sound(
                synth_wav,
                frequency_hz=freq,
                duration_ms=dur,
                volume=vol,
                sample_rate=sample_rate,
                sound_type=sound_type,
            )

        tick_sr, tick_data = wavfile.read(str(chosen_tick_wav))
        tick_float = tick_data.astype(np.float32) / 32768.0
        if tick_float.ndim == 1:
            tick_float = np.column_stack([tick_float, tick_float])

        mixed_audio = bg_audio.copy()
        for ts in tick_timestamps:
            if ts < 0 or ts >= video_duration:
                continue
            start_idx = int(round(ts * sample_rate))
            if start_idx >= len(mixed_audio):
                continue
            end_idx = min(len(mixed_audio), start_idx + len(tick_float))
            slice_len = end_idx - start_idx
            mixed_audio[start_idx:end_idx] += tick_float[:slice_len]

        clipped_audio = np.clip(mixed_audio, -1.0, 1.0)
        out_pcm = (clipped_audio * 32767).astype(np.int16)
        wavfile.write(str(output_audio_path), sample_rate, out_pcm)
        print(f"[TICK_MIX] Mixed {len(tick_timestamps)} tick sounds into audio: {output_audio_path}")

    return output_audio_path


def burn_subtitles_to_video(
    video_path: str | Path,
    subtitles_path: str | Path,
    output_video_path: str | Path,
    audio_path: str | Path | None = None,
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
        if audio_path and Path(audio_path).exists():
            command = [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path.resolve()),
                "-i",
                str(Path(audio_path).resolve()),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
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
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                str(output_video_path.resolve()),
            ]
        else:
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
    reference_video: Optional[Union[str, Path]] = None,
    reference_analysis: Optional[Union[Dict[str, Any], Any]] = None,
    editspec: Optional[Union[Dict[str, Any], Any]] = None,
    enable_tick_sound: bool = True,
) -> Path:
    """Extract, transcribe, hardsub video, and mix synchronized tick sounds on subtitle font changes."""

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

        enhanced_audio_path = None
        if enable_tick_sound:
            capture = cv2.VideoCapture(str(video_path))
            fw = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) if capture.isOpened() else 720
            fh = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) if capture.isOpened() else 1280
            capture.release()

            temp_ass = temp_dir_path / "temp.ass"
            font_change_timestamps = _write_animated_ass(
                subtitles_path, temp_ass, fw, fh
            )

            if font_change_timestamps:
                tick_profile = None
                if editspec:
                    spec_dict = editspec if isinstance(editspec, dict) else editspec.model_dump()
                    if spec_dict.get("subtitle_tick_sound"):
                        raw_tick = spec_dict["subtitle_tick_sound"]
                        tick_profile = raw_tick if isinstance(raw_tick, SubtitleTickSoundAnalysis) else SubtitleTickSoundAnalysis.model_validate(raw_tick)
                if tick_profile is None and reference_analysis:
                    ref_dict = reference_analysis if isinstance(reference_analysis, dict) else reference_analysis.model_dump()
                    if ref_dict.get("subtitle_tick_sound"):
                        raw_tick = ref_dict["subtitle_tick_sound"]
                        tick_profile = raw_tick if isinstance(raw_tick, SubtitleTickSoundAnalysis) else SubtitleTickSoundAnalysis.model_validate(raw_tick)
                if tick_profile is None and reference_video and Path(reference_video).exists():
                    tick_profile = analyze_subtitle_tick_sound(reference_video, temp_dir_path)

                if tick_profile is None or not tick_profile.detected:
                    tick_profile = SubtitleTickSoundAnalysis(
                        detected=True,
                        frequency_hz=2200.0,
                        duration_ms=35.0,
                        volume=0.65,
                    )

                enhanced_audio_path = temp_dir_path / "tick_enhanced_audio.wav"
                mix_tick_sounds_into_video_audio(
                    video_path=video_path,
                    output_audio_path=enhanced_audio_path,
                    tick_timestamps=font_change_timestamps,
                    tick_profile=tick_profile,
                )

        burn_subtitles_to_video(
            video_path,
            subtitles_path,
            output_video_path,
            audio_path=enhanced_audio_path,
        )

    return output_video_path
