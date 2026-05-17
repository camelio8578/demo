"""
ClipRenderer: extract a video segment and reframe to 9:16 vertical for
short-form platforms using FFmpeg. Optional face-detection crop via OpenCV.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)


class ClipRenderer:
    """Render a candidate clip window to a 1080x1920 (9:16) MP4."""

    def render_clip(
        self,
        source_video_path: str,
        start_time: float,
        end_time: float,
        output_path: str,
        padding_seconds: float = 1.5,
    ) -> dict:
        """
        Full render pipeline: extract → reframe → thumbnail.

        Args:
            source_video_path: Absolute path to the downloaded source video.
            start_time: Clip start in seconds.
            end_time: Clip end in seconds.
            output_path: Destination path for the final 9:16 MP4.
            padding_seconds: Extra seconds added before start / after end.

        Returns:
            dict with output_path, thumbnail_path, resolution, fps,
            duration, file_size.
        """
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        # Padded start / end, clamped to non-negative
        start_adj = max(0.0, start_time - padding_seconds)
        end_adj = end_time + padding_seconds
        duration = end_adj - start_adj

        tmp_path = str(output_path_obj.parent / f"_tmp_{output_path_obj.stem}.mp4")
        thumbnail_path = str(output_path_obj.parent / f"{output_path_obj.stem}_thumb.jpg")

        log.info(
            "render_clip_start",
            source=source_video_path,
            start_adj=start_adj,
            duration=duration,
            output=output_path,
        )

        try:
            # 1. Extract segment
            self._extract_segment(source_video_path, start_adj, duration, tmp_path)

            # 2. Reframe to vertical
            self._reframe_to_vertical(tmp_path, output_path)

            # 3. Extract thumbnail (1 second into the rendered clip)
            self._extract_thumbnail(output_path, thumbnail_path, time_offset=1.0)

        finally:
            # Clean up temp file
            if Path(tmp_path).exists():
                try:
                    Path(tmp_path).unlink()
                except OSError:
                    pass

        # Collect metadata
        metadata = self._probe_video(output_path)
        file_size = Path(output_path).stat().st_size if Path(output_path).exists() else 0

        result = {
            "output_path": output_path,
            "thumbnail_path": thumbnail_path if Path(thumbnail_path).exists() else None,
            "resolution": metadata.get("resolution", "1080x1920"),
            "fps": metadata.get("fps"),
            "duration": metadata.get("duration", duration),
            "file_size": file_size,
        }

        log.info("render_clip_complete", output=output_path, file_size=file_size)
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_segment(
        self, input_path: str, start: float, duration: float, tmp_path: str
    ) -> None:
        """Extract a segment from the source video with FFmpeg."""
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(input_path),
            "-t", str(duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-avoid_negative_ts", "make_zero",
            str(tmp_path),
        ]
        log.info("ffmpeg_extract_segment", start=start, duration=duration)
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as exc:
            log.error("ffmpeg_extract_failed", stderr=exc.stderr)
            raise RuntimeError(f"FFmpeg segment extraction failed: {exc.stderr}") from exc

    def _reframe_to_vertical(self, input_path: str, output_path: str) -> None:
        """
        Convert to 1080x1920 (9:16) via center crop (with optional face detection).

        FFmpeg filter scales to fill 1080x1920, then crops to exact size.
        """
        log.info("reframe_to_vertical", input=input_path, output=output_path)

        vf = (
            "scale=iw*max(1080/iw\\,1920/ih):ih*max(1080/iw\\,1920/ih),"
            "crop=1080:1920"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", vf,
            "-c:v", "libx264",
            "-crf", "23",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(output_path),
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as exc:
            log.error("ffmpeg_reframe_failed", stderr=exc.stderr)
            raise RuntimeError(f"FFmpeg reframe failed: {exc.stderr}") from exc

    def _extract_thumbnail(
        self, video_path: str, output_path: str, time_offset: float = 1.0
    ) -> None:
        """Extract a single JPEG frame from the rendered clip."""
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(time_offset),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(output_path),
        ]
        log.info("ffmpeg_thumbnail", video=video_path, thumb=output_path)
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as exc:
            log.warning("ffmpeg_thumbnail_failed", stderr=exc.stderr)
            # Thumbnail failure is non-fatal

    def _probe_video(self, video_path: str) -> dict:
        """Use ffprobe to get basic video metadata."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,duration",
            "-of", "default=noprint_wrappers=1:nokey=0",
            str(video_path),
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
            metadata: dict = {}
            for line in result.stdout.splitlines():
                if "=" in line:
                    key, _, value = line.partition("=")
                    metadata[key.strip()] = value.strip()

            width = metadata.get("width")
            height = metadata.get("height")
            if width and height:
                metadata["resolution"] = f"{width}x{height}"

            fps_str = metadata.get("r_frame_rate", "")
            if "/" in fps_str:
                num, _, den = fps_str.partition("/")
                try:
                    metadata["fps"] = round(int(num) / int(den))
                except (ValueError, ZeroDivisionError):
                    pass

            duration_str = metadata.get("duration", "")
            if duration_str:
                try:
                    metadata["duration"] = float(duration_str)
                except ValueError:
                    pass

            return metadata
        except subprocess.CalledProcessError as exc:
            log.warning("ffprobe_failed", stderr=exc.stderr)
            return {}

    def _try_face_detect_crop(self, frame) -> tuple[int, int] | None:
        """
        Try to use OpenCV face detection to find the best crop center.
        Returns (x_center, y_center) or None if OpenCV is unavailable or
        no face found.
        """
        try:
            import cv2  # type: ignore

            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            face_cascade = cv2.CascadeClassifier(cascade_path)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

            if len(faces) == 0:
                return None

            # Use the largest detected face as anchor
            largest = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest
            return (x + w // 2, y + h // 2)
        except ImportError:
            return None
        except Exception as exc:
            log.warning("face_detection_error", error=str(exc))
            return None
