#!/usr/bin/env python3
"""Estimate subtitle styling from a reference video and apply it to a target.

The analysis is necessarily visual: once text is flattened into video frames,
the original font metadata and animation keyframes are gone. This script scans
every reference frame with OpenCV to estimate caption typography, bounds, and
motion, then renders Whisper-timed phrase clips with MoviePy.

Requirements:
    pip install -r requirements.txt
    OpenCV, MoviePy, Whisper, and imageio-ffmpeg must be installed.

Example:
    python style_transfer_subtitles.py \
        --reference "data/reference.mp4" --target "data/target.mp4"
"""

from __future__ import annotations

import argparse
import bisect
import contextlib
import inspect
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator, Optional


@dataclass
class SubtitleStyle:
    reference_width: int
    reference_height: int
    font_family_estimate: str
    font_size_reference_px: float
    font_size_reference_video_height_ratio: float
    color: str
    stroke_color: str
    stroke_width_reference_px: float
    stroke_width_font_ratio: float
    shadow_color: str
    shadow_width_reference_px: float
    caption_box_x_ratio: float
    caption_box_y_ratio: float
    caption_box_width_ratio: float
    caption_box_height_ratio: float
    center_x_ratio: float
    center_y_ratio: float
    pop_scale: float
    uppercase_scale: float
    sampled_text_observations: int
    reference_frames_scanned: int
    reference_duration_seconds: float
    motion_trajectory: list[dict[str, float]]
    analysis_notes: list[str]


def _discover_video(directory: Path, kind: str) -> Path:
    patterns = ("reference*.mp4", "reference*.mov", "reference*.mkv") if kind == "reference" else (
        "target*.mp4", "target*.mov", "target*.mkv"
    )
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(directory.glob(pattern))
    candidates = sorted(
        path for path in set(candidates)
        if path.is_file()
        and not re.search(r"(?:_subtitled|_styled_subtitled|_styled)$", path.stem, re.I)
    )
    if not candidates:
        raise FileNotFoundError(
            f"No {kind} video found in {directory}. Pass --{kind} with an explicit path."
        )
    if len(candidates) != 1:
        listing = "\n  ".join(str(path) for path in candidates)
        raise ValueError(
            f"More than one {kind} video was found. Pass --{kind} explicitly:\n  {listing}"
        )
    return candidates[0]


