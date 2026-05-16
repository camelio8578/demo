"""
SubtitleGenerator: produce SRT and ASS subtitle files from transcript segments
and optionally burn them into the rendered video using FFmpeg.
"""
from __future__ import annotations

import subprocess
from datetime import timedelta
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)


def _seconds_to_srt_ts(seconds: float) -> str:
    """Convert float seconds to SRT timestamp: HH:MM:SS,mmm"""
    td = timedelta(seconds=max(0.0, seconds))
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _seconds_to_ass_ts(seconds: float) -> str:
    """Convert float seconds to ASS timestamp: H:MM:SS.cc"""
    seconds = max(0.0, seconds)
    total_cs = int(seconds * 100)  # centiseconds
    hours, remainder = divmod(total_cs, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, cs = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def _wrap_text(text: str, max_chars: int) -> str:
    """Wrap text at word boundaries to max_chars per line."""
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    length = 0
    for word in words:
        if length + len(word) + (1 if current else 0) > max_chars:
            if current:
                lines.append(" ".join(current))
            current = [word]
            length = len(word)
        else:
            current.append(word)
            length += len(word) + (1 if len(current) > 1 else 0)
    if current:
        lines.append(" ".join(current))
    return "\\N".join(lines)  # ASS / SRT newline


class SubtitleGenerator:
    """Generate SRT and ASS subtitle files from transcript segment dicts."""

    DEFAULT_STYLE: dict[str, Any] = {
        "font": "Arial",
        "font_size": 48,
        "color": "white",
        "stroke_color": "black",
        "stroke_width": 2,
        "position": "bottom_third",
        "animation": "word_highlight",
        "max_chars_per_line": 32,
    }

    # ASS colour format: &HAABBGGRR (alpha, blue, green, red)
    _COLOR_MAP: dict[str, str] = {
        "white": "&H00FFFFFF",
        "black": "&H00000000",
        "yellow": "&H0000FFFF",
        "red": "&H000000FF",
        "blue": "&H00FF0000",
        "green": "&H0000FF00",
    }

    def generate_srt(
        self,
        segments: list[dict],
        output_path: str,
        clip_start: float,
    ) -> str:
        """
        Generate SRT subtitle file.

        Args:
            segments: List of dicts with start_time, end_time, text keys.
            output_path: Destination .srt file path.
            clip_start: The start time of the clip in the source video (seconds).
                        All timestamps are shifted to be relative to clip_start.

        Returns:
            Absolute path to the generated SRT file.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        entries: list[str] = []
        index = 1

        for seg in segments:
            text = (seg.get("text") or "").strip()
            if not text:
                continue

            seg_start = float(seg.get("start_time", 0.0)) - clip_start
            seg_end = float(seg.get("end_time", 0.0)) - clip_start

            # Skip segments entirely outside the clip window
            if seg_end <= 0.0:
                continue
            seg_start = max(0.0, seg_start)

            # Handle overlapping times: ensure end > start
            if seg_end <= seg_start:
                seg_end = seg_start + 0.1

            ts_start = _seconds_to_srt_ts(seg_start)
            ts_end = _seconds_to_srt_ts(seg_end)

            entries.append(f"{index}\n{ts_start} --> {ts_end}\n{text}\n")
            index += 1

        srt_content = "\n".join(entries)
        out.write_text(srt_content, encoding="utf-8")
        log.info("srt_generated", path=str(out), entry_count=index - 1)
        return str(out)

    def generate_ass(
        self,
        segments: list[dict],
        output_path: str,
        clip_start: float,
        style_config: dict | None = None,
    ) -> str:
        """
        Generate ASS subtitle file with configurable style.

        Args:
            segments: List of dicts with start_time, end_time, text keys.
            output_path: Destination .ass file path.
            clip_start: Source-video start time of the clip in seconds.
            style_config: Override DEFAULT_STYLE keys.

        Returns:
            Absolute path to the generated ASS file.
        """
        style = {**self.DEFAULT_STYLE, **(style_config or {})}
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        font = style.get("font", "Arial")
        font_size = int(style.get("font_size", 48))
        color = self._COLOR_MAP.get(str(style.get("color", "white")), "&H00FFFFFF")
        stroke_color = self._COLOR_MAP.get(
            str(style.get("stroke_color", "black")), "&H00000000"
        )
        stroke_width = int(style.get("stroke_width", 2))
        max_chars = int(style.get("max_chars_per_line", 32))
        animation = style.get("animation", "word_highlight")

        # Position: bottom_third → alignment 2 (bottom-center), margin-v 60
        alignment = 2
        margin_v = 60

        # --- ASS header ---
        header = (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            "PlayResX: 1080\n"
            "PlayResY: 1920\n"
            "ScaledBorderAndShadow: yes\n"
            "\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Default,{font},{font_size},{color},&H000000FF,"
            f"{stroke_color},&H00000000,-1,0,0,0,100,100,0,0,1,"
            f"{stroke_width},0,{alignment},10,10,{margin_v},1\n"
            "\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
            "MarginV, Effect, Text\n"
        )

        dialogue_lines: list[str] = []

        for seg in segments:
            text = (seg.get("text") or "").strip()
            if not text:
                continue

            seg_start = float(seg.get("start_time", 0.0)) - clip_start
            seg_end = float(seg.get("end_time", 0.0)) - clip_start

            if seg_end <= 0.0:
                continue
            seg_start = max(0.0, seg_start)
            if seg_end <= seg_start:
                seg_end = seg_start + 0.1

            ts_start = _seconds_to_ass_ts(seg_start)
            ts_end = _seconds_to_ass_ts(seg_end)

            # Word highlight animation: fade in each word with {\k} tags
            if animation == "word_highlight":
                words = text.split()
                if len(words) > 1 and seg_end > seg_start:
                    dur_per_word_cs = int(
                        (seg_end - seg_start) / len(words) * 100
                    )
                    tagged_words = [
                        f"{{\\k{dur_per_word_cs}}}{w}" for w in words
                    ]
                    ass_text = " ".join(tagged_words)
                else:
                    ass_text = text
            else:
                ass_text = _wrap_text(text, max_chars)

            dialogue_lines.append(
                f"Dialogue: 0,{ts_start},{ts_end},Default,,0,0,0,,{ass_text}"
            )

        ass_content = header + "\n".join(dialogue_lines) + "\n"
        out.write_text(ass_content, encoding="utf-8")
        log.info("ass_generated", path=str(out), line_count=len(dialogue_lines))
        return str(out)

    def burn_subtitles(
        self, video_path: str, ass_path: str, output_path: str
    ) -> str:
        """
        Burn ASS subtitles into video using FFmpeg.

        Args:
            video_path: Path to the input video.
            ass_path: Path to the .ass subtitle file.
            output_path: Path for the captioned output video.

        Returns:
            Absolute output path.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # Escape Windows-style paths (backslashes / colons) for FFmpeg vf filter
        escaped_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"ass={escaped_ass}",
            "-c:v", "libx264",
            "-c:a", "copy",
            str(output_path),
        ]
        log.info("burn_subtitles_start", video=video_path, ass=ass_path)
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as exc:
            log.error("burn_subtitles_failed", stderr=exc.stderr)
            raise RuntimeError(f"FFmpeg subtitle burn failed: {exc.stderr}") from exc

        log.info("burn_subtitles_complete", output=str(output_path))
        return str(output_path)
