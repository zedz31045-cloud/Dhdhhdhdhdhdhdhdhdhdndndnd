"""FFmpeg-based conventional video resizing (not neural video enhancement)."""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

SUPPORTED_VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".webm"}


def find_ffmpeg() -> str | None:
    system = shutil.which("ffmpeg")
    if system:
        return system
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        return path if Path(path).is_file() else None
    except Exception:
        return None


def probe_duration(ffmpeg: str, source: Path) -> float | None:
    try:
        p = subprocess.run([ffmpeg, "-hide_banner", "-i", str(source)], capture_output=True, text=True, timeout=20)
        text = p.stderr or p.stdout
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
        if m:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return None


def upscale_video(
    source: str | Path,
    output_dir: str | Path,
    height: int,
    *,
    crf: int = 20,
    fps: int | None = None,
    preserve_audio: bool = True,
    progress: Callable[[int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> Path:
    """Resize/transcode video in a streaming FFmpeg process; audio may be copied."""
    src = Path(source).expanduser().resolve()
    if not src.is_file() or src.suffix.lower() not in SUPPORTED_VIDEO_SUFFIXES:
        raise ValueError(f"Unsupported or missing video: {src}")
    if height not in (1080, 1440, 2160) and not (240 <= height <= 4320):
        raise ValueError("Output height must be 240–4320 pixels")
    if not 0 <= crf <= 40:
        raise ValueError("CRF quality must be between 0 and 40")
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("لم يتم العثور على FFmpeg. أعد تثبيت حزمة التطبيق أو ثبّت FFmpeg.")
    out_dir = Path(output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{src.stem}_scaled_{height}p.mp4"
    index = 2
    while dest.exists():
        dest = out_dir / f"{src.stem}_scaled_{height}p_{index}.mp4"
        index += 1
    duration = probe_duration(ffmpeg, src)
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostats", "-y", "-i", str(src),
               "-map", "0:v:0", "-map", "0:a?", "-vf", f"scale=-2:{height}:flags=lanczos"]
    if fps:
        command += ["-r", str(fps)]
    command += ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf)]
    command += ["-c:a", "copy" if preserve_audio else "aac", "-movflags", "+faststart", "-progress", "pipe:1", str(dest)]
    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    try:
        assert process.stdout is not None
        for line in process.stdout:
            if cancelled and cancelled():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise InterruptedError("تم إلغاء معالجة الفيديو")
            if line.startswith("out_time_ms=") and duration and progress:
                try:
                    elapsed_media = int(line.split("=", 1)[1].strip()) / 1_000_000
                    progress(min(99, int(elapsed_media * 100 / duration)))
                except ValueError:
                    pass
            elif line.startswith("progress=end") and progress:
                progress(100)
        code = process.wait()
        if code:
            stderr = process.stderr.read()[-3000:] if process.stderr else ""
            raise RuntimeError(f"فشل FFmpeg (رمز {code}): {stderr.strip() or 'خطأ غير معروف'}")
        if not dest.is_file() or dest.stat().st_size == 0:
            raise RuntimeError("FFmpeg لم ينشئ ملف إخراج صالحًا")
        return dest
    except BaseException:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        dest.unlink(missing_ok=True)
        raise
