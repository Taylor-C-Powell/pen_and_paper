import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog
import json
import os


class DrawingCanvas(tk.Canvas):
    """White drawing surface with mouse bindings for freehand drawing/erasing."""

    def __init__(self, parent, app):
        super().__init__(parent, bg="white", cursor="crosshair")
        self.app = app
        self._last_x = None
        self._last_y = None
        self._action_started = False

        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_press(self, event):
        self._last_x = event.x
        self._last_y = event.y
        self._action_started = False
        if self.app.current_tool == "pencil":
            self._save_undo_snapshot()
            r = self.app.brush_size / 2
            self.create_oval(
                event.x - r, event.y - r, event.x + r, event.y + r,
                fill=self.app.current_color, outline=self.app.current_color,
                tags="drawing",
            )
            self.app.modified = True
            self._action_started = True
        elif self.app.current_tool == "eraser":
            self._save_undo_snapshot()
            self._action_started = True
        elif self.app.current_tool == "fill":
            self._save_undo_snapshot()
            w = self.winfo_width()
            h = self.winfo_height()
            rect = self.create_rectangle(
                0, 0, w, h,
                fill=self.app.current_color, outline=self.app.current_color,
                tags="drawing",
            )
            self.tag_lower(rect)
            self.app.modified = True
            self._action_started = True

    def _on_drag(self, event):
        if self.app.current_tool == "pencil":
            self.create_line(
                self._last_x, self._last_y, event.x, event.y,
                fill=self.app.current_color,
                width=self.app.brush_size,
                capstyle=tk.ROUND,
                smooth=True,
                tags="drawing",
            )
            self.app.modified = True
        elif self.app.current_tool == "eraser":
            r = self.app.brush_size * 2
            overlapping = self.find_overlapping(
                event.x - r, event.y - r, event.x + r, event.y + r
            )
            for item_id in overlapping:
                self.delete(item_id)
            if overlapping:
                self.app.modified = True
        self._last_x = event.x
        self._last_y = event.y

    def _on_release(self, event):
        self._last_x = None
        self._last_y = None
        self._action_started = False
        self.app.update_status_bar()

    def _save_undo_snapshot(self):
        """Save current canvas state to undo stack before a new action."""
        snapshot = self.serialize()
        self.app.undo_stack.append(snapshot)
        # Limit stack size to prevent unbounded memory growth
        if len(self.app.undo_stack) > 50:
            self.app.undo_stack.pop(0)
        # New action invalidates redo history
        self.app.redo_stack.clear()

    def get_fill_percentage(self):
        """Estimate how much of the canvas is filled using bounding box area."""
        items = self.find_all()
        if not items:
            return 0.0
        canvas_w = self.winfo_width()
        canvas_h = self.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            return 0.0
        canvas_area = canvas_w * canvas_h
        filled_pixels = set()
        for item_id in items:
            bbox = self.bbox(item_id)
            if bbox:
                x1, y1, x2, y2 = bbox
                # Clamp to canvas bounds
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(canvas_w, x2)
                y2 = min(canvas_h, y2)
                # Sample the bounding box area (approximate)
                filled_pixels.add((x1, y1, x2, y2))
        # Union of bounding box areas (simple approximation)
        total_area = 0
        for x1, y1, x2, y2 in filled_pixels:
            total_area += (x2 - x1) * (y2 - y1)
        # Cap at 100%
        percentage = min(100.0, (total_area / canvas_area) * 100)
        return percentage

    def serialize(self):
        """Serialize all canvas items to a list of dicts."""
        data = []
        for item_id in self.find_all():
            item_type = self.type(item_id)
            coords = self.coords(item_id)
            config = {}
            if item_type == "line":
                config["fill"] = self.itemcget(item_id, "fill")
                config["width"] = float(self.itemcget(item_id, "width"))
                config["capstyle"] = self.itemcget(item_id, "capstyle")
            elif item_type == "oval":
                config["fill"] = self.itemcget(item_id, "fill")
                config["outline"] = self.itemcget(item_id, "outline")
            elif item_type == "rectangle":
                config["fill"] = self.itemcget(item_id, "fill")
                config["outline"] = self.itemcget(item_id, "outline")
            data.append({
                "type": item_type,
                "coords": coords,
                "config": config,
            })
        return data

    def deserialize(self, data):
        """Restore canvas items from serialized data."""
        self.delete("all")
        for item in data:
            item_type = item["type"]
            coords = item["coords"]
            config = item.get("config", {})
            if item_type == "line":
                self.create_line(
                    *coords,
                    fill=config.get("fill", "black"),
                    width=config.get("width", 2),
                    capstyle=config.get("capstyle", tk.ROUND),
                    smooth=True,
                    tags="drawing",
                )
            elif item_type == "oval":
                self.create_oval(
                    *coords,
                    fill=config.get("fill", "black"),
                    outline=config.get("outline", "black"),
                    tags="drawing",
                )
            elif item_type == "rectangle":
                self.create_rectangle(
                    *coords,
                    fill=config.get("fill", "black"),
                    outline=config.get("outline", "black"),
                    tags="drawing",
                )


