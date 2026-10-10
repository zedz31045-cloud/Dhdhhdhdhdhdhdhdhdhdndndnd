from pathlib import Path

from src.image_engine import SUPPORTED_IMAGE_SUFFIXES
from src.models import MODELS, model_path, verify_file
from src.video_engine import SUPPORTED_VIDEO_SUFFIXES


def test_supported_formats_and_model_metadata():
    assert {".png", ".jpg", ".webp", ".tif"}.issubset(SUPPORTED_IMAGE_SUFFIXES)
    assert {".mp4", ".mov", ".mkv"}.issubset(SUPPORTED_VIDEO_SUFFIXES)
    assert set(MODELS) == {2, 4}
    assert MODELS[2]["algorithm"] == "fsrcnn"
    assert MODELS[4]["algorithm"] == "lapsrn"


def test_model_path_rejects_unsupported_scale():
    try:
        model_path(3)
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported scale must be rejected")


def test_model_integrity_check_rejects_missing_file(tmp_path: Path):
    assert not verify_file(tmp_path / "missing.pb", "0" * 64)


def test_model_integrity_check(tmp_path: Path):
    sample = tmp_path / "sample.pb"
    sample.write_bytes(b"a" * 2048)
    import hashlib
    digest = hashlib.sha256(sample.read_bytes()).hexdigest()
    assert verify_file(sample, digest)
    assert not verify_file(sample, "0" * 64)
