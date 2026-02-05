# Pen and Paper

A lightweight freehand drawing application built with Python and tkinter.

![UI Mockup](design/Pen%20and%20Paper%20-%20UI%20Mockup%201.1.JPG)

## Features

- **Freehand Drawing** - Draw with adjustable brush sizes (1-50px)
- **Eraser** - Remove strokes by dragging over them
- **Fill Tool** - Fill the entire canvas with the selected color
- **Color Picker** - Choose any color for drawing
- **Undo / Redo** - Full undo/redo history (up to 50 steps)
- **Save / Open** - Save and load drawings in `.pnp` format (JSON-based)
- **Status Bar** - Shows current filename and canvas fill percentage

## Requirements

- Python 3.8+
- tkinter (included with standard Python installations)

## Usage

```bash
python main.py
```

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New drawing |
| `Ctrl+O` | Open drawing |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` | Redo |

## File Format

Drawings are saved as `.pnp` files (JSON) containing canvas items, current color, and brush size.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Developed by [Wedge Dev](https://github.com/Taylor-C-Powell) | A [Materia Foundation](https://github.com/Taylor-C-Powell) project