class Toolbar(tk.Frame):
    """Toolbar with Pencil, Eraser, Fill, Color Picker, and Brush Size slider."""

    def __init__(self, parent, app):
        super().__init__(parent, bg="#d9d9d9", padx=2, pady=2)
        self.app = app

        self.pencil_btn = tk.Button(
            self, text="Pencil", width=6, relief=tk.SUNKEN,
            command=lambda: self.select_tool("pencil"),
        )
        self.pencil_btn.pack(side=tk.LEFT, padx=(2, 1))

        self.eraser_btn = tk.Button(
            self, text="Eraser", width=6, relief=tk.RAISED,
            command=lambda: self.select_tool("eraser"),
        )
        self.eraser_btn.pack(side=tk.LEFT, padx=(1, 1))

        self.fill_btn = tk.Button(
            self, text="Fill", width=6, relief=tk.RAISED,
            command=lambda: self.select_tool("fill"),
        )
        self.fill_btn.pack(side=tk.LEFT, padx=(1, 4))

        # Separator
        sep = tk.Frame(self, width=2, bg="#a0a0a0")
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)

        self.color_btn = tk.Button(
            self, text="Color Picker", width=20, bg=app.current_color,
            fg="white", relief=tk.RAISED,
            command=self._pick_color,
        )
        self.color_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 2))

        # Separator
        sep2 = tk.Frame(self, width=2, bg="#a0a0a0")
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=2, pady=2)

        # Brush size slider
        size_label = tk.Label(self, text="Size:", bg="#d9d9d9")
        size_label.pack(side=tk.LEFT, padx=(4, 0))

        self.size_var = tk.IntVar(value=app.brush_size)
        self.size_slider = tk.Scale(
            self, from_=1, to=50, orient=tk.HORIZONTAL,
            variable=self.size_var, length=120, showvalue=True,
            bg="#d9d9d9", highlightthickness=0,
            command=self._on_size_change,
        )
        self.size_slider.pack(side=tk.LEFT, padx=(0, 2))

    def _on_size_change(self, value):
        self.app.brush_size = int(value)

    def select_tool(self, tool):
        self.app.current_tool = tool
        self.pencil_btn.config(relief=tk.RAISED)
        self.eraser_btn.config(relief=tk.RAISED)
        self.fill_btn.config(relief=tk.RAISED)
        if tool == "pencil":
            self.pencil_btn.config(relief=tk.SUNKEN)
            self.app.canvas.config(cursor="crosshair")
        elif tool == "eraser":
            self.eraser_btn.config(relief=tk.SUNKEN)
            self.app.canvas.config(cursor="circle")
        elif tool == "fill":
            self.fill_btn.config(relief=tk.SUNKEN)
            self.app.canvas.config(cursor="target")

    def _pick_color(self):
        color = colorchooser.askcolor(
            initialcolor=self.app.current_color, title="Pick a Color"
        )
        if color[1]:
            self.app.current_color = color[1]
            self.color_btn.config(bg=color[1])
            # Adjust text color for readability
            r, g, b = color[0]
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            self.color_btn.config(fg="black" if brightness > 128 else "white")

    def update_color_display(self):
        """Refresh the color button to match current app color."""
        self.color_btn.config(bg=self.app.current_color)


