from __future__ import annotations

from pathlib import Path

from .errors import InteractionError

MAX_CLIPBOARD_PATH_CHARS = 4096


def select_project_directory(initial: str | Path | None = None) -> str | None:
    """Open an explicit, user-triggered system directory picker."""

    try:
        import tkinter as tk
        from tkinter import filedialog
    except (ImportError, OSError) as exc:
        raise InteractionError("The system folder picker is unavailable.") from exc

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(
            title="Choose an SDAD project",
            initialdir=str(initial) if initial else None,
            mustexist=True,
            parent=root,
        )
    except (OSError, tk.TclError) as exc:
        raise InteractionError("The system folder picker could not be opened.") from exc
    finally:
        root.destroy()
    return selected or None


def select_markdown_export_path(suggested_filename: str) -> str | None:
    """Open an explicit, user-triggered Save As dialog for one Markdown file."""

    try:
        import tkinter as tk
        from tkinter import filedialog
    except (ImportError, OSError) as exc:
        raise InteractionError("The system Save As dialog is unavailable.") from exc

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
        selected = filedialog.asksaveasfilename(
            title="Save Rule 5 proposal",
            initialfile=suggested_filename,
            defaultextension=".md",
            filetypes=(("Markdown files", "*.md"),),
            parent=root,
        )
    except (OSError, tk.TclError) as exc:
        raise InteractionError("The system Save As dialog could not be opened.") from exc
    finally:
        root.destroy()
    return selected or None


def read_clipboard_text() -> str:
    """Read one path-sized clipboard value after an explicit request."""

    try:
        import tkinter as tk
    except (ImportError, OSError) as exc:
        raise InteractionError("Clipboard access is unavailable.") from exc

    root = tk.Tk()
    root.withdraw()
    try:
        value = root.clipboard_get()
    except (OSError, tk.TclError) as exc:
        raise InteractionError("The clipboard does not contain readable text.") from exc
    finally:
        root.destroy()
    return normalize_clipboard_path(value)


def normalize_clipboard_path(value: object) -> str:
    if not isinstance(value, str):
        raise InteractionError("The clipboard does not contain text.")
    if len(value) > MAX_CLIPBOARD_PATH_CHARS:
        raise InteractionError("The clipboard text is too long to be a project path.")
    normalized = value.strip()
    if "\x00" in normalized or "\n" in normalized or "\r" in normalized:
        raise InteractionError("Paste one project path at a time.")
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"'", '"'}:
        normalized = normalized[1:-1].strip()
    if not normalized:
        raise InteractionError("The clipboard does not contain a project path.")
    return normalized
