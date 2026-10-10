from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageOps

from src.image_engine import SUPPORTED_IMAGE_SUFFIXES, upscale_image
from src.models import APP_DIR, MODELS, ensure_model, model_status
from src.video_engine import SUPPORTED_VIDEO_SUFFIXES, find_ffmpeg, upscale_video
from src import __version__

APP_NAME = "DAFAN 4K ENHANCER"
BG = "#080d17"
PANEL = "#101a2b"
PANEL_ALT = "#142238"
CYAN = "#18c8ef"
BLUE = "#2179e8"
TEXT = "#eaf3ff"
MUTED = "#91a4bd"

STRINGS = {
    "en": {
        "title": "DAFAN 4K ENHANCER", "tagline": "AI IMAGE SUPER-RESOLUTION  ·  VIDEO RESIZE",
        "tab_images": "Images", "tab_video": "Video", "tab_queue": "Queue & history", "tab_settings": "Settings & about",
        "add_images": "＋  Add images", "add_videos": "＋  Add videos", "output": "Output folder", "browse": "Browse",
        "scale": "Neural model / scale", "denoise": "Gentle denoise before AI", "quality": "Encoding quality (CRF)",
        "resolution": "Output height", "manual_height": "Manual height (px)", "audio": "Preserve original audio stream when compatible", "fps": "Output FPS (optional)",
        "start": "Start all", "stop": "Stop all", "cancel": "Cancel current", "retry": "Retry failed", "open": "Open results folder",
        "clear": "Clear finished", "queue": "Processing queue", "empty": "Add images or videos to create your queue.",
        "preview": "Before / after preview", "before": "SOURCE", "after": "RESULT", "no_preview": "Choose an image task to preview",
        "stats_done": "Completed", "stats_failed": "Failed", "stats_running": "Running", "stats_waiting": "Waiting",
        "model_check": "Check / download AI models", "model_ready": "AI models", "ffmpeg": "FFmpeg", "language": "العربية",
        "save_settings": "Save settings", "about": "About", "about_text": "Dafan 4K Enhancer  ·  v{version}\nCopyright © 2026 Dafan\n\nPhoto AI uses OpenCV DNN super-resolution models (FSRCNN 2×, LapSRN 4×). Results are estimates; generated details may not exist in the source.\n\nVideo mode uses FFmpeg Lanczos scaling and H.264 encoding. It is conventional resizing, not AI video enhancement.",
        "settings_note": "Models download on first use from the official OpenCV extra-data repository and are SHA-256 verified. AI inference currently runs on CPU for broad compatibility.",
        "help_image": "Neural super-resolution creates plausible detail; it cannot recover information absent from the original. 4× is slower and uses more memory.",
        "help_video": "Video processing is conventional Lanczos resizing through FFmpeg, not AI. The source is preserved. Output is MP4/H.264.",
        "status_pending": "Waiting", "status_running": "Processing", "status_done": "Completed", "status_failed": "Failed", "status_cancelled": "Cancelled",
        "choose_images": "Select images", "choose_videos": "Select videos", "none": "Not available", "ready": "Ready", "missing": "Missing",
        "error": "Error", "done_message": "Finished processing queue.", "download_start": "Downloading and verifying model…", "no_task": "No task selected",
        "memory": "Large images are tiled to limit memory; maximum accepted source size is 150 megapixels.",
    },
    "ar": {
        "title": "محسّن دافان 4K", "tagline": "تحسين الصور بالذكاء الاصطناعي  ·  تحجيم الفيديو",
        "tab_images": "الصور", "tab_video": "الفيديو", "tab_queue": "قائمة الانتظار والسجل", "tab_settings": "الإعدادات وحول",
        "add_images": "＋  إضافة صور", "add_videos": "＋  إضافة فيديوهات", "output": "مجلد النتائج", "browse": "استعراض",
        "scale": "نموذج الذكاء الاصطناعي / التكبير", "denoise": "تقليل تشويش خفيف قبل التحسين", "quality": "جودة الترميز (CRF)",
        "resolution": "ارتفاع الإخراج", "manual_height": "ارتفاع يدوي (بكسل)", "audio": "الحفاظ على مسار الصوت الأصلي إن كان متوافقًا", "fps": "معدل الإطارات (اختياري)",
        "start": "بدء الكل", "stop": "إيقاف الكل", "cancel": "إلغاء المهمة الحالية", "retry": "إعادة محاولة الفاشلة", "open": "فتح مجلد النتائج",
        "clear": "مسح المكتمل", "queue": "قائمة المعالجة", "empty": "أضف صورًا أو فيديوهات لإنشاء قائمة المعالجة.",
        "preview": "معاينة قبل / بعد", "before": "الأصل", "after": "النتيجة", "no_preview": "اختر مهمة صورة للمعاينة",
        "stats_done": "مكتملة", "stats_failed": "فاشلة", "stats_running": "قيد التنفيذ", "stats_waiting": "بانتظار البدء",
        "model_check": "فحص / تنزيل نماذج AI", "model_ready": "نماذج AI", "ffmpeg": "FFmpeg", "language": "English",
        "save_settings": "حفظ الإعدادات", "about": "حول البرنامج", "about_text": "محسّن دافان 4K  ·  الإصدار {version}\nحقوق النشر © 2026 Dafan\n\nتحسين الصور العصبي يستخدم نماذج OpenCV DNN (FSRCNN 2× وLapSRN 4×). النتائج تقديرية وقد تتضمن تفاصيل مولدة غير موجودة في المصدر.\n\nيعالج الفيديو عبر تحجيم Lanczos وترميز H.264 باستخدام FFmpeg. هذه معالجة تقليدية وليست تحسين فيديو بالذكاء الاصطناعي.",
        "settings_note": "تنزل النماذج عند أول استخدام من مستودع بيانات OpenCV الرسمي، ثم تتحقق سلامتها ببصمة SHA-256. يعمل الاستدلال حاليًا على CPU للتوافق.",
        "help_image": "ينشئ التحسين العصبي تفاصيل محتملة، ولا يستعيد معلومات غير موجودة في الأصل. تكبير 4× أبطأ ويستهلك ذاكرة أكثر.",
        "help_video": "معالجة الفيديو تحجيم Lanczos تقليدي عبر FFmpeg وليست ذكاءً اصطناعيًا. يُحفظ الأصل دون تغيير. الإخراج MP4/H.264.",
        "status_pending": "بانتظار البدء", "status_running": "قيد المعالجة", "status_done": "مكتملة", "status_failed": "فشلت", "status_cancelled": "ألغيت",
        "choose_images": "اختيار الصور", "choose_videos": "اختيار الفيديوهات", "none": "غير متاح", "ready": "جاهز", "missing": "غير موجود",
        "error": "خطأ", "done_message": "انتهت معالجة القائمة.", "download_start": "جارٍ تنزيل النموذج والتحقق منه…", "no_task": "لم تحدد مهمة",
        "memory": "تُقسّم الصور الكبيرة لتقليل الذاكرة؛ الحد الأقصى للصورة المصدر 150 ميغابكسل.",
    },
}