class StatusBar(tk.Frame):
    """Footer showing filename (left) and % filled (right)."""

    def __init__(self, parent, app):
        super().__init__(parent, bg="#c0c0c0", bd=1, relief=tk.SUNKEN)
        self.app = app

        self.filename_label = tk.Label(
            self, text="Untitled", bg="#c0c0c0", anchor=tk.W, padx=8,
        )
        self.filename_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.fill_label = tk.Label(
            self, text="0.0% filled", bg="#c0c0c0", anchor=tk.E, padx=8,
        )
        self.fill_label.pack(side=tk.RIGHT)

    def update(self):
        """Refresh the status bar display."""
        if self.app.current_file:
            name = os.path.basename(self.app.current_file)
        else:
            name = "Untitled"
        if self.app.modified:
            name += " *"
        self.filename_label.config(text=name)
        pct = self.app.canvas.get_fill_percentage()
        self.fill_label.config(text=f"{pct:.1f}% filled")


class MenuBar(tk.Menu):
    """File menu and Options menu."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # File menu
        file_menu = tk.Menu(self, tearoff=0)
        file_menu.add_command(
            label="New", accelerator="Ctrl+N", command=app.file_new
        )
        file_menu.add_command(
            label="Open...", accelerator="Ctrl+O", command=app.file_open
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Save", accelerator="Ctrl+S", command=app.file_save
        )
        file_menu.add_command(
            label="Save As...", accelerator="Ctrl+Shift+S",
            command=app.file_save_as,
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=app.file_exit)
        self.add_cascade(label="File", menu=file_menu)

        # Edit menu
        edit_menu = tk.Menu(self, tearoff=0)
        edit_menu.add_command(
            label="Undo", accelerator="Ctrl+Z", command=app.undo
        )
        edit_menu.add_command(
            label="Redo", accelerator="Ctrl+Y", command=app.redo
        )
        self.add_cascade(label="Edit", menu=edit_menu)

        # Options menu
        options_menu = tk.Menu(self, tearoff=0)

        # Brush size submenu
        brush_menu = tk.Menu(options_menu, tearoff=0)
        brush_menu.add_command(
            label="Small (2px)", command=lambda: app.set_brush_size(2)
        )
        brush_menu.add_command(
            label="Medium (5px)", command=lambda: app.set_brush_size(5)
        )
        brush_menu.add_command(
            label="Large (10px)", command=lambda: app.set_brush_size(10)
        )
        brush_menu.add_separator()
        brush_menu.add_command(label="Custom...", command=app.custom_brush_size)
        options_menu.add_cascade(label="Brush Size", menu=brush_menu)

        options_menu.add_separator()
        options_menu.add_command(label="Clear Canvas", command=app.clear_canvas)
        self.add_cascade(label="Options", menu=options_menu)


class PenAndPaperApp(tk.Tk):
    """Root window for the Pen and Paper drawing application."""

    def __init__(self):
        super().__init__()
        self.title("Pen and Paper")
        self.geometry("800x600")
        self.configure(bg="#d9d9d9")

        # App state
        self.current_tool = "pencil"
        self.current_color = "#000000"
        self.brush_size = 2
        self.current_file = None
        self.modified = False
        self.undo_stack = []
        self.redo_stack = []

        # Build UI
        self._build_ui()
        self._bind_shortcuts()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.file_exit)

    def _build_ui(self):
        # Menu bar
        self.menu_bar = MenuBar(self, self)
        self.config(menu=self.menu_bar)

        # Toolbar
        self.toolbar = Toolbar(self, self)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        # Status bar (pack before canvas so it stays at the bottom)
        self.status_bar = StatusBar(self, self)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Canvas (fills remaining space)
        self.canvas = DrawingCanvas(self, self)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _bind_shortcuts(self):
        self.bind_all("<Control-n>", lambda e: self.file_new())
        self.bind_all("<Control-o>", lambda e: self.file_open())
        self.bind_all("<Control-s>", lambda e: self.file_save())
        self.bind_all("<Control-Shift-S>", lambda e: self.file_save_as())
        self.bind_all("<Control-z>", lambda e: self.undo())
        self.bind_all("<Control-y>", lambda e: self.redo())

    def update_status_bar(self):
        self.status_bar.update()

    def _update_title(self):
        name = os.path.basename(self.current_file) if self.current_file else "Untitled"
        mod = " *" if self.modified else ""
        self.title(f"{name}{mod} - Pen and Paper")

    # --- Brush size ---

    def set_brush_size(self, size):
        self.brush_size = size
        self.toolbar.size_var.set(size)

    def custom_brush_size(self):
        size = simpledialog.askinteger(
            "Brush Size", "Enter brush size (1-50):",
            initialvalue=self.brush_size, minvalue=1, maxvalue=50,
            parent=self,
        )
        if size is not None:
            self.brush_size = size

    # --- Undo / Redo ---

    def undo(self):
        if not self.undo_stack:
            return
        # Save current state to redo stack
        self.redo_stack.append(self.canvas.serialize())
        # Restore previous state
        snapshot = self.undo_stack.pop()
        self.canvas.deserialize(snapshot)
        self.modified = True
        self.update_status_bar()
        self._update_title()

    def redo(self):
        if not self.redo_stack:
            return
        # Save current state to undo stack
        self.undo_stack.append(self.canvas.serialize())
        # Restore next state
        snapshot = self.redo_stack.pop()
        self.canvas.deserialize(snapshot)
        self.modified = True
        self.update_status_bar()
        self._update_title()

    # --- Canvas operations ---

    def clear_canvas(self):
        if self.canvas.find_all():
            confirm = messagebox.askyesno(
                "Clear Canvas",
                "Are you sure you want to clear the canvas?",
                parent=self,
            )
            if not confirm:
                return
        self.canvas._save_undo_snapshot()
        self.canvas.delete("all")
        self.modified = True
        self.update_status_bar()
        self._update_title()

    # --- File operations ---

    def _check_unsaved(self):
        """Prompt user to save if there are unsaved changes.
        Returns True if it's OK to proceed, False to cancel."""
        if not self.modified:
            return True
        result = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved changes. Save before continuing?",
            parent=self,
        )
        if result is None:  # Cancel
            return False
        if result:  # Yes
            self.file_save()
            return not self.modified  # False if save was cancelled
        return True  # No (discard)

    def file_new(self):
        if not self._check_unsaved():
            return
        self.canvas.delete("all")
        self.current_file = None
        self.modified = False
        self.current_color = "#000000"
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.toolbar.update_color_display()
        self.toolbar.select_tool("pencil")
        self.update_status_bar()
        self._update_title()

    def file_open(self):
        if not self._check_unsaved():
            return
        filepath = filedialog.askopenfilename(
            title="Open Drawing",
            filetypes=[("Pen and Paper files", "*.pnp"), ("All files", "*.*")],
            parent=self,
        )
        if not filepath:
            return
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            self.canvas.deserialize(data.get("items", []))
            self.current_color = data.get("color", "#000000")
            self.brush_size = data.get("brush_size", 2)
            self.toolbar.update_color_display()
            self.current_file = filepath
            self.modified = False
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.update_status_bar()
            self._update_title()
        except (json.JSONDecodeError, OSError, KeyError) as e:
            messagebox.showerror(
                "Open Error", f"Could not open file:\n{e}", parent=self
            )

    def file_save(self):
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self.file_save_as()

    def file_save_as(self):
        filepath = filedialog.asksaveasfilename(
            title="Save Drawing As",
            defaultextension=".pnp",
            filetypes=[("Pen and Paper files", "*.pnp"), ("All files", "*.*")],
            parent=self,
        )
        if not filepath:
            return
        self._save_to_file(filepath)

    def _save_to_file(self, filepath):
        data = {
            "items": self.canvas.serialize(),
            "color": self.current_color,
            "brush_size": self.brush_size,
        }
        try:
            with open(filepath, "w") as f:
                json.dump(data, f)
            self.current_file = filepath
            self.modified = False
            self.update_status_bar()
            self._update_title()
        except OSError as e:
            messagebox.showerror(
                "Save Error", f"Could not save file:\n{e}", parent=self
            )

    def file_exit(self):
        if not self._check_unsaved():
            return
        self.destroy()


if __name__ == "__main__":
    app = PenAndPaperApp()
    app.mainloop()