def _hex_color(rgb: tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % rgb


def _sample_text_color(frame: Any, box: tuple[int, int, int, int]) -> Optional[tuple[int, int, int]]:
    import cv2
    import numpy as np

    x, y, width, height = box
    crop = frame[max(0, y):max(0, y) + height, max(0, x):max(0, x) + width]
    if crop.size == 0:
        return None
    bgr = crop.reshape(-1, 3).astype("uint8")
    maximum = bgr.max(axis=1)
    minimum = bgr.min(axis=1)
    # Bright neutral pixels capture white captions; saturated warm pixels
    # capture common yellow emphasis. Avoid simply sampling the dark outline.
    white = bgr[(minimum > 155) & ((maximum - minimum) < 65)]
    yellow = bgr[(bgr[:, 2] > 150) & (bgr[:, 1] > 115) & (bgr[:, 0] < 145)]
    if len(yellow) > max(2, len(white) * 0.18):
        values = yellow
    elif len(white):
        values = white
    else:
        luminance = (0.114 * bgr[:, 0] + 0.587 * bgr[:, 1] + 0.299 * bgr[:, 2])
        values = bgr[luminance >= float(np.percentile(luminance, 90))]
    if not len(values):
        return None
    median_bgr = tuple(int(round(value)) for value in np.median(values, axis=0))
    return median_bgr[2], median_bgr[1], median_bgr[0]


def _sample_outline_color(frame: Any, box: tuple[int, int, int, int]) -> Optional[tuple[int, int, int]]:
    import cv2
    import numpy as np

    x, y, width, height = box
    pad = max(2, int(round(min(width, height) * 0.08)))
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(frame.shape[1], x + width + pad), min(frame.shape[0], y + height + pad)
    crop = frame[y0:y1, x0:x1]
    if crop.size == 0:
        return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    # Dark pixels in the OCR box neighborhood are an outline/shadow estimate.
    dark = crop[gray < 65]
    if len(dark) < 4:
        return None
    median_bgr = tuple(int(round(value)) for value in np.median(dark, axis=0))
    return median_bgr[2], median_bgr[1], median_bgr[0]


def _analyze_reference_opencv(
    reference_path: Path,
    sample_fps: float = 4.0,
    max_samples: int = 320,
) -> SubtitleStyle:
    """Scan every reference frame and estimate caption style and motion from pixels."""
    import cv2
    import numpy as np

    capture = cv2.VideoCapture(str(reference_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open reference video: {reference_path}")
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if not width or not height:
        capture.release()
        raise RuntimeError(f"Could not read dimensions from {reference_path}")
    total_frames = max(1, total_frames)
    duration = total_frames / fps if fps else 0.0
    detections: list[dict[str, Any]] = []
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 3))

    for frame_number in range(total_frames):
        ok, frame = capture.read()
        if not ok:
            continue
        timestamp = frame_number / fps if fps else float(frame_number)
        min_channel = frame.min(axis=2)
        max_channel = frame.max(axis=2)
        # Detect bright, neutral caption pixels throughout the full frame so
        # captions that move vertically can still be tracked.
        mask = ((min_channel > 228) & ((max_channel - min_channel) < 45)).astype("uint8") * 255
        mask[:, :int(width * 0.06)] = 0
        mask[:, int(width * 0.94):] = 0
        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)),
        )
        merged = cv2.dilate(mask, kernel, iterations=1)
        count, _, stats, _ = cv2.connectedComponentsWithStats(merged, connectivity=8)
        components = []
        for x, y, box_width, box_height, area in stats[1:count]:
            if (
                box_height < max(14, int(height * 0.012))
                or box_height > height * 0.09
                or box_width < max(48, int(width * 0.065))
                or box_width > width * 0.78
                or area < 300
            ):
                continue
            center_x = (x + box_width / 2) / width
            center_y = (y + box_height / 2) / height
            if not 0.10 <= center_x <= 0.90 or not 0.06 <= center_y <= 0.94:
                continue
            components.append((int(x), int(y), int(box_width), int(box_height)))

        # Join separate words that sit on the same caption line. Components
        # are sorted vertically and clustered by their center y coordinate.
        components.sort(key=lambda box: box[1] + box[3] / 2)
        lines: list[list[tuple[int, int, int, int]]] = []
        for box in components:
            box_center_y = box[1] + box[3] / 2
            matching = next(
                (line for line in lines if abs(
                    statistics.median(item[1] + item[3] / 2 for item in line) - box_center_y
                ) <= height * 0.022),
                None,
            )
            if matching is None:
                lines.append([box])
            else:
                matching.append(box)

        for line in lines:
            left = min(item[0] for item in line)
            top = min(item[1] for item in line)
            right = max(item[0] + item[2] for item in line)
            bottom = max(item[1] + item[3] for item in line)
            box_width, box_height = right - left, bottom - top
            if box_width < width * 0.08:
                continue
            box = (left, top, box_width, box_height)
            detections.append({
                "timestamp": timestamp,
                "x_ratio": (left + right) / (2 * width),
                "y_ratio": (top + bottom) / (2 * height),
                "left_ratio": left / width,
                "top_ratio": top / height,
                "width_ratio": box_width / width,
                "height_ratio": box_height / height,
                "color": _sample_text_color(frame, box),
                "outline": _sample_outline_color(frame, box),
            })
    capture.release()

    # Prefer the dominant centered text band; this rejects bright scene
    # details (lamps, signs, and props) that can resemble glyphs in isolated
    # frames while still allowing moderate subtitle movement around that band.
    central_candidates = [
        item for item in detections
        if 0.25 <= item["x_ratio"] <= 0.75 and 0.10 <= item["y_ratio"] <= 0.75
    ]
    if central_candidates:
        bands: dict[int, list[dict[str, Any]]] = {}
        for item in central_candidates:
            band = int(round(item["y_ratio"] / 0.015))
            bands.setdefault(band, []).append(item)
        dominant_y = max(bands, key=lambda band: len(bands[band])) * 0.015
        caption_candidates = [
            item for item in central_candidates
            if abs(item["y_ratio"] - dominant_y) <= 0.12
        ]
    else:
        dominant_y = 0.5
        caption_candidates = []

    # Link per-frame candidates into the most consistent caption track. The
    # selected points retain actual frame timestamps for later resampling.
    by_frame: dict[int, list[dict[str, Any]]] = {}
    for item in caption_candidates:
        frame_number = int(round(item["timestamp"] * fps)) if fps else 0
        by_frame.setdefault(frame_number, []).append(item)
    tracked: list[dict[str, Any]] = []
    previous: Optional[dict[str, Any]] = None
    for frame_number, candidates in sorted(by_frame.items()):
        if previous is not None and candidates and (frame_number / max(fps, 1.0) - previous["timestamp"]) <= 0.8:
            chosen = min(candidates, key=lambda item: (
                abs(item["y_ratio"] - previous["y_ratio"]) * 2.5
                + abs(item["x_ratio"] - previous["x_ratio"])
                - min(item["width_ratio"], 0.6) * 0.08
            ))
        else:
            chosen = min(candidates, key=lambda item: (
                abs(item["x_ratio"] - 0.5) * 0.7 - min(item["width_ratio"], 0.6) * 0.12
            ))
        tracked.append(chosen)
        previous = chosen

    notes = [
        "OpenCV scanned the reference video frame by frame and tracked bright caption bounding boxes.",
        "Font family and exact animation keyframes cannot be recovered from flattened pixels; the selected font and smooth word-pop curve are visual approximations.",
    ]
    if tracked:
        captions = tracked
        median = lambda field: float(statistics.median(item[field] for item in captions))
        colors = [item["color"] for item in captions if item["color"]]
        outlines = [item["outline"] for item in captions if item["outline"]]
        color = _hex_color(tuple(
            int(statistics.median(value[channel] for value in colors))
            for channel in range(3)
        )) if colors else "#FFFFFF"
        outline_color = _hex_color(tuple(
            int(statistics.median(value[channel] for value in outlines))
            for channel in range(3)
        )) if outlines else "#000000"
        glyph_ratio = median("height_ratio")
        font_size = max(12.0, glyph_ratio * height * 1.35)
        stroke_width = max(1.0, glyph_ratio * height * 0.045)
        # Smooth small per-frame detection jitter, then retain a compact
        # 5-sample/second trajectory for normalized-time interpolation.
        smoothed: list[dict[str, Any]] = []
        for item in captions:
            neighborhood = [
                sample for sample in captions
                if abs(sample["timestamp"] - item["timestamp"]) <= 0.10
            ] or [item]
            point = dict(item)
            for field in ("x_ratio", "y_ratio", "height_ratio"):
                point[field] = float(statistics.median(sample[field] for sample in neighborhood))
            smoothed.append(point)
        baseline_height = max(0.001, float(statistics.median(item["height_ratio"] for item in smoothed)))
        sample_step = max(1, int(round((fps or 30.0) / 5.0)))
        trajectory_points = smoothed[::sample_step]
        if smoothed and (not trajectory_points or trajectory_points[-1] is not smoothed[-1]):
            trajectory_points.append(smoothed[-1])
        motion_trajectory = [
            {
                "time_ratio": round(min(1.0, max(0.0, item["timestamp"] / duration)) if duration else 0.0, 6),
                "x_ratio": round(item["x_ratio"], 6),
                "y_ratio": round(item["y_ratio"], 6),
                "font_scale": round(min(1.25, max(0.80, item["height_ratio"] / baseline_height)), 4),
            }
            for item in trajectory_points
        ]
        return SubtitleStyle(
            reference_width=width,
            reference_height=height,
            font_family_estimate="bold sans-serif (Arial Bold used as a visual match)",
            font_size_reference_px=round(font_size, 2),
            font_size_reference_video_height_ratio=round(font_size / height, 5),
            color=color,
            stroke_color=outline_color if outline_color != "#FFFFFF" else "#000000",
            stroke_width_reference_px=round(stroke_width, 2),
            stroke_width_font_ratio=round(stroke_width / max(font_size, 1), 4),
            shadow_color="#000000",
            shadow_width_reference_px=1.0,
            caption_box_x_ratio=round(median("left_ratio"), 5),
            caption_box_y_ratio=round(median("top_ratio"), 5),
            caption_box_width_ratio=round(median("width_ratio"), 5),
            caption_box_height_ratio=round(glyph_ratio, 5),
            center_x_ratio=round(min(0.98, max(0.02, median("x_ratio"))), 5),
            center_y_ratio=round(min(0.95, max(0.05, median("y_ratio"))), 5),
            pop_scale=1.16,
            uppercase_scale=1.12,
            sampled_text_observations=len(captions),
            reference_frames_scanned=total_frames,
            reference_duration_seconds=round(duration, 3),
            motion_trajectory=motion_trajectory,
            analysis_notes=notes,
        )

    notes.append("No stable centered caption track was detected; using a static centered position and default typography.")
    return SubtitleStyle(
        reference_width=width,
        reference_height=height,
        font_family_estimate="bold sans-serif (Arial Bold used as a visual match)",
        font_size_reference_px=48.0,
        font_size_reference_video_height_ratio=0.0375,
        color="#FFFFFF",
        stroke_color="#000000",
        stroke_width_reference_px=2.0,
        stroke_width_font_ratio=0.0417,
        shadow_color="#000000",
        shadow_width_reference_px=1.0,
        caption_box_x_ratio=0.25,
        caption_box_y_ratio=0.32,
        caption_box_width_ratio=0.5,
        caption_box_height_ratio=0.0375,
        center_x_ratio=0.5,
        center_y_ratio=0.34,
        pop_scale=1.16,
        uppercase_scale=1.12,
        sampled_text_observations=0,
        reference_frames_scanned=total_frames,
        reference_duration_seconds=round(duration, 3),
        motion_trajectory=[
            {"time_ratio": 0.0, "x_ratio": 0.5, "y_ratio": 0.5, "font_scale": 1.0},
            {"time_ratio": 1.0, "x_ratio": 0.5, "y_ratio": 0.5, "font_scale": 1.0},
        ],
        analysis_notes=notes,
    )