SETTINGS_FILE = APP_DIR / "settings.json"
HISTORY_FILE = APP_DIR / "history.json"


@dataclass
class Task:
    path: Path
    kind: str
    state: str = "pending"
    result: Path | None = None
    error: str = ""
    progress: int = 0


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


class DafanApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.geometry("1240x850")
        self.minsize(980, 690)
        self.configure(fg_color=BG)
        self.settings = load_json(SETTINGS_FILE, {"output_dir": str(Path.home() / "Pictures" / "Dafan4K"), "language": "en", "scale": "2× · FSRCNN (CPU fast)", "height": "2160p · 4K", "manual_height": "", "tile_size": 512, "crf": 20, "fps": ""})
        self.lang = self.settings.get("language", "en") if self.settings.get("language") in STRINGS else "en"
        self.tasks: list[Task] = []
        self.events: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self.cancel_event = threading.Event()
        self.stop_all_event = threading.Event()
        self.active = False
        self.selected_index: int | None = None
        self.row_widgets: list[ctk.CTkFrame] = []
        self._build_ui()
        self.after(200, self._poll_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def tr(self, key):
        return STRINGS[self.lang].get(key, key)

    def _build_ui(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.row_widgets = []
        shell = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        shell.pack(fill="both", expand=True, padx=24, pady=20)
        header = ctk.CTkFrame(shell, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(brand, text="✦  " + self.tr("title"), font=ctk.CTkFont(size=26, weight="bold"), text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(brand, text=self.tr("tagline"), font=ctk.CTkFont(size=11, weight="bold"), text_color=CYAN).pack(anchor="w", padx=(36, 0), pady=(2, 0))
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right")
        self.output_label = ctk.CTkLabel(right, text=self.tr("output"), text_color=MUTED)
        self.output_label.pack(side="left", padx=(0, 8))
        self.output_button = ctk.CTkButton(right, text=self.tr("browse"), width=100, height=34, fg_color=PANEL_ALT, hover_color="#203454", command=self.choose_output)
        self.output_button.pack(side="left", padx=(0, 10))
        self.language_button = ctk.CTkButton(right, text=self.tr("language"), width=90, height=34, fg_color=BLUE, hover_color="#165fc1", command=self.toggle_language)
        self.language_button.pack(side="left")

        # Small status dashboard
        stats = ctk.CTkFrame(shell, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 14))
        self.stat_labels = {}
        for key, color in [("stats_done", "#21c78a"), ("stats_failed", "#ff657a"), ("stats_running", CYAN), ("stats_waiting", MUTED)]:
            card = ctk.CTkFrame(stats, fg_color=PANEL, corner_radius=12, height=60)
            card.pack(side="left", fill="x", expand=True, padx=(0, 10))
            card.pack_propagate(False)
            value = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=21, weight="bold"), text_color=color)
            value.pack(side="left", padx=(16, 9))
            label = ctk.CTkLabel(card, text=self.tr(key), text_color=MUTED, font=ctk.CTkFont(size=12))
            label.pack(side="left")
            self.stat_labels[key] = (value, label)

        self.tabs = ctk.CTkTabview(shell, fg_color=PANEL, segmented_button_selected_color=BLUE, segmented_button_selected_hover_color="#165fc1", segmented_button_unselected_color=PANEL_ALT)
        self.tabs.pack(fill="both", expand=True)
        self.tab_images = self.tabs.add(self.tr("tab_images"))
        self.tab_video = self.tabs.add(self.tr("tab_video"))
        self.tab_queue = self.tabs.add(self.tr("tab_queue"))
        self.tab_settings = self.tabs.add(self.tr("tab_settings"))
        self._build_images_tab()
        self._build_video_tab()
        self._build_queue_tab()
        self._build_settings_tab()
        self.refresh_queue()

    def _section(self, parent, title, subtitle=None):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="x", padx=18, pady=(14, 6))
        ctk.CTkLabel(box, text=title, font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(box, text=subtitle, font=ctk.CTkFont(size=11), text_color=MUTED, wraplength=900, justify="left").pack(anchor="w", pady=(4, 0))
        return box

    def _build_images_tab(self):
        self._section(self.tab_images, self.tr("preview"), self.tr("help_image"))
        controls = ctk.CTkFrame(self.tab_images, fg_color="transparent")
        controls.pack(fill="x", padx=18, pady=12)
        self.add_images_button = ctk.CTkButton(controls, text=self.tr("add_images"), command=self.add_images, height=40, fg_color=BLUE, hover_color="#165fc1")
        self.add_images_button.pack(side="left", padx=(0, 12))
        self.scale_label = ctk.CTkLabel(controls, text=self.tr("scale"), text_color=MUTED)
        self.scale_label.pack(side="left", padx=(4, 8))
        self.scale_menu = ctk.CTkOptionMenu(controls, values=["2× · FSRCNN (CPU fast)", "4× · LapSRN (slower)"], width=220, command=lambda _: self.save_settings())
        self.scale_menu.set(self.settings.get("scale", "2× · FSRCNN (CPU fast)"))
        self.scale_menu.pack(side="left", padx=(0, 16))
        self.denoise_var = ctk.BooleanVar(value=False)
        self.denoise_checkbox = ctk.CTkCheckBox(controls, text=self.tr("denoise"), variable=self.denoise_var, checkbox_width=18, checkbox_height=18)
        self.denoise_checkbox.pack(side="left", padx=8)
        self.preview_frame = ctk.CTkFrame(self.tab_images, fg_color="transparent")
        self.preview_frame.pack(fill="both", expand=True, padx=18, pady=(5, 14))
        self.preview_labels = []
        for caption in (self.tr("before"), self.tr("after")):
            card = ctk.CTkFrame(self.preview_frame, fg_color="#0b1320", corner_radius=12)
            card.pack(side="left", fill="both", expand=True, padx=(0, 10))
            ctk.CTkLabel(card, text=caption, text_color=CYAN, font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="nw", padx=12, pady=(10, 2))
            image_label = ctk.CTkLabel(card, text=self.tr("no_preview"), text_color=MUTED)
            image_label.pack(fill="both", expand=True, padx=12, pady=12)
            self.preview_labels.append(image_label)

    def _build_video_tab(self):
        self._section(self.tab_video, self.tr("tab_video"), self.tr("help_video"))
        controls = ctk.CTkFrame(self.tab_video, fg_color="transparent")
        controls.pack(fill="x", padx=18, pady=12)
        self.add_videos_button = ctk.CTkButton(controls, text=self.tr("add_videos"), command=self.add_videos, height=40, fg_color=BLUE, hover_color="#165fc1")
        self.add_videos_button.pack(side="left", padx=(0, 18))
        self.resolution_label = ctk.CTkLabel(controls, text=self.tr("resolution"), text_color=MUTED)
        self.resolution_label.pack(side="left", padx=(0, 8))
        self.height_menu = ctk.CTkOptionMenu(controls, values=["1080p", "1440p", "2160p · 4K"], width=150, command=lambda _: self.save_settings())
        self.height_menu.set(self.settings.get("height", "2160p · 4K"))
        self.height_menu.pack(side="left", padx=(0, 18))
        self.crf_label = ctk.CTkLabel(controls, text=self.tr("quality"), text_color=MUTED)
        self.crf_label.pack(side="left", padx=(0, 8))
        self.crf_slider = ctk.CTkSlider(controls, from_=16, to=32, number_of_steps=16, command=self._crf_changed, width=160)
        self.crf_slider.set(int(self.settings.get("crf", 20)))
        self.crf_slider.pack(side="left")
        self.crf_value = ctk.CTkLabel(controls, text=str(self.settings.get("crf", 20)), text_color=TEXT, width=28)
        self.crf_value.pack(side="left", padx=(6, 0))
        options = ctk.CTkFrame(self.tab_video, fg_color="transparent")
        options.pack(fill="x", padx=18, pady=4)
        self.audio_var = ctk.BooleanVar(value=True)
        self.audio_checkbox = ctk.CTkCheckBox(options, text=self.tr("audio"), variable=self.audio_var, checkbox_width=18, checkbox_height=18)
        self.audio_checkbox.pack(side="left", padx=(0, 18))
        self.fps_label = ctk.CTkLabel(options, text=self.tr("fps"), text_color=MUTED)
        self.fps_label.pack(side="left", padx=(0, 8))
        self.fps_entry = ctk.CTkEntry(options, width=100, placeholder_text="source")
        self.fps_entry.insert(0, str(self.settings.get("fps", "")))
        self.fps_entry.pack(side="left")
        self.manual_height_label = ctk.CTkLabel(options, text=self.tr("manual_height"), text_color=MUTED)
        self.manual_height_label.pack(side="left", padx=(18, 8))
        self.manual_height_entry = ctk.CTkEntry(options, width=100, placeholder_text="240–4320")
        self.manual_height_entry.insert(0, str(self.settings.get("manual_height", "")))
        self.manual_height_entry.pack(side="left")
        self._section(self.tab_video, "FFmpeg", self.tr("memory"))

    def _build_queue_tab(self):
        self._section(self.tab_queue, self.tr("queue"))
        bar = ctk.CTkFrame(self.tab_queue, fg_color="transparent")
        bar.pack(fill="x", padx=18, pady=(4, 10))
        self.start_button = ctk.CTkButton(bar, text=self.tr("start"), command=self.start_queue, fg_color=BLUE, hover_color="#165fc1")
        self.start_button.pack(side="left", padx=(0, 8))
        self.cancel_button = ctk.CTkButton(bar, text=self.tr("cancel"), command=self.cancel_current, fg_color="#6c527a", hover_color="#805d92")
        self.cancel_button.pack(side="left", padx=(0, 8))
        self.stop_button = ctk.CTkButton(bar, text=self.tr("stop"), command=self.stop_all, fg_color="#9a3e52", hover_color="#b3475e")
        self.stop_button.pack(side="left", padx=(0, 8))
        self.retry_button = ctk.CTkButton(bar, text=self.tr("retry"), command=self.retry_failed, fg_color=PANEL_ALT, hover_color="#203454")
        self.retry_button.pack(side="left", padx=(0, 8))
        self.open_button = ctk.CTkButton(bar, text=self.tr("open"), command=self.open_output, fg_color=PANEL_ALT, hover_color="#203454")
        self.open_button.pack(side="left", padx=(0, 8))
        self.clear_button = ctk.CTkButton(bar, text=self.tr("clear"), command=self.clear_finished, fg_color=PANEL_ALT, hover_color="#203454")
        self.clear_button.pack(side="right")
        self.progress_bar = ctk.CTkProgressBar(self.tab_queue, progress_color=CYAN)
        self.progress_bar.pack(fill="x", padx=18, pady=(2, 10))
        self.progress_bar.set(0)
        self.queue_frame = ctk.CTkScrollableFrame(self.tab_queue, fg_color="#0b1320", corner_radius=10)
        self.queue_frame.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.history_caption = ctk.CTkLabel(self.tab_queue, text="Recent activity" if self.lang == "en" else "آخر العمليات", text_color=CYAN, font=ctk.CTkFont(size=12, weight="bold"))
        self.history_caption.pack(anchor="w", padx=18, pady=(4, 2))
        self.history_box = ctk.CTkTextbox(self.tab_queue, height=86, fg_color="#0b1320", text_color=MUTED, wrap="word")
        self.history_box.pack(fill="x", padx=18, pady=(0, 12))
        self.refresh_history()
        self.queue_empty_label = ctk.CTkLabel(self.queue_frame, text=self.tr("empty"), text_color=MUTED)
        self.queue_empty_label.pack(pady=40)

    def _build_settings_tab(self):
        self._section(self.tab_settings, self.tr("settings_note"))
        status_card = ctk.CTkFrame(self.tab_settings, fg_color=PANEL_ALT, corner_radius=12)
        status_card.pack(fill="x", padx=18, pady=(12, 8))
        self.model_status_label = ctk.CTkLabel(status_card, text="", text_color=TEXT, justify="left", wraplength=880)
        self.model_status_label.pack(anchor="w", padx=16, pady=12)
        action = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        action.pack(fill="x", padx=18, pady=8)
        self.model_button = ctk.CTkButton(action, text=self.tr("model_check"), command=self.check_models, fg_color=BLUE, hover_color="#165fc1")
        self.model_button.pack(side="left", padx=(0, 10))
        self.save_button = ctk.CTkButton(action, text=self.tr("save_settings"), command=self.save_settings, fg_color=PANEL_ALT, hover_color="#203454")
        self.save_button.pack(side="left")
        memory_frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        memory_frame.pack(fill="x", padx=18, pady=(8, 4))
        ctk.CTkLabel(memory_frame, text="Image tile size / حجم رقعة الصورة", text_color=MUTED).pack(side="left", padx=(0, 10))
        self.tile_size_menu = ctk.CTkOptionMenu(memory_frame, values=["256 px · lower memory", "512 px · balanced", "768 px · faster"], width=200, command=lambda _: self.save_settings())
        tile_value = int(self.settings.get("tile_size", 512))
        self.tile_size_menu.set({256: "256 px · lower memory", 768: "768 px · faster"}.get(tile_value, "512 px · balanced"))
        self.tile_size_menu.pack(side="left")
        ctk.CTkLabel(self.tab_settings, text=self.tr("memory"), text_color=MUTED, wraplength=900, justify="left").pack(anchor="w", padx=18, pady=8)
        ctk.CTkLabel(self.tab_settings, text=self.tr("about"), text_color=CYAN, font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=18, pady=(22, 4))
        self.about_label = ctk.CTkLabel(self.tab_settings, text=self.tr("about_text").format(version=__version__), text_color=MUTED, justify="left", wraplength=930)
        self.about_label.pack(anchor="w", padx=18, pady=(0, 16))
        self.refresh_environment_status()

    def _crf_changed(self, value):
        self.crf_value.configure(text=str(round(value)))

    def choose_output(self):
        selected = filedialog.askdirectory(title=self.tr("output"), initialdir=self.settings.get("output_dir", str(Path.home())))
        if selected:
            self.settings["output_dir"] = selected
            self.save_settings()

    def add_images(self):
        paths = filedialog.askopenfilenames(title=self.tr("choose_images"), filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff")])
        self._add_paths(paths, "image")

    def add_videos(self):
        paths = filedialog.askopenfilenames(title=self.tr("choose_videos"), filetypes=[("Videos", "*.mp4 *.mov *.mkv *.avi *.webm")])
        self._add_paths(paths, "video")

    def _add_paths(self, paths, kind):
        allowed = SUPPORTED_IMAGE_SUFFIXES if kind == "image" else SUPPORTED_VIDEO_SUFFIXES
        existing = {str(task.path) for task in self.tasks if task.state in ("pending", "running")}
        for raw in paths:
            p = Path(raw).expanduser().resolve()
            if p.is_file() and p.suffix.lower() in allowed and str(p) not in existing:
                self.tasks.append(Task(p, kind))
                existing.add(str(p))
        self.refresh_queue()

    def _model_scale(self):
        return 4 if self.scale_menu.get().startswith("4") else 2

    def _output_directory(self) -> Path:
        path = Path(self.settings.get("output_dir") or (Path.home() / "Pictures" / "Dafan4K")).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def start_queue(self):
        if self.active:
            return
        pending = [i for i, task in enumerate(self.tasks) if task.state in ("pending", "cancelled")]
        if not pending:
            self.tabs.set(self.tr("tab_queue"))
            return
        self.cancel_event.clear()
        self.stop_all_event.clear()
        height_text = self.height_menu.get().split("p")[0]
        manual_height = self.manual_height_entry.get().strip()
        try:
            output_height = int(manual_height) if manual_height else int(height_text)
            if not 240 <= output_height <= 4320:
                raise ValueError
        except ValueError:
            messagebox.showerror(self.tr("error"), "Output height must be 240–4320 pixels")
            return
        fps_text = self.fps_entry.get().strip()
        try:
            output_fps = int(fps_text) if fps_text else None
            if output_fps is not None and not 1 <= output_fps <= 240:
                raise ValueError
        except ValueError:
            messagebox.showerror(self.tr("error"), "FPS must be between 1 and 240")
            return
        config = {
            "scale": self._model_scale(), "denoise": self.denoise_var.get(),
            "output_dir": self.settings.get("output_dir", str(Path.home() / "Pictures" / "Dafan4K")),
            "height": output_height, "fps": output_fps,
            "crf": round(self.crf_slider.get()), "preserve_audio": self.audio_var.get(),
            "tile_size": 256 if self.tile_size_menu.get().startswith("256") else 768 if self.tile_size_menu.get().startswith("768") else 512,
        }
        self.active = True
        self.worker = threading.Thread(target=self._worker_run, args=(pending, config), daemon=True)
        self.worker.start()
        self.refresh_queue()

    def _worker_run(self, indexes, config):
        for position, index in enumerate(indexes):
            if self.stop_all_event.is_set():
                self.events.put(("task", index, "cancelled", None, "Stopped before start", 0))
                continue
            self.cancel_event.clear()
            task = self.tasks[index]
            self.events.put(("task", index, "running", None, "", 0))
            try:
                if task.kind == "image":
                    result, before, after = upscale_image(task.path, config["scale"], Path(config["output_dir"]), denoise=config["denoise"], tile_size=config["tile_size"], progress=lambda p: self.events.put(("progress", index, p)), cancelled=lambda: self.cancel_event.is_set() or self.stop_all_event.is_set())
                    msg = f"{before[0]}×{before[1]} → {after[0]}×{after[1]}"
                else:
                    output_dir = Path(config["output_dir"])
                    output_dir.mkdir(parents=True, exist_ok=True)
                    height = config["height"]
                    result = upscale_video(task.path, output_dir, height, crf=config["crf"], fps=config["fps"], preserve_audio=config["preserve_audio"], progress=lambda p: self.events.put(("progress", index, p)), cancelled=lambda: self.cancel_event.is_set() or self.stop_all_event.is_set())
                    msg = f"Scaled to {height}p · conventional FFmpeg resize"
                self.events.put(("task", index, "done", str(result), msg, 100))
            except InterruptedError as exc:
                state = "cancelled"
                self.events.put(("task", index, state, None, str(exc), 0))
            except Exception as exc:
                self.events.put(("task", index, "failed", None, str(exc), 0))
            if self.stop_all_event.is_set():
                for remaining in indexes[position + 1:]:
                    self.events.put(("task", remaining, "cancelled", None, "Stopped before start", 0))
                break
        self.events.put(("worker_done",))

    def cancel_current(self):
        if self.active:
            self.cancel_event.set()

    def stop_all(self):
        if self.active:
            self.stop_all_event.set()
            self.cancel_event.set()

    def retry_failed(self):
        for task in self.tasks:
            if task.state == "failed":
                task.state, task.error, task.progress = "pending", "", 0
        self.refresh_queue()
        self.start_queue()

    def clear_finished(self):
        if self.active:
            return
        self.tasks = [t for t in self.tasks if t.state in ("pending", "running")]
        self.selected_index = None
        self.refresh_queue()
        self._show_preview(None)

    def refresh_queue(self):
        if not hasattr(self, "queue_frame"):
            return
        for child in self.queue_frame.winfo_children():
            child.destroy()
        self.row_widgets.clear()
        if not self.tasks:
            self.queue_empty_label = ctk.CTkLabel(self.queue_frame, text=self.tr("empty"), text_color=MUTED)
            self.queue_empty_label.pack(pady=40)
        else:
            for idx, task in enumerate(self.tasks):
                row = ctk.CTkFrame(self.queue_frame, fg_color=PANEL if idx % 2 == 0 else "#0e1828", corner_radius=8)
                row.pack(fill="x", padx=7, pady=4)
                self.row_widgets.append(row)
                icon = "▣" if task.kind == "image" else "▶"
                ctk.CTkLabel(row, text=icon, text_color=CYAN, width=28).pack(side="left", padx=(8, 0))
                name = ctk.CTkLabel(row, text=task.path.name, text_color=TEXT, anchor="w")
                name.pack(side="left", fill="x", expand=True, padx=8, pady=8)
                try:
                    size_text = f"{task.path.stat().st_size / (1024 * 1024):.1f} MB"
                    if task.kind == "image":
                        with Image.open(task.path) as im:
                            size_text += f" · {im.width}×{im.height}"
                except Exception:
                    size_text = "—"
                ctk.CTkLabel(row, text=size_text, text_color=MUTED, width=150, font=ctk.CTkFont(size=10)).pack(side="left", padx=4)
                status_key = {"pending":"status_pending", "running":"status_running", "done":"status_done", "failed":"status_failed", "cancelled":"status_cancelled"}.get(task.state, "status_pending")
                status_color = {"done":"#21c78a", "failed":"#ff657a", "running":CYAN, "cancelled":"#e4a853", "pending":MUTED}.get(task.state, MUTED)
                ctk.CTkLabel(row, text=self.tr(status_key), text_color=status_color, width=125).pack(side="left", padx=8)
                if task.state == "running":
                    bar = ctk.CTkProgressBar(row, width=100, progress_color=CYAN)
                    bar.pack(side="left", padx=8)
                    bar.set(task.progress / 100)
                if task.result and task.kind == "image":
                    ctk.CTkButton(row, text="Preview", width=76, height=28, fg_color=PANEL_ALT, command=lambda i=idx: self.select_task(i)).pack(side="right", padx=10)
                row.bind("<Button-1>", lambda _e, i=idx: self.select_task(i))
                name.bind("<Button-1>", lambda _e, i=idx: self.select_task(i))
                if task.error:
                    ctk.CTkLabel(self.queue_frame, text=task.error[:300], text_color="#ff8b9a", font=ctk.CTkFont(size=10), anchor="w", wraplength=880, justify="left").pack(fill="x", padx=34, pady=(0, 4))
        counts = {s: sum(1 for t in self.tasks if t.state == s) for s in ("done", "failed", "running", "pending")}
        for key, state in [("stats_done", "done"), ("stats_failed", "failed"), ("stats_running", "running"), ("stats_waiting", "pending")]:
            if key in self.stat_labels:
                self.stat_labels[key][0].configure(text=str(counts[state]))
        if hasattr(self, "start_button"):
            self.start_button.configure(state="disabled" if self.active else "normal")
            self.stop_button.configure(state="normal" if self.active else "disabled")
            self.cancel_button.configure(state="normal" if self.active else "disabled")

    def _poll_events(self):
        changed = False
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "task":
                    _, idx, state, result, error, progress = event
                    if idx < len(self.tasks):
                        task = self.tasks[idx]
                        task.state, task.error, task.progress = state, error, progress
                        task.result = Path(result) if result else None
                        if state == "done":
                            self._record_history(task)
                    changed = True
                elif event[0] == "progress":
                    _, idx, value = event
                    if idx < len(self.tasks):
                        self.tasks[idx].progress = max(0, min(100, int(value)))
                        self.progress_bar.set(self.tasks[idx].progress / 100)
                        changed = True
                elif event[0] == "worker_done":
                    self.active = False
                    self.progress_bar.set(0)
                    changed = True
                elif event[0] == "models_done":
                    self.model_button.configure(state="normal")
                    self.refresh_environment_status()
                    messagebox.showinfo(self.tr("model_ready"), self.tr("ready"))
                elif event[0] == "models_error":
                    self.model_button.configure(state="normal")
                    self.refresh_environment_status()
                    messagebox.showerror(self.tr("error"), event[1])
        except queue.Empty:
            pass
        if changed:
            self.refresh_queue()
            if self.selected_index is not None and self.selected_index < len(self.tasks):
                self._show_preview(self.tasks[self.selected_index])
        self.after(250, self._poll_events)

    def select_task(self, index):
        self.selected_index = index
        task = self.tasks[index]
        if task.kind == "image":
            self._show_preview(task)
            self.tabs.set(self.tr("tab_images"))

    def _show_preview(self, task):
        if not hasattr(self, "preview_labels"):
            return
        if not task or task.kind != "image":
            for label in self.preview_labels:
                label.configure(image=None, text=self.tr("no_preview"))
            return
        paths = [task.path, task.result]
        self.preview_images = []
        for label, path in zip(self.preview_labels, paths):
            if path and path.is_file():
                try:
                    with Image.open(path) as image:
                        image = ImageOps.exif_transpose(image).convert("RGB")
                        image.thumbnail((480, 360), Image.Resampling.LANCZOS)
                        preview = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
                    self.preview_images.append(preview)
                    label.configure(image=preview, text="")
                except Exception:
                    label.configure(image=None, text=path.name)
            else:
                label.configure(image=None, text=task.path.name if path else self.tr("no_preview"))

    def _record_history(self, task):
        history = load_json(HISTORY_FILE, [])
        history.append({"source": str(task.path), "result": str(task.result), "kind": task.kind, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
        save_json(HISTORY_FILE, history[-300:])

    def refresh_history(self):
        if not hasattr(self, "history_box"):
            return
        history = load_json(HISTORY_FILE, [])
        lines = [f"{item.get('time', '')}  ·  {Path(item.get('result', '')).name}" for item in history[-5:]]
        if not lines:
            lines = [self.tr("empty")]
        self.history_box.configure(state="normal")
        self.history_box.delete("1.0", "end")
        self.history_box.insert("1.0", "\n".join(reversed(lines)))
        self.history_box.configure(state="disabled")

    def open_output(self):
        path = self._output_directory()
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror(self.tr("error"), str(exc))

    def save_settings(self):
        if hasattr(self, "scale_menu"):
            self.settings["scale"] = self.scale_menu.get()
        if hasattr(self, "height_menu"):
            self.settings["height"] = self.height_menu.get()
        if hasattr(self, "crf_slider"):
            self.settings["crf"] = round(self.crf_slider.get())
        if hasattr(self, "fps_entry"):
            self.settings["fps"] = self.fps_entry.get().strip()
        if hasattr(self, "manual_height_entry"):
            self.settings["manual_height"] = self.manual_height_entry.get().strip()
        if hasattr(self, "tile_size_menu"):
            tile = self.tile_size_menu.get()
            self.settings["tile_size"] = 256 if tile.startswith("256") else 768 if tile.startswith("768") else 512
        self.settings["language"] = self.lang
        self.settings["output_dir"] = self.settings.get("output_dir", str(Path.home() / "Pictures" / "Dafan4K"))
        save_json(SETTINGS_FILE, self.settings)
        self.refresh_environment_status()

    def refresh_environment_status(self):
        if not hasattr(self, "model_status_label"):
            return
        statuses = model_status()
        model_lines = [f"{scale}× {MODELS[scale]['algorithm'].upper()}: {self.tr('ready') if ready else self.tr('missing')}" for scale, ready in statuses.items()]
        self.model_status_label.configure(text=f"{self.tr('model_ready')}:  " + "  ·  ".join(model_lines) + f"\n{self.tr('ffmpeg')}:  {self.tr('ready') if find_ffmpeg() else self.tr('missing')}\n\n{self.tr('settings_note')}")

    def check_models(self):
        if self.active:
            return
        self.model_button.configure(state="disabled")
        self.model_status_label.configure(text=self.tr("download_start"))
        threading.Thread(target=self._download_models_worker, daemon=True).start()

    def _download_models_worker(self):
        try:
            for scale in (2, 4):
                ensure_model(scale)
            self.events.put(("models_done", None))
        except Exception as exc:
            self.events.put(("models_error", str(exc)))

    def toggle_language(self):
        self.save_settings()
        self.settings["language"] = "ar" if self.lang == "en" else "en"
        self.lang = self.settings["language"]
        save_json(SETTINGS_FILE, self.settings)
        self._build_ui()

    def _on_close(self):
        self.save_settings()
        if self.active:
            self.stop_all_event.set()
            self.cancel_event.set()
        self.destroy()


def main():
    if "--self-test" in sys.argv:
        from src.models import model_status
        print(f"Dafan {__version__}; models={model_status()}; ffmpeg={find_ffmpeg()}")
        return
    app = DafanApp()
    app.mainloop()


if __name__ == "__main__":
    main()
