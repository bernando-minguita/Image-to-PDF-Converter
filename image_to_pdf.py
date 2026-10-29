"""
Image to PDF Converter — modern Tkinter desktop app
Python 3.10+
Dependency: Pillow (PIL)

Run:
    python image_to_pdf.py

Notes:
- Uses Pillow to convert common image formats into a multi-page PDF.
- Drag-and-drop is not required; use Add Images / Add Folder.
- All conversion is local; files are not uploaded anywhere.
"""
from __future__ import annotations

import os
import sys
import threading
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

if TYPE_CHECKING:
    from PIL import Image as _ImageType, ImageOps as _ImageOpsType, ImageTk as _ImageTkType
    ImageType = _ImageType.Image
    PhotoImageType = _ImageTkType.PhotoImage
else:
    ImageType = Any
    PhotoImageType = Any

try:
    from PIL import Image, ImageOps, ImageTk
except ImportError:
    Image = ImageOps = ImageTk = None


APP_TITLE = "Image to PDF"
BG = "#F4F7FB"
CARD = "#FFFFFF"
INK = "#172033"
MUTED = "#667085"
ACCENT = "#4F46E5"
ACCENT_HOVER = "#4338CA"
BORDER = "#E3E8F0"
GREEN = "#12805C"
RED = "#C0392B"


def format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def open_file(path: str) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        messagebox.showerror("Could not open file", str(exc))


class ImageToPDFApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1050x820")
        self.root.minsize(850, 620)
        self.root.configure(bg=BG)

        assert ImageTk is not None
        self.files: list[Path] = []
        self.preview_refs: list[PhotoImageType] = []
        self.output_var = tk.StringVar(value=str(Path.home() / "Pictures" / "converted_images.pdf"))
        self.page_size_var = tk.StringVar(value="Fit to image")
        self.orientation_var = tk.StringVar(value="Auto")
        self.margin_var = tk.StringVar(value="0")
        self.quality_var = tk.StringVar(value="High")
        self.convert_mode_var = tk.StringVar(value="merge")
        self.status_var = tk.StringVar(value="Add images to get started.")
        self.progress_var = tk.DoubleVar(value=0)

        self._setup_style()
        self._build_ui()
        self._refresh_list()
        self._center_window()

    def _center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", background=CARD, fieldbackground=CARD,
                        foreground=INK, rowheight=34, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#EEF2F7", foreground=INK,
                        font=("Segoe UI Semibold", 9), relief="flat")
        style.map("Treeview", background=[("selected", "#E8E9FF")],
                  foreground=[("selected", INK)])
        style.configure("TCombobox", padding=7, font=("Segoe UI", 10))
        style.configure("Horizontal.TProgressbar", troughcolor="#E9EDF5",
                        background=ACCENT, bordercolor="#E9EDF5", lightcolor=ACCENT,
                        darkcolor=ACCENT)

    def _button(self, parent, text, command, primary=False, width=None):
        btn = tk.Button(
            parent, text=text, command=command,
            bg=ACCENT if primary else CARD,
            fg="white" if primary else INK,
            activebackground=ACCENT_HOVER if primary else "#F1F4F9",
            activeforeground="white" if primary else INK,
            relief="flat", bd=0, cursor="hand2",
            font=("Segoe UI Semibold", 10), padx=15, pady=10,
        )
        if width is not None:
            btn.configure(width=width)
        return btn

    def _card(self, parent, **kwargs):
        return tk.Frame(parent, bg=CARD, highlightbackground=BORDER,
                        highlightthickness=1, **kwargs)

    def _build_ui(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=28, pady=(24, 16))
        title_area = tk.Frame(header, bg=BG)
        title_area.pack(side="left", fill="x", expand=True)
        tk.Label(title_area, text="Image to PDF", bg=BG, fg=INK,
                 font=("Segoe UI Semibold", 25)).pack(anchor="w")
        tk.Label(title_area, text="Combine images into a clean, shareable PDF — right on your computer.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))
        tk.Label(header, text="●  LOCAL & PRIVATE", bg="#E5F6EF", fg=GREEN,
                 font=("Segoe UI Semibold", 9), padx=12, pady=8).pack(side="right", anchor="n")

        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=28, pady=(0, 16))
        main.grid_columnconfigure(0, weight=7)
        main.grid_columnconfigure(1, weight=4)
        main.grid_rowconfigure(0, weight=1)

        # Left: image list
        left = self._card(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        left.grid_rowconfigure(2, weight=1)
        left.grid_columnconfigure(0, weight=1)

        list_head = tk.Frame(left, bg=CARD)
        list_head.grid(row=0, column=0, sticky="ew", padx=18, pady=(17, 10))
        tk.Label(list_head, text="Your images", bg=CARD, fg=INK,
                 font=("Segoe UI Semibold", 14)).pack(side="left")
        self.count_label = tk.Label(list_head, text="0 files", bg="#F0F2F7", fg=MUTED,
                                    font=("Segoe UI Semibold", 9), padx=9, pady=4)
        self.count_label.pack(side="left", padx=10)

        actions = tk.Frame(left, bg=CARD)
        actions.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        self._button(actions, "+ Add images", self.add_images, primary=True).pack(side="left")
        self._button(actions, "Add folder", self.add_folder).pack(side="left", padx=(8, 0))
        self._button(actions, "Remove", self.remove_selected).pack(side="right")
        self._button(actions, "Clear all", self.clear_all).pack(side="right", padx=(0, 8))

        tree_frame = tk.Frame(left, bg=CARD)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 8))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        columns = ("name", "dimensions", "size")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("name", text="FILE NAME")
        self.tree.heading("dimensions", text="DIMENSIONS")
        self.tree.heading("size", text="SIZE")
        self.tree.column("name", width=280, anchor="w")
        self.tree.column("dimensions", width=110, anchor="center")
        self.tree.column("size", width=90, anchor="e")
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Delete>", lambda _e: self.remove_selected())
        self.tree.bind("<Control-Up>", lambda _e: self._move_selected_key(-1))
        self.tree.bind("<Control-Down>", lambda _e: self._move_selected_key(1))

        order_row = tk.Frame(left, bg=CARD)
        order_row.grid(row=3, column=0, sticky="ew", padx=18, pady=(4, 16))
        tk.Label(order_row, text="PDF page order follows this list.", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="left")
        self._button(order_row, "↑", lambda: self.move_selected(-1), width=3).pack(side="right", padx=(5, 0))
        self._button(order_row, "↓", lambda: self.move_selected(1), width=3).pack(side="right")

        # Right: settings
        right = self._card(main)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        tk.Label(right, text="PDF settings", bg=CARD, fg=INK,
                 font=("Segoe UI Semibold", 14)).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 14))

        settings = tk.Frame(right, bg=CARD)
        settings.grid(row=1, column=0, sticky="ew", padx=18)
        settings.grid_columnconfigure(0, weight=1)

        self._setting_label(settings, "PAGE SIZE", 0)
        self.page_combo = ttk.Combobox(settings, textvariable=self.page_size_var, state="readonly",
                                       values=("Fit to image", "A4", "Letter", "A3"))
        self.page_combo.grid(row=1, column=0, sticky="ew", pady=(5, 13))

        self._setting_label(settings, "ORIENTATION", 2)
        self.orientation_combo = ttk.Combobox(settings, textvariable=self.orientation_var, state="readonly",
                                              values=("Auto", "Portrait", "Landscape"))
        self.orientation_combo.grid(row=3, column=0, sticky="ew", pady=(5, 13))

        self._setting_label(settings, "MARGIN", 4)
        margin_row = tk.Frame(settings, bg=CARD)
        margin_row.grid(row=5, column=0, sticky="ew", pady=(5, 13))
        self.margin_combo = ttk.Combobox(margin_row, textvariable=self.margin_var, state="readonly",
                                         values=("0", "5", "10", "15", "20"))
        self.margin_combo.pack(side="left", fill="x", expand=True)
        tk.Label(margin_row, text="mm", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", padx=(8, 0))

        self._setting_label(settings, "IMAGE QUALITY", 6)
        self.quality_combo = ttk.Combobox(settings, textvariable=self.quality_var, state="readonly",
                                          values=("High", "Balanced", "Smaller file"))
        self.quality_combo.grid(row=7, column=0, sticky="ew", pady=(5, 13))

        self._setting_label(settings, "CONVERSION MODE", 8)
        mode_row = tk.Frame(settings, bg=CARD)
        mode_row.grid(row=9, column=0, sticky="ew", pady=(5, 13))
        tk.Radiobutton(
            mode_row, text="Merge all into one PDF", variable=self.convert_mode_var,
            value="merge", bg=CARD, fg=INK, selectcolor=CARD, activebackground=CARD,
            command=self._toggle_output_mode).pack(side="left")
        tk.Radiobutton(
            mode_row, text="Save each image as a separate PDF", variable=self.convert_mode_var,
            value="per_file", bg=CARD, fg=INK, selectcolor=CARD, activebackground=CARD,
            command=self._toggle_output_mode).pack(side="left", padx=(16, 0))

        separator = tk.Frame(right, bg=BORDER, height=1)
        separator.grid(row=2, column=0, sticky="ew", padx=18, pady=(5, 16))
        self.output_label = tk.Label(right, text="OUTPUT FILE", bg=CARD, fg=INK,
                 font=("Segoe UI Semibold", 9))
        self.output_label.grid(row=3, column=0, sticky="w", padx=18)
        out_row = tk.Frame(right, bg=CARD)
        out_row.grid(row=4, column=0, sticky="ew", padx=18, pady=(7, 16))
        out_row.grid_columnconfigure(0, weight=1)
        self.output_entry = tk.Entry(out_row, textvariable=self.output_var, relief="solid",
                                     bd=1, bg="#FBFCFE", fg=INK, insertbackground=INK,
                                     font=("Segoe UI", 9))
        self.output_entry.grid(row=0, column=0, sticky="ew", ipady=8)
        self.browse_button = self._button(out_row, "Browse", self.choose_output)
        self.browse_button.grid(row=0, column=1, padx=(7, 0))

        self.convert_button = self._button(right, "Convert to PDF  →", self.convert, primary=True)
        self.convert_button.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 10), ipady=3)
        self.progress = ttk.Progressbar(right, variable=self.progress_var, maximum=100, mode="determinate")
        self.progress.grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 8))
        self.status_label = tk.Label(right, textvariable=self.status_var, bg=CARD, fg=MUTED,
                                     font=("Segoe UI", 9), wraplength=300, justify="left")
        self.status_label.grid(row=7, column=0, sticky="ew", padx=18, pady=(0, 10))
        self.open_button = self._button(right, "Open output PDF", self.open_output)
        self.open_button.grid(row=8, column=0, sticky="ew", padx=18, pady=(0, 18))
        self.open_button.configure(state="disabled")

        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="x", padx=28, pady=(0, 16))
        tk.Label(footer, text="Supports JPG, JPEG, PNG, BMP, TIFF, WEBP and other Pillow-readable images.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        tk.Label(footer, text="Tip: select files and use Ctrl + ↑ / Ctrl + ↓ to reorder.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="right")

    def _setting_label(self, parent, text, row):
        tk.Label(parent, text=text, bg=CARD, fg=MUTED,
                 font=("Segoe UI Semibold", 8)).grid(row=row, column=0, sticky="w")

    def add_images(self):
        paths = filedialog.askopenfilenames(
            title="Choose images",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp *.gif"),
                       ("All files", "*.*")]
        )
        if paths:
            self._add_paths([Path(p) for p in paths])

    def add_folder(self):
        folder = filedialog.askdirectory(title="Choose a folder containing images")
        if not folder:
            return
        allowed = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".gif"}
        paths = sorted((p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in allowed),
                       key=lambda p: p.name.lower())
        if not paths:
            messagebox.showinfo("No images found", "That folder does not contain supported image files.")
            return
        self._add_paths(paths)

    def _add_paths(self, paths: list[Path]):
        assert Image is not None
        existing = {str(p.resolve()).lower() for p in self.files}
        added = 0
        for path in paths:
            try:
                resolved = path.resolve()
                if not resolved.is_file() or str(resolved).lower() in existing:
                    continue
                # Validate that Pillow can open it before adding.
                with Image.open(resolved) as img:
                    img.verify()
                self.files.append(resolved)
                existing.add(str(resolved).lower())
                added += 1
            except Exception:
                continue
        self._refresh_list()
        if added == 0 and paths:
            messagebox.showwarning("No supported images added",
                                   "The selected files were unsupported, unreadable, or already in the list.")

    def _refresh_list(self):
        assert Image is not None
        for item in self.tree.get_children():
            self.tree.delete(item)
        for index, path in enumerate(self.files):
            try:
                with Image.open(path) as img:
                    dimensions = f"{img.width} × {img.height}"
                size = format_size(path.stat().st_size)
            except Exception:
                dimensions, size = "Unavailable", "—"
            self.tree.insert("", "end", iid=str(index), values=(path.name, dimensions, size))
        total_size = sum(p.stat().st_size for p in self.files if p.exists())
        self.count_label.configure(text=f"{len(self.files)} file" + ("" if len(self.files) == 1 else "s"))
        if self.files:
            self.status_var.set(f"{len(self.files)} image(s) ready • {format_size(total_size)} total")
        else:
            self.status_var.set("Add images to get started.")
        self.progress_var.set(0)

    def remove_selected(self):
        selected = sorted((int(i) for i in self.tree.selection()), reverse=True)
        for index in selected:
            if 0 <= index < len(self.files):
                del self.files[index]
        self._refresh_list()

    def clear_all(self):
        if not self.files:
            return
        if messagebox.askyesno("Clear image list", "Remove all images from the list?"):
            self.files.clear()
            self._refresh_list()

    def _move_selected_key(self, direction: int):
        self.move_selected(direction)
        return "break"

    def move_selected(self, direction: int):
        selected = sorted(int(i) for i in self.tree.selection())
        if not selected:
            return

        # Remember the originally selected items so we can re-select them after the move.
        original_items = [self.files[i] for i in selected]

        if direction < 0:
            # Move up: process ascending so each item shifts toward the top.
            for i in selected:
                if i > 0:
                    self.files[i - 1], self.files[i] = self.files[i], self.files[i - 1]
        else:
            # Move down: process descending so each item shifts toward the bottom.
            for i in reversed(selected):
                if i < len(self.files) - 1:
                    self.files[i + 1], self.files[i] = self.files[i], self.files[i + 1]

        self._refresh_list()

        # Re-select the originally selected items at their new positions.
        new_indices = []
        for item in original_items:
            try:
                new_index = self.files.index(item)
                new_indices.append(new_index)
            except ValueError:
                pass

        # Replace the entire selection so the highlight is exactly on moved rows.
        if new_indices:
            self.tree.selection_set()
            self.tree.selection_set(*[str(i) for i in new_indices])
            first = str(new_indices[0])
            self.tree.focus(first)
            self.tree.see(first)

    def choose_output(self):
        current = self.output_var.get().strip()
        initial_dir = str(Path(current).parent) if current else str(Path.home())
        if self.convert_mode_var.get() == "per_file":
            path = filedialog.askdirectory(title="Choose output folder", initialdir=initial_dir)
            if path:
                self.output_var.set(path)
        else:
            initial_name = Path(current).name if current else "converted_images.pdf"
            path = filedialog.asksaveasfilename(
                title="Save PDF as", defaultextension=".pdf", initialdir=initial_dir,
                initialfile=initial_name, filetypes=[("PDF document", "*.pdf")]
            )
            if path:
                if not path.lower().endswith(".pdf"):
                    path += ".pdf"
                self.output_var.set(path)

    def _page_dimensions(self, image: ImageType):
        # Dimensions are in PDF points (72 points per inch).
        page_size = self.page_size_var.get()
        orientation = self.orientation_var.get()
        margin_pt = float(self.margin_var.get()) * 72 / 25.4
        if page_size == "Fit to image":
            width, height = image.size
            # Scale pixels to 72 dpi points, capped to a sensible large page.
            width_pt, height_pt = width * 72 / 150, height * 72 / 150
        else:
            sizes = {
                "A4": (595.28, 841.89),
                "Letter": (612.0, 792.0),
                "A3": (841.89, 1190.55),
            }
            width_pt, height_pt = sizes[page_size]
        if orientation == "Landscape" and height_pt > width_pt:
            width_pt, height_pt = height_pt, width_pt
        elif orientation == "Portrait" and width_pt > height_pt:
            width_pt, height_pt = height_pt, width_pt
        return width_pt, height_pt, margin_pt

    def _toggle_output_mode(self):
        mode = self.convert_mode_var.get()
        current = self.output_var.get().strip()
        if mode == "per_file":
            self.output_label.configure(text="OUTPUT FOLDER")
            self.browse_button.configure(text="Browse folder")
            self.convert_button.configure(text="Convert each to PDF  →")
            # Keep only a directory path; drop any filename.
            if current:
                p = Path(current)
                if p.suffix.lower() == ".pdf" or not p.exists():
                    self.output_var.set(str(p.parent))
        else:
            self.output_label.configure(text="OUTPUT FILE")
            self.browse_button.configure(text="Browse")
            self.convert_button.configure(text="Convert to PDF  →")
            # Ensure a PDF filename is present.
            if current:
                p = Path(current)
                if p.suffix.lower() != ".pdf":
                    self.output_var.set(str(p / "converted_images.pdf"))
            else:
                self.output_var.set(str(Path.home() / "Pictures" / "converted_images.pdf"))

    def convert(self):
        if not self.files:
            messagebox.showinfo("No images", "Add at least one image before converting.")
            return
        output = Path(self.output_var.get().strip()).expanduser()
        if not str(output) or not output.name:
            messagebox.showerror("Output required", "Choose an output PDF filename.")
            return
        if any(not p.exists() for p in self.files):
            messagebox.showerror("Missing image", "One or more source images no longer exist. Remove them and try again.")
            return
        mode = self.convert_mode_var.get()
        if mode == "merge":
            if output.suffix.lower() != ".pdf":
                output = output.with_suffix(".pdf")
                self.output_var.set(str(output))
            if output.exists() and not messagebox.askyesno("Overwrite PDF?",
                    f"The file already exists:\n{output}\n\nReplace it?"):
                return
            try:
                output.parent.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                messagebox.showerror("Output folder error", str(exc))
                return
        else:
            try:
                output.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                messagebox.showerror("Output folder error", str(exc))
                return

        self.convert_button.configure(state="disabled", text="Converting…")
        self.progress_var.set(0)
        self.status_var.set("Preparing images…")
        files_snapshot = list(self.files)
        settings = (self.convert_mode_var.get(), self.page_size_var.get(),
                    self.orientation_var.get(), self.margin_var.get(), self.quality_var.get())
        threading.Thread(target=self._convert_worker,
                         args=(files_snapshot, output, settings), daemon=True).start()

    def _convert_worker(self, files: list[Path], output: Path, settings):
        mode, page_size, orientation, margin, quality = settings
        if mode == "per_file":
            self._convert_per_file_worker(files, output, page_size, orientation, margin, quality)
            return
        assert Image is not None
        assert ImageOps is not None
        temp_path = output.with_name(output.stem + ".tmp.pdf")
        try:
            converted: list[ImageType] = []
            for index, path in enumerate(files, start=1):
                with Image.open(path) as opened:
                    frame = ImageOps.exif_transpose(opened)
                    # GIF/TIFF can contain multiple frames; convert the first frame only.
                    try:
                        frame.seek(0)
                    except Exception:
                        pass
                    frame = frame.convert("RGB")
                    width_pt, height_pt, margin_pt = self._page_dimensions_for(frame, page_size, orientation, margin)
                    available_w = max(1, width_pt - 2 * margin_pt)
                    available_h = max(1, height_pt - 2 * margin_pt)
                    scale = min(available_w / frame.width, available_h / frame.height)
                    if page_size == "Fit to image":
                        # Keep each image's natural aspect ratio and use an image-sized page.
                        width_pt, height_pt = frame.width * 72 / 150, frame.height * 72 / 150
                        margin_pt = float(margin) * 72 / 25.4
                        available_w = max(1, width_pt - 2 * margin_pt)
                        available_h = max(1, height_pt - 2 * margin_pt)
                        scale = min(available_w / frame.width, available_h / frame.height)
                    target_w = max(1, round(frame.width * scale))
                    target_h = max(1, round(frame.height * scale))
                    if quality == "Smaller file":
                        frame.thumbnail((max(1, int(target_w * 0.75)), max(1, int(target_h * 0.75))), Image.Resampling.LANCZOS)
                    elif quality == "Balanced":
                        frame.thumbnail((max(1, int(target_w * 0.9)), max(1, int(target_h * 0.9))), Image.Resampling.LANCZOS)
                    # Save page geometry on image info for PDF assembly.
                    frame.info["pdf_page_size"] = (width_pt, height_pt, margin_pt)
                    converted.append(frame.copy())
                self.root.after(0, self._set_progress, index / len(files) * 75,
                                f"Processing image {index} of {len(files)}…")

            if not converted:
                raise RuntimeError("No valid images were converted.")
            # Pillow's PDF writer uses the first image's resolution to set page geometry.
            # To preserve mixed page dimensions, use Pillow's multi-page PDF support; for
            # fixed paper sizes, normalize every image to a white page canvas first.
            pages = []
            for img in converted:
                width_pt, height_pt, margin_pt = img.info.get("pdf_page_size", (img.width * 72 / 150, img.height * 72 / 150, 0))
                page_size_name = page_size
                if page_size_name != "Fit to image":
                    canvas_w = max(1, round(width_pt * 150 / 72))
                    canvas_h = max(1, round(height_pt * 150 / 72))
                    margin_px = round(margin_pt * 150 / 72)
                    canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
                    scale = min(max(1, canvas_w - 2 * margin_px) / img.width,
                                max(1, canvas_h - 2 * margin_px) / img.height)
                    resized = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.Resampling.LANCZOS)
                    x = (canvas_w - resized.width) // 2
                    y = (canvas_h - resized.height) // 2
                    canvas.paste(resized, (x, y))
                    pages.append(canvas)
                else:
                    pages.append(img)
            save_kwargs: dict[str, Any] = {"format": "PDF", "save_all": True, "append_images": pages[1:]}
            if quality == "High":
                save_kwargs["resolution"] = 150.0
            elif quality == "Balanced":
                save_kwargs["resolution"] = 120.0
            else:
                save_kwargs["resolution"] = 96.0
            pages[0].save(temp_path, **save_kwargs)
            os.replace(temp_path, output)
            self.root.after(0, self._conversion_done, str(output), len(files))
        except Exception as exc:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass
            self.root.after(0, self._conversion_failed, str(exc))
        finally:
            for img in locals().get("converted", []):
                try:
                    img.close()
                except Exception:
                    pass

    def _convert_per_file_worker(self, files: list[Path], output_dir: Path,
                                 page_size: str, orientation: str, margin: str, quality: str):
        assert Image is not None
        assert ImageOps is not None
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            total = len(files)
            success = 0
            failed: list[tuple[str, str]] = []
            for index, path in enumerate(files, start=1):
                try:
                    out_path = output_dir / (path.stem + ".pdf")
                    counter = 1
                    while out_path.exists():
                        out_path = output_dir / f"{path.stem} ({counter}).pdf"
                        counter += 1
                    with Image.open(path) as opened:
                        frame = self._prepare_frame(opened, page_size, orientation, margin, quality)
                        width_pt, height_pt, margin_pt = frame.info.get(
                            "pdf_page_size", (frame.width * 72 / 150, frame.height * 72 / 150, 0))
                        if page_size != "Fit to image":
                            canvas_w = max(1, round(width_pt * 150 / 72))
                            canvas_h = max(1, round(height_pt * 150 / 72))
                            margin_px = round(margin_pt * 150 / 72)
                            canvas = Image.new("RGB", (canvas_w, canvas_h), "white")
                            scale = min(max(1, canvas_w - 2 * margin_px) / frame.width,
                                        max(1, canvas_h - 2 * margin_px) / frame.height)
                            resized = frame.resize((max(1, round(frame.width * scale)),
                                                    max(1, round(frame.height * scale))), Image.Resampling.LANCZOS)
                            x = (canvas_w - resized.width) // 2
                            y = (canvas_h - resized.height) // 2
                            canvas.paste(resized, (x, y))
                            img_to_save = canvas
                        else:
                            img_to_save = frame
                        save_kwargs: dict[str, Any] = {"format": "PDF"}
                        if quality == "High":
                            save_kwargs["resolution"] = 150.0
                        elif quality == "Balanced":
                            save_kwargs["resolution"] = 120.0
                        else:
                            save_kwargs["resolution"] = 96.0
                        img_to_save.save(out_path, **save_kwargs)
                        if img_to_save is not frame:
                            try:
                                img_to_save.close()
                            except Exception:
                                pass
                    success += 1
                except Exception as exc:
                    failed.append((path.name, str(exc)))
                self.root.after(0, self._set_progress, index / total * 100,
                                f"Converting {index} of {total}…")
            self.root.after(0, self._conversion_per_file_done, success, failed, str(output_dir))
        except Exception as exc:
            self.root.after(0, self._conversion_failed, str(exc))

    def _prepare_frame(self, opened: ImageType, page_size: str, orientation: str, margin: str,
                       quality: str) -> ImageType:
        assert Image is not None
        assert ImageOps is not None
        frame = ImageOps.exif_transpose(opened)
        try:
            frame.seek(0)
        except Exception:
            pass
        frame = frame.convert("RGB")
        width_pt, height_pt, margin_pt = self._page_dimensions_for(frame, page_size, orientation, margin)
        available_w = max(1, width_pt - 2 * margin_pt)
        available_h = max(1, height_pt - 2 * margin_pt)
        scale = min(available_w / frame.width, available_h / frame.height)
        if page_size == "Fit to image":
            width_pt, height_pt = frame.width * 72 / 150, frame.height * 72 / 150
            margin_pt = float(margin) * 72 / 25.4
            available_w = max(1, width_pt - 2 * margin_pt)
            available_h = max(1, height_pt - 2 * margin_pt)
            scale = min(available_w / frame.width, available_h / frame.height)
        target_w = max(1, round(frame.width * scale))
        target_h = max(1, round(frame.height * scale))
        if quality == "Smaller file":
            frame.thumbnail((max(1, int(target_w * 0.75)), max(1, int(target_h * 0.75))), Image.Resampling.LANCZOS)
        elif quality == "Balanced":
            frame.thumbnail((max(1, int(target_w * 0.9)), max(1, int(target_h * 0.9))), Image.Resampling.LANCZOS)
        frame.info["pdf_page_size"] = (width_pt, height_pt, margin_pt)
        return frame

    def _conversion_per_file_done(self, success: int, failed: list[tuple[str, str]], output_dir: str):
        self.convert_button.configure(state="normal")
        mode = self.convert_mode_var.get()
        self.convert_button.configure(text="Convert each to PDF  →" if mode == "per_file" else "Convert to PDF  →")
        self.progress_var.set(100)
        if failed:
            self.status_var.set(f"Finished with errors: {success} saved, {len(failed)} failed.")
            self.status_label.configure(fg=RED)
            detail = "\n".join(f"{name}: {err}" for name, err in failed[:10])
            messagebox.showwarning(
                "Conversion complete with errors",
                f"Saved {success} PDF(s) to:\n{output_dir}\n\n{len(failed)} failed:\n{detail}")
        else:
            self.status_var.set(f"Done! Saved {success} PDF(s) to {output_dir}.")
            self.status_label.configure(fg=GREEN)
            messagebox.showinfo("Conversion complete", f"Saved {success} PDF(s) successfully to:\n{output_dir}")
        self.open_button.configure(state="normal")

    @staticmethod
    def _page_dimensions_for(image, page_size, orientation, margin):
        margin_pt = float(margin) * 72 / 25.4
        if page_size == "Fit to image":
            width_pt, height_pt = image.width * 72 / 150, image.height * 72 / 150
        else:
            width_pt, height_pt = {
                "A4": (595.28, 841.89), "Letter": (612.0, 792.0), "A3": (841.89, 1190.55)
            }[page_size]
        if orientation == "Landscape" and height_pt > width_pt:
            width_pt, height_pt = height_pt, width_pt
        elif orientation == "Portrait" and width_pt > height_pt:
            width_pt, height_pt = height_pt, width_pt
        return width_pt, height_pt, margin_pt

    def _set_progress(self, value, message):
        self.progress_var.set(value)
        self.status_var.set(message)

    def _conversion_done(self, output, count):
        self.convert_button.configure(state="normal", text="Convert to PDF  →")
        self.progress_var.set(100)
        self.status_var.set(f"Done! Created {Path(output).name} from {count} image(s).")
        self.status_label.configure(fg=GREEN)
        self.open_button.configure(state="normal")
        messagebox.showinfo("Conversion complete", f"PDF created successfully:\n{output}")

    def _conversion_failed(self, error):
        self.convert_button.configure(state="normal", text="Convert to PDF  →")
        self.status_var.set("Conversion failed.")
        self.status_label.configure(fg=RED)
        messagebox.showerror("Conversion failed", error)

    def open_output(self):
        output = self.output_var.get().strip()
        if not output:
            messagebox.showinfo("Nothing to open", "Convert the images first, then open the output.")
            return
        path = Path(output)
        if self.convert_mode_var.get() == "per_file":
            if path.exists():
                open_file(str(path))
            else:
                messagebox.showinfo("Folder not found", "Convert the images first, then open the output folder.")
        else:
            if path.exists():
                open_file(output)
            else:
                messagebox.showinfo("PDF not found", "Convert the images first, then open the output PDF.")


def main():
    if Image is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Pillow is required",
            "The Pillow package is not installed.\n\nInstall it with:\n"
            "py -m pip install Pillow\n\n"
            "Then run the app using the included run_app.bat."
        )
        root.destroy()
        return
    root = tk.Tk()
    app = ImageToPDFApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