def analyze_reference_style(
    reference_path: Path,
    sample_fps: float = 4.0,
    max_samples: int = 320,
    tesseract_cmd: Optional[str] = None,
) -> SubtitleStyle:
    """Analyze every reference frame with OpenCV to estimate style and motion."""
    # Keep legacy arguments accepted for callers, but frame-by-frame OpenCV
    # analysis is now the single path used for both the look and motion track.
    return _analyze_reference_opencv(reference_path, sample_fps, max_samples)


@contextlib.contextmanager
def _whisper_ffmpeg_on_path(ffmpeg_path: str) -> Iterator[None]:
    """Make imageio's bundled FFmpeg discoverable to Whisper's subprocess."""
    ffmpeg = Path(ffmpeg_path).resolve()
    with tempfile.TemporaryDirectory(prefix="subtitle_ffmpeg_") as temp_dir:
        alias = Path(temp_dir) / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        try:
            if os.name == "nt":
                shutil.copy2(ffmpeg, alias)
            else:
                alias.symlink_to(ffmpeg)
        except OSError:
            # If alias creation fails, preserve the user's PATH and let Whisper
            # use a system ffmpeg if available.
            yield
            return
        previous = os.environ.get("PATH", "")
        os.environ["PATH"] = temp_dir + os.pathsep + previous
        try:
            yield
        finally:
            os.environ["PATH"] = previous


def _get_ffmpeg() -> str:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError("FFmpeg was not found. Install FFmpeg or imageio-ffmpeg.") from exc


def _extract_audio(ffmpeg: str, video: Path, audio: Path) -> None:
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError(f"FFmpeg audio extraction failed for {video}: {details}") from exc
    if not audio.is_file() or audio.stat().st_size == 0:
        raise RuntimeError(f"FFmpeg did not produce a usable audio file for {video}")


def _transcribe_words(audio_path: Path, model_name: str, device: Optional[str], ffmpeg: str) -> list[dict[str, Any]]:
    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError("OpenAI Whisper is not installed. Install openai-whisper from requirements.txt.") from exc

    try:
        with _whisper_ffmpeg_on_path(ffmpeg):
            model = whisper.load_model(model_name, device=device) if device else whisper.load_model(model_name)
            result = model.transcribe(
                str(audio_path),
                word_timestamps=True,
                verbose=False,
            )
    except Exception as exc:
        raise RuntimeError(
            f"Whisper transcription failed with model {model_name!r}. "
            "Check the PyTorch/Whisper installation and selected --device."
        ) from exc

    words: list[dict[str, Any]] = []
    for segment in result.get("segments", []):
        segment_words = segment.get("words") or []
        if segment_words:
            for word in segment_words:
                text = str(word.get("word", "")).strip()
                if text:
                    words.append({
                        "start": float(word.get("start", segment.get("start", 0.0))),
                        "end": float(word.get("end", segment.get("end", 0.0))),
                        "text": text,
                    })
        else:
            # Whisper's word alignment can be absent for some languages or
            # tokenization cases. Keep output usable and report the estimate.
            tokens = str(segment.get("text", "")).split()
            if not tokens:
                continue
            start, end = float(segment.get("start", 0)), float(segment.get("end", 0))
            interval = max(0.04, (end - start) / len(tokens))
            for index, token in enumerate(tokens):
                words.append({
                    "start": start + index * interval,
                    "end": min(end, start + (index + 1) * interval),
                    "text": token,
                })
    if not words:
        raise RuntimeError("Whisper returned no timed words for the target audio.")
    return words


