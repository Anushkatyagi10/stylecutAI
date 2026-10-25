#!/usr/bin/env python3
"""Estimate subtitle styling from a reference video and apply it to a target.

The analysis is necessarily visual: once text is flattened into video frames,
the original font metadata and animation keyframes are gone. This script uses
Tesseract OCR and sampled pixels to estimate the visible style, then renders
word-level Whisper timestamps as animated MoviePy text clips.

Requirements:
    pip install -r requirements.txt
    Install the Tesseract OCR executable separately and make it available on
    PATH (or pass --tesseract-cmd).

Example:
    python style_transfer_subtitles.py \
        --reference "data/reference.mp4" --target "data/target.mp4"
"""

from __future__ import annotations

import argparse
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
    center_x_ratio: float
    center_y_ratio: float
    pop_scale: float
    uppercase_scale: float
    sampled_text_observations: int
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


def analyze_reference_style(
    reference_path: Path,
    sample_fps: float = 4.0,
    max_samples: int = 320,
    tesseract_cmd: Optional[str] = None,
) -> SubtitleStyle:
    """Estimate typography, color and placement from OCR boxes in the reference."""
    try:
        import cv2
        import pytesseract
        from pytesseract import Output
    except ImportError as exc:
        raise RuntimeError(
            "Reference analysis needs opencv-python and pytesseract. Install "
            "requirements.txt, and install the Tesseract executable separately."
        ) from exc

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

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
    if total_frames <= 0:
        total_frames = max(1, int(capture.get(cv2.CAP_PROP_POS_FRAMES)))
    requested_stride = max(1, int(round(fps / max(sample_fps, 0.1)))) if fps else 1
    stride = max(requested_stride, int(math.ceil(total_frames / max(1, max_samples))))

    detections: list[dict[str, Any]] = []
    for frame_number in range(0, total_frames, stride):
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ok, frame = capture.read()
        if not ok:
            continue
        timestamp = frame_number / fps if fps else 0.0
        try:
            data = pytesseract.image_to_data(
                frame,
                output_type=Output.DICT,
                config="--psm 11",
            )
        except Exception as exc:
            capture.release()
            raise RuntimeError(
                "Tesseract OCR failed. Confirm that the Tesseract executable is installed "
                "and set --tesseract-cmd if it is not on PATH."
            ) from exc
        for index, raw_text in enumerate(data.get("text", [])):
            text = str(raw_text).strip()
            try:
                confidence = float(data["conf"][index])
                x, y = int(data["left"][index]), int(data["top"][index])
                box_width, box_height = int(data["width"][index]), int(data["height"][index])
            except (ValueError, TypeError, KeyError):
                continue
            if (
                not text
                or confidence < 30
                or box_width < 3
                or box_height < 8
                or box_height > height * 0.15
            ):
                continue
            box = (x, y, box_width, box_height)
            detections.append({
                "text": text,
                "confidence": confidence,
                "timestamp": timestamp,
                "x": x,
                "width": box_width,
                "x_ratio": (x + box_width / 2) / width,
                "y_ratio": (y + box_height / 2) / height,
                "height_ratio": box_height / height,
                "color": _sample_text_color(frame, box),
                "outline": _sample_outline_color(frame, box),
            })
    capture.release()

    notes: list[str] = []
    if detections:
        # Find the most frequently observed horizontal text band. This reduces
        # interference from one-off title cards and incidental signs.
        bins: dict[int, list[dict[str, Any]]] = {}
        for detection in detections:
            band = int(round(detection["y_ratio"] / 0.015))
            bins.setdefault(band, []).append(detection)
        selected_band = max(bins, key=lambda key: len(bins[key]))
        band_center = selected_band * 0.015
        captions = [
            item for item in detections
            if abs(item["y_ratio"] - band_center) <= 0.03
        ] or bins[selected_band]
        # Aggregate OCR word boxes into a caption-line box per sampled frame;
        # this avoids biasing the center toward the longer side of a phrase.
        line_centers = []
        for timestamp in sorted({item["timestamp"] for item in captions}):
            frame_items = [item for item in captions if item["timestamp"] == timestamp]
            line_left = min(item["x"] for item in frame_items)
            line_right = max(item["x"] + item["width"] for item in frame_items)
            line_centers.append((line_left + line_right) / (2 * width))
        center_x = float(statistics.median(line_centers or [item["x_ratio"] for item in captions]))
        center_y = float(statistics.median(item["y_ratio"] for item in captions))
        glyph_height_ratio = float(statistics.median(item["height_ratio"] for item in captions))
        color_values = [item["color"] for item in captions if item["color"]]
        outline_values = [item["outline"] for item in captions if item["outline"]]
        color = _hex_color(tuple(int(statistics.median(color[i] for color in color_values)) for i in range(3))) if color_values else "#FFFFFF"
        outline_color = _hex_color(tuple(int(statistics.median(color[i] for color in outline_values)) for i in range(3))) if outline_values else "#000000"

        # OCR sees the glyph body; a 1.35 factor approximates the font-size
        # setting that produces the measured glyph height in MoviePy.
        font_size_ref = max(12.0, glyph_height_ratio * height * 1.35)
        stroke_px_ref = max(1.0, glyph_height_ratio * height * 0.045)

        # If identical words are captured at multiple sampled moments, their
        # OCR heights give a weak visual estimate of the reference pop range.
        by_word: dict[str, list[dict[str, Any]]] = {}
        for item in captions:
            by_word.setdefault(re.sub(r"\W+", "", item["text"]).lower(), []).append(item)
        pop_estimates = []
        for items in by_word.values():
            if len(items) >= 2:
                ratios = [item["height_ratio"] for item in items]
                if min(ratios) > 0:
                    pop_estimates.append(max(ratios) / statistics.median(ratios))
        pop_scale = min(1.35, max(1.08, statistics.median(pop_estimates))) if pop_estimates else 1.16
        if not pop_estimates:
            notes.append("Pop strength was not observable across repeated OCR samples; using a subtle 1.16x pop estimate.")
        notes.append("Font family and exact keyframes cannot be recovered from flattened video pixels; typography and motion are visual estimates.")
    else:
        center_x, center_y = 0.5, 0.35
        glyph_height_ratio = 0.035
        font_size_ref = height * glyph_height_ratio * 1.35
        stroke_px_ref = max(1.0, height * glyph_height_ratio * 0.045)
        color, outline_color, pop_scale = "#FFFFFF", "#000000", 1.16
        captions = []
        notes.append("OCR found no confident captions; using a bold white, black-outlined, upper-center fallback profile.")
        notes.append("Font family and exact keyframes cannot be recovered from flattened video pixels; typography and motion are visual estimates.")

    return SubtitleStyle(
        reference_width=width,
        reference_height=height,
        font_family_estimate="bold sans-serif (font identity is not recoverable from rendered frames)",
        font_size_reference_px=round(font_size_ref, 2),
        font_size_reference_video_height_ratio=round(font_size_ref / height, 5),
        color=color,
        stroke_color=outline_color if outline_color != "#FFFFFF" else "#000000",
        stroke_width_reference_px=round(stroke_px_ref, 2),
        stroke_width_font_ratio=round(stroke_px_ref / max(font_size_ref, 1), 4),
        shadow_color="#000000",
        shadow_width_reference_px=1.0,
        center_x_ratio=round(min(0.98, max(0.02, center_x)), 5),
        center_y_ratio=round(min(0.95, max(0.05, center_y)), 5),
        pop_scale=round(pop_scale, 3),
        uppercase_scale=1.12,
        sampled_text_observations=len(captions),
        analysis_notes=notes,
    )


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
            "method": "label",
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
            "method": "label",
            "align": "center",
        }
    if "duration" in parameters:
        kwargs["duration"] = duration
    clip = TextClip(**kwargs)
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    return clip.set_duration(duration)


