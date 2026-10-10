"""Image super-resolution using OpenCV's pretrained DNN models (CPU-first)."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps, ImageFilter

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def _read_oriented(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        return ImageOps.exif_transpose(opened).copy()


def _positions(length: int, tile: int) -> list[tuple[int, int]]:
    if length <= tile:
        return [(0, length)]
    stride = max(1, tile - 32)
    starts = list(range(0, max(1, length - tile + 1), stride))
    if starts[-1] + tile < length:
        starts.append(length - tile)
    return [(start, min(length, start + tile)) for start in starts]


def upscale_image(
    source: str | Path,
    scale: int,
    output_dir: str | Path,
    *,
    denoise: bool = False,
    tile_size: int = 512,
    progress: Callable[[int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> tuple[Path, tuple[int, int], tuple[int, int]]:
    """Run a pretrained neural SR model; original input is never overwritten."""
    import cv2
    import numpy as np
    from .models import MODELS, ensure_model

    src = Path(source).expanduser().resolve()
    if not src.is_file() or src.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        raise ValueError(f"Unsupported or missing image: {src}")
    if scale not in MODELS:
        raise ValueError("Scale must be 2 or 4")
    if not 64 <= tile_size <= 1024:
        raise ValueError("Tile size must be between 64 and 1024 pixels")
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    model = ensure_model(scale, progress=(lambda value: progress(int(value * 0.2)) if value >= 0 else None) if progress else None)
    spec = MODELS[scale]
    sr = cv2.dnn_superres.DnnSuperResImpl_create()
    sr.readModel(str(model))
    sr.setModel(spec["algorithm"], scale)

    original = _read_oriented(src)
    original_size = original.size
    has_alpha = original.mode in ("RGBA", "LA")
    if original.mode == "L":
        rgb = original
    else:
        rgb = original.convert("RGB")
    if denoise:
        rgb = rgb.filter(ImageFilter.MedianFilter(size=3))
    arr = np.asarray(rgb)
    # OpenCV expects BGR (or a one-channel grayscale matrix).
    if arr.ndim == 3:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    height, width = arr.shape[:2]
    if width * height > 150_000_000:
        raise ValueError("الصورة كبيرة جدًا للحد الآمن (150 ميغابكسل). اختر صورة أصغر.")

    # DNN inference on overlapping tiles bounds peak memory for large images.
    ys = _positions(height, tile_size)
    xs = _positions(width, tile_size)
    canvas_shape = (height * scale, width * scale) if arr.ndim == 2 else (height * scale, width * scale, arr.shape[2])
    result = np.empty(canvas_shape, dtype=np.uint8)
    total = len(ys) * len(xs)
    done = 0
    margin = 16
    for y0, y1 in ys:
        for x0, x1 in xs:
            if cancelled and cancelled():
                raise InterruptedError("تم إلغاء المعالجة")
            ey0, ey1 = max(0, y0 - margin), min(height, y1 + margin)
            ex0, ex1 = max(0, x0 - margin), min(width, x1 + margin)
            patch = arr[ey0:ey1, ex0:ex1]
            inferred = sr.upsample(patch)
            cy0, cy1 = (y0 - ey0) * scale, (y1 - ey0) * scale
            cx0, cx1 = (x0 - ex0) * scale, (x1 - ex0) * scale
            result[y0 * scale:y1 * scale, x0 * scale:x1 * scale] = inferred[cy0:cy1, cx0:cx1]
            done += 1
            if progress:
                progress(20 + int(done * 80 / total))

    if result.ndim == 3:
        result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        output_image = Image.fromarray(result, "RGB")
    else:
        output_image = Image.fromarray(result, "L")
    if has_alpha:
        alpha = original.getchannel("A").resize(output_image.size, Image.Resampling.LANCZOS)
        output_image.putalpha(alpha)
    suffix = ".png" if original.mode in ("RGBA", "LA") else src.suffix.lower()
    if suffix == ".jpg":
        suffix = ".jpg"
    destination = target_dir / f"{src.stem}_AI_{scale}x{suffix}"
    counter = 2
    while destination.exists():
        destination = target_dir / f"{src.stem}_AI_{scale}x_{counter}{suffix}"
        counter += 1
    save_options = {"quality": 95} if suffix in (".jpg", ".jpeg", ".webp") else {}
    if suffix in (".tif", ".tiff"):
        save_options = {"compression": "tiff_lzw"}
    output_image.save(destination, **save_options)
    return destination, original_size, output_image.size