def _srt_time(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def _write_word_srt(words: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as srt:
        for index, word in enumerate(words, 1):
            start, end = float(word["start"]), float(word["end"])
            if end <= start:
                end = start + 0.04
            srt.write(f"{index}\n{_srt_time(start)} --> {_srt_time(end)}\n{word['text']}\n\n")


def _find_font(font_choice: Optional[str]) -> str:
    candidates = []
    if font_choice:
        chosen = Path(font_choice).expanduser()
        if chosen.is_file():
            return str(chosen.resolve())
        candidates.append(font_choice)

    candidates.extend([
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ])
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_file():
            return str(path.resolve())
        if shutil.which("fc-match"):
            result = subprocess.run(
                ["fc-match", "-f", "%{file}", candidate],
                check=False,
                capture_output=True,
                text=True,
            )
            match = result.stdout.strip()
            if match and Path(match).is_file():
                return match
    raise RuntimeError(
        "No usable font file was found. Install a bold sans-serif font or provide --font with a font path/family."
    )


def _moviepy_text_clip(
    TextClip: Any,
    text: str,
    font: str,
    font_size: int,
    color: str,
    stroke_color: str,
    stroke_width: int,
    duration: float,
    method: str = "label",
    box_size: Optional[tuple[int, int]] = None,
) -> Any:
    parameters = inspect.signature(TextClip).parameters
    if "text" in parameters:
        kwargs: dict[str, Any] = {
            "text": text,
            "font": font,
            "font_size": font_size,
            "color": color,
            "stroke_color": stroke_color,
            "stroke_width": stroke_width,
            "method": method,
            "text_align": "center",
            "horizontal_align": "center",
            "vertical_align": "center",
        }
    else:
        kwargs = {
            "txt": text,
            "font": font,
            "fontsize": font_size,
            "color": color,
            "stroke_color": stroke_color,
            "stroke_width": stroke_width,
            "method": method,
            "align": "center",
        }
    if box_size is not None:
        kwargs["size"] = box_size
    if "duration" in parameters:
        kwargs["duration"] = duration
    clip = TextClip(**kwargs)
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    return clip.set_duration(duration)


def _chain_method(clip: Any, modern: str, legacy: str, *args: Any) -> Any:
    method = getattr(clip, modern, None) or getattr(clip, legacy)
    return method(*args)


def _group_words_into_chunks(
    words: list[dict[str, Any]],
    *,
    max_words: int = 3,
    min_duration: float = 0.4,
    video_duration: Optional[float] = None,
    max_pause: float = 0.55,
) -> list[dict[str, Any]]:
    """Combine timed Whisper tokens into readable, non-overlapping phrases."""
    ordered = sorted(words, key=lambda item: (float(item["start"]), float(item["end"])))
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for word in ordered:
        text = str(word.get("text", "")).strip()
        if not text:
            continue
        if current:
            previous = current[-1]
            gap = float(word["start"]) - float(previous["end"])
            previous_text = str(previous.get("text", "")).strip()
            ends_sentence = bool(re.search(r"[.!?…][\"'’)]*$", previous_text))
            if len(current) >= max_words or gap > max_pause or ends_sentence:
                groups.append(current)
                current = []
        current.append(word)
    if current:
        groups.append(current)

    chunks: list[dict[str, Any]] = []
    cursor = 0.0
    for group_index, group in enumerate(groups):
        nominal_start = max(0.0, min(float(item["start"]) for item in group))
        nominal_end = max(float(item["end"]) for item in group)
        start = max(nominal_start, cursor)
        end = max(nominal_end, start + min_duration)
        if video_duration is not None:
            if group_index == 0 and nominal_start > video_duration:
                start = max(0.0, video_duration - min_duration)
            if start >= video_duration:
                start = max(0.0, video_duration - min_duration)
            end = min(end, video_duration)
            # Keep a final short phrase visible for at least the requested
            # duration whenever the video has enough remaining time.
            if (
                group_index == len(groups) - 1
                and end - start < min_duration
                and video_duration >= min_duration
            ):
                start = max(cursor, video_duration - min_duration)
                if video_duration - start < min_duration:
                    start = max(0.0, video_duration - min_duration)
                end = video_duration
        if end <= start:
            continue
        chunks.append({
            "start": start,
            "end": end,
            "text": " ".join(str(item.get("text", "")).strip() for item in group).strip(),
            "word_count": len(group),
            "words": [dict(item) for item in group],
        })
        cursor = end
    return chunks


def _smoothstep(progress: float) -> float:
    value = max(0.0, min(1.0, progress))
    return value * value * (3.0 - 2.0 * value)


def _pop_envelope(local_time: float, duration: float) -> float:
    """Return a 0..1 pulse that follows the subtitle's pop-in/settle timing."""
    if duration <= 0:
        return 0.0
    progress = max(0.0, min(1.0, float(local_time) / duration))
    rise_fraction, return_fraction = 0.15, 0.15
    if progress < rise_fraction:
        return _smoothstep(progress / rise_fraction)
    return_start = 1.0 - return_fraction
    if progress > return_start:
        return 1.0 - _smoothstep((progress - return_start) / return_fraction)
    return 1.0


def _pop_curve(local_time: float, duration: float, peak: float = 1.15) -> float:
    """Ease from 0.85x to peak, hold, then ease back to 1.0x."""
    if duration <= 0:
        return 1.0
    progress = max(0.0, min(1.0, float(local_time) / duration))
    rise_fraction, return_fraction = 0.15, 0.15
    if progress < rise_fraction:
        return 0.85 + (peak - 0.85) * _smoothstep(progress / rise_fraction)
    return_start = 1.0 - return_fraction
    if progress > return_start:
        return peak + (1.0 - peak) * _smoothstep((progress - return_start) / return_fraction)
    return peak


def _video_with_synchronized_zoom(video: Any, chunks: list[dict[str, Any]], zoom_max: float) -> Any:
    """Apply centered background punches whose envelopes match each subtitle pop."""
    if zoom_max <= 1.0 or not chunks:
        return video

    import cv2
    import numpy as np

    width, height = int(video.w), int(video.h)

    def zoom_frame(get_frame: Any, time_seconds: float) -> Any:
        frame = get_frame(time_seconds)
        envelope = 0.0
        for chunk in chunks:
            start, end = float(chunk["start"]), float(chunk["end"])
            if start <= time_seconds <= end:
                envelope = max(envelope, _pop_envelope(time_seconds - start, end - start))
        scale = 1.0 + (zoom_max - 1.0) * envelope
        if scale <= 1.00001:
            return frame

        scaled_width = max(width, int(math.ceil(width * scale)))
        scaled_height = max(height, int(math.ceil(height * scale)))
        resized = cv2.resize(frame, (scaled_width, scaled_height), interpolation=cv2.INTER_LINEAR)
        x0 = (scaled_width - width) // 2
        y0 = (scaled_height - height) // 2
        cropped = resized[y0:y0 + height, x0:x0 + width]
        if cropped.shape[:2] != (height, width):
            # Guard against a one-pixel rounding discrepancy from unusual frame sizes.
            padded = np.zeros((height, width, *frame.shape[2:]), dtype=frame.dtype)
            copy_height = min(height, cropped.shape[0])
            copy_width = min(width, cropped.shape[1])
            padded[:copy_height, :copy_width] = cropped[:copy_height, :copy_width]
            return padded
        return cropped

    transform = getattr(video, "transform", None)
    if transform is None:
        raise RuntimeError("This MoviePy version does not support per-frame video transforms.")
    return transform(zoom_frame, apply_to=[])


def _trajectory_at(style: SubtitleStyle, time_seconds: float, target_duration: float) -> dict[str, float]:
    """Interpolate reference position and font height at normalized target time."""
    trajectory = style.motion_trajectory
    if not trajectory:
        return {
            "x_ratio": style.center_x_ratio,
            "y_ratio": style.center_y_ratio,
            "font_scale": 1.0,
        }
    time_ratio = max(0.0, min(1.0, time_seconds / target_duration)) if target_duration > 0 else 0.0
    times = [float(point["time_ratio"]) for point in trajectory]
    upper = bisect.bisect_right(times, time_ratio)
    if upper <= 0:
        left = right = trajectory[0]
        fraction = 0.0
    elif upper >= len(trajectory):
        left = right = trajectory[-1]
        fraction = 0.0
    else:
        left, right = trajectory[upper - 1], trajectory[upper]
        span = float(right["time_ratio"]) - float(left["time_ratio"])
        fraction = (time_ratio - float(left["time_ratio"])) / span if span > 1e-9 else 0.0
    defaults = {
        "x_ratio": style.center_x_ratio,
        "y_ratio": style.center_y_ratio,
        "font_scale": 1.0,
    }
    values: dict[str, float] = {}
    for key, default in defaults.items():
        left_value = float(left.get(key, default))
        right_value = float(right.get(key, left_value))
        values[key] = left_value + (right_value - left_value) * fraction
    return values


def render_subtitled_video(
    target_path: Path,
    output_path: Path,
    style: SubtitleStyle,
    words: list[dict[str, Any]],
    font: str,
    font_size_override: Optional[int] = None,
    color_override: Optional[str] = None,
    active_color_override: Optional[str] = "#FFFF00",
    stroke_width_override: Optional[int] = None,
    caption_y_ratio: Optional[float] = None,
    background_zoom_max: float = 1.04,
    active_underline: bool = True,
    caption_width_ratio: float = 0.88,
) -> None:
    try:
        from moviepy import ColorClip, CompositeVideoClip, TextClip, VideoFileClip
    except ImportError:
        try:
            from moviepy.editor import ColorClip, CompositeVideoClip, TextClip, VideoFileClip
        except ImportError as exc:
            raise RuntimeError("MoviePy is not installed. Install the moviepy package from requirements.txt.") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    video = VideoFileClip(str(target_path))
    overlays: list[Any] = []
    composite = None
    try:
        output_font_size = int(font_size_override or round(
            style.font_size_reference_video_height_ratio * video.h
        ))
        output_font_size = max(12, output_font_size)
        stroke_width = int(stroke_width_override) if stroke_width_override is not None else max(
            1, round(output_font_size * style.stroke_width_font_ratio)
        )
        color = color_override or style.color
        active_color = active_color_override or "#FFFF00"
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", active_color):
            raise ValueError(f"Active word color must be a #RRGGBB value, got {active_color!r}.")
        active_rgb = tuple(int(active_color[index:index + 2], 16) for index in (1, 3, 5))
        if not 0.55 <= caption_width_ratio <= 0.95:
            raise ValueError("Caption width ratio must be between 0.55 and 0.95.")
        chunks = _group_words_into_chunks(
            words,
            max_words=3,
            min_duration=0.4,
            video_duration=float(video.duration),
        )
        if any(int(chunk["word_count"]) > 3 for chunk in chunks):
            raise RuntimeError("Subtitle chunking exceeded the three-word maximum.")
        if any(float(chunk["end"]) - float(chunk["start"]) < 0.4 - 1e-6 for chunk in chunks):
            raise RuntimeError("Subtitle chunking produced a block shorter than 0.4 seconds.")
        word_events = [word for chunk in chunks for word in chunk.get("words", [])]
        zoomed_video = _video_with_synchronized_zoom(video, word_events or chunks, background_zoom_max)
        if background_zoom_max > 1.0:
            print(
                f"Applying subtitle-synchronized background zoom from 1.00x to "
                f"{background_zoom_max:.2f}x, synchronized to spoken-word pops."
            )
        print(
            f"Rendering active word highlight in {active_color}"
            f"{' with underline' if active_underline else ''}; "
            f"MoviePy caption box width {caption_width_ratio:.0%} of the frame."
        )

        max_font_scale = max(
            (float(point.get("font_scale", 1.0)) for point in style.motion_trajectory),
            default=1.0,
        )
        max_font_scale = max(1.0, min(1.5, max_font_scale))
        caption_box_width = max(1, round(video.w * caption_width_ratio))
        for chunk in chunks:
            start = max(0.0, float(chunk["start"]))
            end = min(float(video.duration), float(chunk["end"]))
            text = str(chunk["text"]).strip()
            if not text or end - start < 0.025:
                continue
            duration = end - start
            chunk_words = chunk.get("words") or [{
                "text": token,
                "start": start + duration * index / max(1, len(text.split())),
                "end": start + duration * (index + 1) / max(1, len(text.split())),
            } for index, token in enumerate(text.split())]
            max_word_scale = 1.15 * max_font_scale
            # Measure the complete phrase first, then shrink only as much as
            # necessary to keep the caption on one naturally centered line.
            phrase_measure = _moviepy_text_clip(
                TextClip,
                text,
                font,
                output_font_size,
                color,
                style.stroke_color,
                stroke_width,
                duration,
            )
            phrase_width = float(phrase_measure.w)
            phrase_measure.close()
            safe_text_width = caption_box_width * 0.94
            reduction = min(1.0, safe_text_width / max(1.0, phrase_width * max_word_scale))
            effective_font_size = max(12, int(math.floor(output_font_size * reduction)))
            effective_stroke_width = max(1, round(stroke_width * effective_font_size / output_font_size))
            phrase_measure = _moviepy_text_clip(
                TextClip,
                text,
                font,
                effective_font_size,
                color,
                style.stroke_color,
                effective_stroke_width,
                duration,
            )
            phrase_width = float(phrase_measure.w)
            phrase_measure.close()
            while phrase_width * max_word_scale > safe_text_width and effective_font_size > 12:
                effective_font_size -= 1
                effective_stroke_width = max(1, round(stroke_width * effective_font_size / output_font_size))
                phrase_measure = _moviepy_text_clip(
                    TextClip,
                    text,
                    font,
                    effective_font_size,
                    color,
                    style.stroke_color,
                    effective_stroke_width,
                    duration,
                )
                phrase_width = float(phrase_measure.w)
                phrase_measure.close()
            caption_box_height = max(
                effective_font_size * 2 + 2 * effective_stroke_width,
                round(video.h * 0.09),
            )
            # `caption` gives us a fixed, padded text box with MoviePy's
            # wrapping behavior; fitting the measured phrase keeps 2–3 word
            # chunks on one line while retaining the safety margins.
            phrase_clip = _moviepy_text_clip(
                TextClip,
                text,
                font,
                effective_font_size,
                color,
                style.stroke_color,
                effective_stroke_width,
                duration,
                method="caption",
                box_size=(caption_box_width, caption_box_height),
            )
            word_specs: list[dict[str, Any]] = []
            for word in chunk_words:
                token = str(word.get("text", "")).strip()
                if not token:
                    continue
                word_start = max(start, min(end, float(word.get("start", start))))
                word_end = max(word_start + 0.04, min(end, float(word.get("end", end))))
                word_end = min(end, word_end)
                word_duration = max(0.04, word_end - word_start)
                token_size = effective_font_size
                measure_clip = _moviepy_text_clip(
                    TextClip,
                    token,
                    font,
                    token_size,
                    color,
                    style.stroke_color,
                    effective_stroke_width,
                    duration,
                )
                word_specs.append({
                    "text": token,
                    "start": word_start,
                    "end": word_end,
                    "duration": word_duration,
                    "size": token_size,
                    "base_width": float(measure_clip.w),
                    "base_height": float(measure_clip.h),
                })
                measure_clip.close()
            if not word_specs:
                phrase_clip.close()
                continue

            from PIL import ImageFont
            advance_font = ImageFont.truetype(font, effective_font_size)
            phrase_advance = float(advance_font.getlength(text))
            prefix_advances: list[float] = []
            cursor_advance = 0.0
            for index, spec in enumerate(word_specs):
                if index:
                    cursor_advance += float(advance_font.getlength(" "))
                prefix_advances.append(cursor_advance)
                cursor_advance += float(advance_font.getlength(spec["text"]))

            def phrase_scale(
                absolute_time: float,
                timed_words: list[dict[str, Any]] = word_specs,
            ) -> float:
                motion = _trajectory_at(style, absolute_time, float(video.duration))
                active_pops = [
                    _pop_curve(absolute_time - float(word["start"]), float(word["duration"]), 1.15)
                    for word in timed_words
                    if float(word["start"]) <= absolute_time <= float(word["end"])
                ]
                return motion["font_scale"] * (max(active_pops) if active_pops else 1.0)

            def phrase_position(
                t: float,
                clip_width: float = phrase_clip.w,
                clip_height: float = phrase_clip.h,
                chunk_start: float = start,
                phrase_width_px: float = phrase_width,
                scale_function: Any = phrase_scale,
            ) -> tuple[float, float]:
                absolute_time = chunk_start + t
                motion = _trajectory_at(style, absolute_time, float(video.duration))
                scale = scale_function(absolute_time)
                content_width = phrase_width_px * scale
                edge_margin = video.w * 0.035
                center_x = min(
                    video.w - content_width / 2 - edge_margin,
                    max(content_width / 2 + edge_margin, motion["x_ratio"] * video.w),
                )
                y_ratio = caption_y_ratio if caption_y_ratio is not None else motion["y_ratio"]
                center_y = min(video.h - clip_height * scale / 2, max(clip_height * scale / 2, y_ratio * video.h))
                return center_x - clip_width * scale / 2, center_y - clip_height * scale / 2

            phrase_clip = _chain_method(phrase_clip, "resized", "resize", phrase_scale)
            phrase_clip = _chain_method(phrase_clip, "with_position", "set_position", phrase_position)
            phrase_clip = _chain_method(phrase_clip, "with_start", "set_start", start)
            overlays.append(phrase_clip)

            def word_center_x(
                absolute_time: float,
                word_index: int,
                advances: list[float] = prefix_advances,
                full_advance: float = phrase_advance,
                tokens: list[dict[str, Any]] = word_specs,
                font_metrics: Any = advance_font,
                phrase_width_px: float = phrase_width,
                scale_function: Any = phrase_scale,
            ) -> float:
                motion = _trajectory_at(style, absolute_time, float(video.duration))
                scale = scale_function(absolute_time)
                layout_width = phrase_width_px * scale
                preferred_center = min(0.98, max(0.02, motion["x_ratio"])) * video.w
                edge_margin = video.w * 0.035
                min_center = layout_width / 2 + edge_margin
                max_center = video.w - layout_width / 2 - edge_margin
                phrase_center = min(max_center, max(min_center, preferred_center))
                token_advance = float(font_metrics.getlength(tokens[word_index]["text"]))
                word_offset = advances[word_index] + token_advance / 2 - full_advance / 2
                return phrase_center + word_offset * scale

            for word_index, spec in enumerate(word_specs):
                word_start, word_end = spec["start"], spec["end"]
                word_duration = spec["duration"]
                active_width = spec["base_width"]
                active_height = spec["base_height"]

                def active_scale(
                    t: float,
                    ws: float = word_start,
                    d: float = word_duration,
                    size_ratio: float = spec["size"] / effective_font_size,
                    chunk_scale: Any = phrase_scale,
                ) -> float:
                    absolute_time = ws + t
                    return chunk_scale(absolute_time) * size_ratio

                if active_underline:
                    line_height = max(2, round(spec["size"] * 0.055))
                    underline = ColorClip(
                        size=(max(1, round(active_width)), line_height),
                        color=active_rgb,
                        duration=word_duration,
                    )
                    underline = _chain_method(underline, "resized", "resize", active_scale)

                    def underline_position(
                        t: float,
                        bw: float = active_width,
                        bh: float = active_height,
                        index: int = word_index,
                        ws: float = word_start,
                        d: float = word_duration,
                        gap_below: float = max(2, round(spec["size"] * 0.07)),
                        lh: int = line_height,
                        center_function: Any = word_center_x,
                        scale_function: Any = active_scale,
                    ) -> tuple[float, float]:
                        absolute_time = ws + t
                        scale = scale_function(t, ws, d)
                        motion = _trajectory_at(style, absolute_time, float(video.duration))
                        center_x = center_function(absolute_time, index)
                        y_ratio = caption_y_ratio if caption_y_ratio is not None else motion["y_ratio"]
                        center_y = min(0.97, max(0.03, y_ratio)) * video.h
                        x = center_x - bw * scale / 2
                        y = min(
                            max(0.0, center_y + bh * scale / 2 + gap_below * scale),
                            max(0.0, video.h - lh * scale),
                        )
                        return x, y

                    underline = _chain_method(underline, "with_position", "set_position", underline_position)
                    underline = _chain_method(underline, "with_start", "set_start", word_start)
                    overlays.append(underline)

        composite = CompositeVideoClip([zoomed_video, *overlays], size=video.size)
        composite = _chain_method(composite, "with_duration", "set_duration", video.duration)
        with tempfile.TemporaryDirectory(prefix="subtitle_render_", dir=str(output_path.parent)) as temp_dir:
            render_path = Path(temp_dir) / "rendered.mp4"
            temp_audio = str(Path(temp_dir) / "moviepy_audio.m4a")
            composite.write_videofile(
                str(render_path),
                fps=video.fps or 30,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=temp_audio,
                remove_temp=True,
                preset="medium",
                ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
                logger="bar",
            )
            if not render_path.is_file() or render_path.stat().st_size == 0:
                raise RuntimeError("MoviePy finished without producing a usable rendered video.")
            os.replace(render_path, output_path)
    finally:
        if composite is not None:
            composite.close()
        for overlay in overlays:
            try:
                overlay.close()
            except Exception:
                pass
        video.close()

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"MoviePy did not write a valid output file: {output_path}")


def _video_duration_seconds(path: Path) -> float:
    import cv2

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not inspect video duration: {path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    capture.release()
    if fps <= 0 or frame_count <= 0:
        raise RuntimeError(f"Could not determine video duration: {path}")
    return frame_count / fps


def run(reference_path: Path, target_path: Path, output_path: Path, args: argparse.Namespace) -> None:
    if not reference_path.is_file():
        raise FileNotFoundError(f"Reference video not found: {reference_path}")
    if not target_path.is_file():
        raise FileNotFoundError(f"Target video not found: {target_path}")
    if target_path.resolve() == output_path.resolve():
        raise ValueError("Output path must not overwrite the target video.")

    style = analyze_reference_style(
        reference_path,
        sample_fps=args.sample_fps,
        max_samples=args.max_samples,
        tesseract_cmd=args.tesseract_cmd,
    )
    font = _find_font(args.font)
    if "bodoni 72" in Path(font).name.lower():
        style.font_family_estimate = "high-contrast serif (Bodoni 72 Book used as a visual match)"
    print("\nEstimated reference subtitle style:")
    style_summary = asdict(style)
    style_summary.pop("motion_trajectory", None)
    print(json.dumps(style_summary, indent=2))
    print(f"Font file used: {font}")
    if args.caption_y_ratio is None:
        y_values = [point["y_ratio"] for point in style.motion_trajectory]
        font_scales = [point["font_scale"] for point in style.motion_trajectory]
        print(
            f"Applying {len(style.motion_trajectory)} reference motion samples over "
            f"{style.reference_duration_seconds:.2f}s using normalized target time; "
            f"Y range {min(y_values):.3f}-{max(y_values):.3f}, "
            f"font scale {min(font_scales):.2f}-{max(font_scales):.2f}."
        )
    else:
        print(f"Using requested fixed caption Y ratio: {args.caption_y_ratio:.3f}")

    ffmpeg = _get_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="subtitle_work_", dir=str(output_path.parent)) as temp_dir:
        work_dir = Path(temp_dir)
        audio_path = work_dir / "target_audio.wav"
        srt_path = work_dir / "word_timestamps.srt"
        print(f"\nExtracting target audio with: {ffmpeg}")
        _extract_audio(ffmpeg, target_path, audio_path)
        print(f"Transcribing with Whisper model: {args.model}")
        words = _transcribe_words(audio_path, args.model, args.device, ffmpeg)
        _write_word_srt(words, srt_path)
        target_duration = _video_duration_seconds(target_path)
        chunks = _group_words_into_chunks(
            words,
            max_words=3,
            min_duration=0.4,
            video_duration=target_duration,
        )
        retained_words = sum(int(chunk["word_count"]) for chunk in chunks)
        if retained_words != len([word for word in words if str(word.get("text", "")).strip()]):
            raise RuntimeError("Phrase chunking did not retain every transcribed word.")
        if any(int(chunk["word_count"]) > 3 for chunk in chunks):
            raise RuntimeError("Phrase chunking exceeded the three-word maximum.")
        if any(float(chunk["end"]) - float(chunk["start"]) < 0.4 - 1e-6 for chunk in chunks):
            raise RuntimeError("Phrase chunking produced a subtitle shorter than 0.4 seconds.")
        if any(
            float(current["start"]) < float(previous["end"]) - 1e-6
            for previous, current in zip(chunks, chunks[1:])
        ):
            raise RuntimeError("Phrase chunking produced overlapping subtitle blocks.")
        words = sorted(words, key=lambda word: (float(word["start"]), float(word["end"])))
        first_word_start = float(words[0]["start"])
        last_word_end = float(words[-1]["end"])
        max_word_gap = max((
            max(0.0, float(next_word["start"]) - float(word["end"]))
            for word, next_word in zip(words, words[1:])
        ), default=0.0)
        print(
            f"Transcribed {len(words)} timed words across {target_duration:.2f}s "
            f"(first {first_word_start:.2f}s, last {last_word_end:.2f}s; "
            f"largest inter-word gap {max_word_gap:.2f}s); "
            f"rendering {len(chunks)} phrase chunks (max 3 words, min 0.40s) "
            f"with {retained_words}/{len(words)} words retained."
        )
        render_subtitled_video(
            target_path,
            output_path,
            style,
            words,
            font,
            font_size_override=args.font_size,
            color_override=args.color,
            active_color_override=args.active_color,
            stroke_width_override=args.stroke_width,
            caption_y_ratio=args.caption_y_ratio,
            background_zoom_max=args.background_zoom_max,
            active_underline=not args.no_active_underline,
            caption_width_ratio=args.caption_width_ratio,
        )
    print(f"Saved styled subtitled video: {output_path} ({output_path.stat().st_size:,} bytes)")
    print("Temporary audio, SRT, FFmpeg alias, and render audio files were removed.")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reference", type=Path, help="Reference video; otherwise discover a unique reference*.mp4 under --data-dir.")
    parser.add_argument("--target", type=Path, help="Target video; otherwise discover a unique target*.mp4 under --data-dir.")
    parser.add_argument("--output", type=Path, help="Output video path (default: <target>_styled_subtitled.mp4).")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Directory for automatic reference/target discovery.")
    parser.add_argument("--model", default="base", help="Whisper model name (default: base; use tiny for lower resource use).")
    parser.add_argument("--device", default=None, help="Whisper device, e.g. cpu or cuda. Defaults to Whisper's automatic choice.")
    parser.add_argument("--font", help="Font file path or font family name. Defaults to a bold sans-serif match.")
    parser.add_argument("--font-size", type=int, help="Override the estimated output font size in pixels.")
    parser.add_argument("--color", help="Override estimated text color, e.g. #FFFFFF or #FFFF00.")
    parser.add_argument("--active-color", default="#FFFF00", help="Accent color for the currently spoken word (default: bright yellow).")
    parser.add_argument("--no-active-underline", action="store_true", help="Disable the underline on the active spoken word.")
    parser.add_argument(
        "--caption-width-ratio",
        type=float,
        default=0.88,
        help="Fixed MoviePy caption box width as a fraction of frame width (default: 0.88).",
    )
    parser.add_argument("--stroke-width", type=int, help="Override estimated text outline width in pixels.")
    parser.add_argument("--caption-y-ratio", type=float, help="Optional fixed normalized Y override; otherwise map the reference Y trajectory dynamically.")
    parser.add_argument(
        "--background-zoom-max",
        type=float,
        default=1.04,
        help="Maximum background scale synchronized to each subtitle pop (default: 1.04x).",
    )
    parser.add_argument("--sample-fps", type=float, default=4.0, help="Legacy compatibility option; OpenCV analyzes every frame regardless.")
    parser.add_argument("--max-samples", type=int, default=320, help="Legacy compatibility option; OpenCV analyzes every frame regardless.")
    parser.add_argument("--tesseract-cmd", help="Legacy compatibility option; style analysis uses OpenCV pixels.")
    args = parser.parse_args(argv)
    return args


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    try:
        reference = args.reference or _discover_video(args.data_dir, "reference")
        target = args.target or _discover_video(args.data_dir, "target")
        output = args.output or target.with_name(f"{target.stem}_styled_subtitled{target.suffix}")
        run(reference, target, output, args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if os.environ.get("STYLECUT_SUBTITLE_TRACEBACK") == "1":
            import traceback
            traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