def _chain_method(clip: Any, modern: str, legacy: str, *args: Any) -> Any:
    method = getattr(clip, modern, None) or getattr(clip, legacy)
    return method(*args)


def _pop_curve(local_time: float, duration: float, peak: float) -> float:
    time = max(0.0, min(float(local_time), duration))
    rise = min(0.10, max(0.035, duration * 0.28))
    settle = min(0.16, max(0.05, duration * 0.45))
    if time < rise:
        return 0.82 + (peak - 0.82) * (time / rise)
    if time < rise + settle:
        progress = (time - rise) / settle
        return peak + (1.0 - peak) * progress
    return 1.0


def render_subtitled_video(
    target_path: Path,
    output_path: Path,
    style: SubtitleStyle,
    words: list[dict[str, Any]],
    font: str,
    font_size_override: Optional[int] = None,
    color_override: Optional[str] = None,
    stroke_width_override: Optional[int] = None,
    reference_path: Optional[Path] = None,
    enable_tick_sound: bool = True,
) -> None:
    try:
        from moviepy import CompositeVideoClip, TextClip, VideoFileClip
    except ImportError:
        try:
            from moviepy.editor import CompositeVideoClip, TextClip, VideoFileClip
        except ImportError as exc:
            raise RuntimeError("MoviePy is not installed. Install the moviepy package from requirements.txt.") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    video = VideoFileClip(str(target_path))
    overlays: list[Any] = []
    composite = None
    font_change_timestamps: list[float] = []
    try:
        output_font_size = int(font_size_override or round(
            style.font_size_reference_video_height_ratio * video.h
        ))
        output_font_size = max(12, output_font_size)
        stroke_width = int(stroke_width_override) if stroke_width_override is not None else max(
            1, round(output_font_size * style.stroke_width_font_ratio)
        )
        color = color_override or style.color
        center_x = style.center_x_ratio * video.w
        center_y = style.center_y_ratio * video.h

        for word in words:
            start = max(0.0, float(word["start"]))
            end = min(float(video.duration), float(word["end"]))
            text = str(word["text"]).strip()
            if not text or end - start < 0.025:
                continue
            duration = end - start
            size = output_font_size
            if text.isupper() and any(char.isalpha() for char in text):
                size = round(size * style.uppercase_scale)
            clip = _moviepy_text_clip(
                TextClip,
                text,
                font,
                size,
                color,
                style.stroke_color,
                stroke_width,
                duration,
            )
            if clip.w > video.w * 0.92:
                reduction = video.w * 0.92 / clip.w
                clip = _chain_method(clip, "resized", "resize", reduction)
            base_width, base_height = clip.w, clip.h
            peak = style.pop_scale
            curve = lambda t, d=duration, p=peak: _pop_curve(t, d, p)
            clip = _chain_method(clip, "resized", "resize", curve)
            positioned = lambda t, bw=base_width, bh=base_height, cx=center_x, cy=center_y, d=duration, p=peak: (
                cx - bw * _pop_curve(t, d, p) / 2,
                cy - bh * _pop_curve(t, d, p) / 2,
            )
            clip = _chain_method(clip, "with_position", "set_position", positioned)
            clip = _chain_method(clip, "with_start", "set_start", start)
            overlays.append(clip)

        # Collect tick timestamps strictly at full stops, not every second
        has_punct = any(re.search(r"[\.!?]", str(w.get("text", ""))) for w in words)
        last_tick_time = -10.0
        min_interval = 2.0  # Minimum seconds between ticks to avoid ticking every second

        for i, word in enumerate(words):
            start = max(0.0, float(word["start"]))
            end = min(float(video.duration), float(word["end"]))
            text = str(word.get("text", "")).strip()
            if not text or end - start < 0.025:
                continue

            is_full_stop = False
            words_in_text = text.split()
            if has_punct:
                if re.search(r"[\.!?]+$", text) or "." in text:
                    is_full_stop = True
            else:
                next_start = float(words[i + 1]["start"]) if i + 1 < len(words) else end + 1.0
                if (next_start - end >= 0.45) or (i == len(words) - 1):
                    is_full_stop = True

            if is_full_stop:
                tick_time = round(start, 3) if len(words_in_text) == 1 else round(end, 3)
                if tick_time - last_tick_time >= min_interval:
                    font_change_timestamps.append(tick_time)
                    last_tick_time = tick_time

        composite = CompositeVideoClip([video, *overlays], size=video.size)
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

            if enable_tick_sound and font_change_timestamps:
                try:
                    from app.video_utils import analyze_subtitle_tick_sound, mix_tick_sounds_into_video_audio, run_ffmpeg
                    tick_profile = None
                    if reference_path and reference_path.exists():
                        tick_profile = analyze_subtitle_tick_sound(reference_path, Path(temp_dir))
                    enhanced_audio = Path(temp_dir) / "enhanced_tick_audio.wav"
                    mix_tick_sounds_into_video_audio(
                        render_path,
                        enhanced_audio,
                        font_change_timestamps,
                        tick_profile=tick_profile,
                    )
                    mux_cmd = [
                        "ffmpeg", "-y",
                        "-i", str(render_path),
                        "-i", str(enhanced_audio),
                        "-map", "0:v:0",
                        "-map", "1:a:0",
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-movflags", "+faststart",
                        str(output_path),
                    ]
                    run_ffmpeg(mux_cmd)
                except Exception as tick_err:
                    print(f"Warning: could not mix tick sounds: {tick_err}")
                    os.replace(render_path, output_path)
            else:
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
    print("\nEstimated reference subtitle style:")
    print(json.dumps(asdict(style), indent=2))
    print(f"Font file used: {font}")

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
        print(f"Transcribed {len(words)} timed words; rendering animated captions.")
        render_subtitled_video(
            target_path,
            output_path,
            style,
            words,
            font,
            font_size_override=args.font_size,
            color_override=args.color,
            stroke_width_override=args.stroke_width,
            reference_path=reference_path,
            enable_tick_sound=not args.no_tick_sound,
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
    parser.add_argument("--stroke-width", type=int, help="Override estimated text outline width in pixels.")
    parser.add_argument("--sample-fps", type=float, default=4.0, help="Reference OCR sample rate (default: 4 frames/sec).")
    parser.add_argument("--max-samples", type=int, default=320, help="Maximum reference frames sampled for OCR.")
    parser.add_argument("--tesseract-cmd", help="Tesseract executable path if it is not on PATH.")
    parser.add_argument("--no-tick-sound", action="store_true", help="Disable adding tick sounds on subtitle font changes.")
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
