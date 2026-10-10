"""Verified runtime downloads for OpenCV DNN super-resolution models."""
from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable

_USER_DATA = os.environ.get("APPDATA") or os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
APP_DIR = Path(_USER_DATA) / "Dafan4KEnhancer"
MODEL_DIR = APP_DIR / "models"
_FSRCNN_URL = "https://raw.githubusercontent.com/opencv/opencv_extra/a568a1d06b9acb2f99fc0f0904dcca471b44db76/testdata/cv/dnn_superres/FSRCNN_x2.pb"
_LAPSRN_URL = "https://raw.githubusercontent.com/opencv/opencv_extra/658522228a6031154cac4d6535d2b4f379ecd51c/testdata/cv/dnn_superres/LapSRN_x4.pb"
MODELS = {
    2: {
        "file": "FSRCNN_x2.pb",
        "algorithm": "fsrcnn",
        "sha256": "366b33f0084c7b3f2bf6724f0a2c77bca94fcec9d7b6d72389d330073b380d5c",
        "url": _FSRCNN_URL,
    },
    4: {
        "file": "LapSRN_x4.pb",
        "algorithm": "lapsrn",
        "sha256": "263abfdba005a68730616e9753072141b8bfd09a799411883f285ea697d4d1fe",
        "url": _LAPSRN_URL,
    },
}


def model_path(scale: int) -> Path:
    if scale not in MODELS:
        raise ValueError("الدقة المدعومة هي تكبير 2× أو 4× فقط")
    return MODEL_DIR / MODELS[scale]["file"]


def verify_file(path: Path, expected: str) -> bool:
    if not path.is_file() or path.stat().st_size < 1024:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest() == expected


def ensure_model(scale: int, progress: Callable[[int], None] | None = None) -> Path:
    """Download a model to the per-user cache and verify its pinned SHA-256."""
    if scale not in MODELS:
        raise ValueError("Only 2x and 4x models are supported")
    spec = MODELS[scale]
    target = MODEL_DIR / spec["file"]
    if verify_file(target, spec["sha256"]):
        return target
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=target.name + ".", suffix=".part", dir=MODEL_DIR)
    os.close(fd)
    temp_path = Path(temporary)
    try:
        request = urllib.request.Request(spec["url"], headers={"User-Agent": "Dafan4KEnhancer/1.0"})
        with urllib.request.urlopen(request, timeout=45) as response, temp_path.open("wb") as output:
            total = int(response.headers.get("Content-Length", "0") or 0)
            received = 0
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                received += len(chunk)
                if progress:
                    progress(min(100, int(received * 100 / total)) if total else -1)
        if not verify_file(temp_path, spec["sha256"]):
            raise RuntimeError("فشل التحقق من سلامة نموذج الذكاء الاصطناعي؛ حُذف التنزيل غير السليم.")
        temp_path.replace(target)
        if progress:
            progress(100)
        return target
    finally:
        temp_path.unlink(missing_ok=True)


def model_status() -> dict[int, bool]:
    return {scale: verify_file(model_path(scale), info["sha256"]) for scale, info in MODELS.items()}
