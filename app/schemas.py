from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================================
# VIDEO METADATA
# ============================================================

class VideoMetadata(BaseModel):
    duration_seconds: float
    width: int
    height: int
    fps: float
    frame_count: int

    codec: Optional[str] = None
    pixel_format: Optional[str] = None


# ============================================================
# REPRESENTATIVE FRAME
# ============================================================

class RepresentativeFrame(BaseModel):
    timestamp: float
    path: str


# ============================================================
# REFERENCE SEGMENT
# ============================================================

class ReferenceSegment(BaseModel):

    segment_id: str

    start_time: float
    end_time: float
    duration: float

    shot_type: str
    camera_motion: str
    subject_motion: str

    editing_characteristics: List[str] = Field(
        default_factory=list
    )

    transitions: List[str] = Field(
        default_factory=list
    )

    description: str

    motion_score: Optional[float] = None


# ============================================================
# SUBTITLE TICK SOUND ANALYSIS
# ============================================================

class SubtitleTickSoundAnalysis(BaseModel):
    detected: bool = Field(
        default=True,
        description="Whether a tick/click sound is produced on subtitle font changes in the reference video"
    )
    sound_type: str = Field(
        default="mechanical_tick",
        description="Type of tick sound, e.g. mechanical_tick, typewriter_click, pop, click"
    )
    frequency_hz: float = Field(
        default=2200.0,
        description="Dominant pitch/frequency of the tick sound in Hz"
    )
    duration_ms: float = Field(
        default=35.0,
        description="Duration of the tick sound in milliseconds"
    )
    volume: float = Field(
        default=0.65,
        description="Relative volume of the tick sound from 0.0 to 1.0"
    )
    font_change_triggers: List[str] = Field(
        default_factory=lambda: [
            "font_family_change",
            "font_size_emphasis",
            "word_transition",
            "style_pop"
        ],
        description="Events that trigger the tick sound"
    )
    timestamps: List[float] = Field(
        default_factory=list,
        description="Observed timestamps of subtitle font changes with tick sounds in reference video"
    )
    extracted_sample_path: Optional[str] = Field(
        default=None,
        description="Path to extracted reference tick sample WAV file if available"
    )


# ============================================================
# REFERENCE ANALYSIS
# ============================================================

class ReferenceAnalysis(BaseModel):

    video_path: str

    metadata: VideoMetadata

    total_segments: int

    segments: List[ReferenceSegment]

    subtitle_tick_sound: Optional[SubtitleTickSoundAnalysis] = None


# ============================================================
# TARGET SEGMENT
# ============================================================

class TargetSegment(BaseModel):

    segment_id: str

    start_time: float
    end_time: float
    duration: float

    shot_type: str
    camera_motion: str
    subject_motion: str

    description: str

    motion_score: Optional[float] = None


# ============================================================
# TARGET ANALYSIS
# ============================================================

class TargetAnalysis(BaseModel):

    video_path: str

    metadata: VideoMetadata

    total_segments: int

    segments: List[TargetSegment]


# ============================================================
# EDIT OPERATION
# ============================================================

class EditOperation(BaseModel):

    operation: str

    parameters: dict = Field(
        default_factory=dict
    )


# ============================================================
# EDIT SPEC SEGMENT
# ============================================================

class EditSegment(BaseModel):

    output_segment_id: str

    source_segment_id: str

    source_start: float
    source_end: float

    target_start: float
    target_end: float

    operations: List[EditOperation] = Field(
        default_factory=list
    )

    rationale: Optional[str] = None


# ============================================================
# EDIT SPEC
# ============================================================

class EditSpec(BaseModel):

    version: str = "1.0"

    source_video: str

    reference_video: str

    output_video: str

    reference_style_summary: str

    segments: List[EditSegment]

    global_operations: List[EditOperation] = Field(
        default_factory=list
    )

    subtitle_tick_sound: Optional[SubtitleTickSoundAnalysis] = None