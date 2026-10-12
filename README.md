<div align="center">

[Português (Brasil)](README.md) · **English**

<h1>dls</h1>

<h3>The <code>ls</code> you can drag.</h3>

<p>List files as usual and drag them <b>straight out of the terminal</b> into your browser,<br>file manager, WhatsApp Web or any app that accepts files.</p>

<p>
<a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-yellow"></a>
<img alt="Python 3.8+" src="https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white">
<img alt="Linux X11" src="https://img.shields.io/badge/linux-X11-FCC624?logo=linux&logoColor=black">
<img alt="GNOME" src="https://img.shields.io/badge/GNOME-GTK%203-4A86CF?logo=gnome&logoColor=white">
<img alt="zero dependencies" src="https://img.shields.io/badge/dependencies-zero-brightgreen">
<a href="https://github.com/ArturEndres/dls/stargazers"><img alt="stars" src="https://img.shields.io/github/stars/ArturEndres/dls?style=flat&logo=github"></a>
</p>

<img src="assets/arrastar.gif" alt="Dragging a file from the terminal into an upload page" width="100%">

<p>
<a href="#installation"><b>Installation</b></a> ·
<a href="#usage"><b>Usage</b></a> ·
<a href="#how-it-works"><b>How it works</b></a> ·
<a href="#limitations"><b>Limitations</b></a>
</p>

<pre>git clone https://github.com/ArturEndres/dls.git && ln -s "$PWD/dls/dls" ~/.local/bin/dls</pre>

</div>

---

## Why

Terminals don't let you drag files *out*. To send a file through the browser, someone working in the terminal has to open the file manager, navigate to the same folder and only then drag it. `dls` removes that detour: the file you're looking at in the terminal can be dragged right from there.

## Features

- **Native drag** (XDND): works with any app that accepts dropped files.
- **Multi-select**: drag over the names (like selecting text), Shift+click for a range, Ctrl+click to toggle.
- **Visual cues**: the row under the mouse is highlighted (translucent with a compositor, solid without one, as in the demos), the cursor turns into a hand, the selection is shown in reverse video and the drag icon shows how many files are coming along.
- **Open**: double-click opens with the default app. Right-click shows an *open with…* menu listing the apps installed for that file type.
- **Keeps the `ls` look**: colors, `-l`, `-h`, `-a` and the other display flags.
- **Lightweight**: a single Python file, nothing to install on a standard GNOME desktop. The listing shows up in ~30 ms and interaction is ready in ~150 ms.
- **Never leaves the terminal broken**: quitting with `q`, closing the tab or receiving `kill` all restore the terminal.

## Requirements

**Works out of the box:** Ubuntu and GNOME-based derivatives (Zorin, Pop!_OS…) on an X11 session, using gnome-terminal.
**Doesn't work:** Wayland sessions (the Ubuntu 22.04+ default) and terminals that don't use the gnome-terminal profile font (Konsole, xfce4-terminal, Ptyxis with its own font). In those cases `dls` doesn't break: it's just misaligned or falls back to `ls`.

| | |
|---|---|
| Session | **X11** (Ubuntu 22.04+ defaults to Wayland: pick *Ubuntu on Xorg* on the login screen) |
| Terminal | **gnome-terminal** (or another VTE-based terminal using the gnome-terminal profile font) |
| Python | 3.8+ |
| Libraries | PyGObject, pycairo, GTK 3 |

Ubuntu, Zorin, Pop!_OS, Fedora Workstation and other GNOME distros ship all of this already. If something is missing:

```bash
# Debian / Ubuntu
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0

# Fedora
sudo dnf install python3-gobject python3-cairo gtk3
```

## Installation

```bash
git clone https://github.com/ArturEndres/dls.git
cd dls
ln -s "$PWD/dls" ~/.local/bin/dls
```

`~/.local/bin` must be on your `PATH` (it already is on Ubuntu and derivatives). To check:

```bash
command -v dls
```

To uninstall, just `rm ~/.local/bin/dls`.

## Usage

```bash
dls                  # current folder
dls -lh ~/Downloads  # accepts ls flags
dls *.pdf            # only files matching the pattern
dls -a               # include hidden files
```

`dls` prints the listing and waits for the mouse. When you quit, the listing stays in the terminal.

### Mouse

![Selecting several files by dragging over the names and with Ctrl+click, then sending them all at once](assets/selecao-multipla.gif)

| Action | Result |
|---|---|
| Hover over a name | highlights the row; the cursor turns into a hand |
| Press on a name and move **sideways** | drags that file |
| Press and move **up/down** | selects the rows you pass over (the first movement decides between dragging and selecting) |
| …then leave the names column sideways | drags everything selected |
| Click | selects just that file |
| Shift + click | selects the range from the last click |
| Ctrl + click | adds to or removes from the selection |
| Drag a row that's already selected | drags the whole selection |
| Double-click | opens with the default app |
| Right-click | *open with…* menu |

### Keyboard

| Key | Result |
|---|---|
| `a` | select all |
| `Esc` | clear the selection (with nothing selected, quit) |
| `q` / `Ctrl+C` | quit |

### Outside an interactive terminal

With output redirected (`dls | grep x`) or without a graphical display (SSH, TTY), `dls` behaves exactly like `ls`. `ls` errors (a missing path, for example) are shown and the exit code is preserved.

## How it works

No program running *inside* a terminal can start a drag: while the button is held, X11 hands the pointer to the terminal window. `dls` works around this:

1. **Mouse tracking.** `dls` turns on the terminal's mouse tracking mode (`?1003` + `?1006`). From then on, the terminal reports which cell (row, column) the mouse is in.
2. **Calibration.** The cell size comes from your gnome-terminal profile font, measured with Pango the same way VTE (gnome-terminal's engine) measures it. The grid's position on screen is deduced by matching each terminal event with the real pointer position. Each event narrows the origin down to an interval, and the intersection converges to the exact pixel within a few movements.
3. **Transparent window.** A borderless, semi-transparent window is placed exactly over the row under the mouse. It, not the terminal, receives the click, so the drag is a native GTK/XDND drag.
4. **Selection.** Kept inside `dls` and drawn in the terminal itself with ANSI sequences (reverse video).

## Limitations

- **X11 only.** On Wayland, a window can't place itself at absolute coordinates or read the global pointer position. On a Wayland session `dls` warns and behaves like `ls`.
- **Terminal zoom** (`Ctrl +` / `Ctrl -`) or a non-default profile misaligns the highlight, since the measurement comes from the default profile font.
- **Sorting:** the listing is always alphabetical. Flags like `-t` and `-S` are ignored.
- **Lists taller than the screen:** only visible rows respond to the mouse. Filter instead (`dls *.pdf`).
- **Names with wide characters** (CJK, emoji) may make the highlight a bit narrower than the row.
- **Flags with a separate argument** (`-I pattern`, `-w 80`) are passed to `ls`, but the argument isn't treated as a draggable file. Files hidden by `-I` still show up as draggable.
- **If the terminal starts printing numbers when you click** (only happens if `dls` is killed with `kill -9`), restore it with `reset` or with:

  ```bash
  printf '\e[?1003l\e[?1006l\e[?7h'
  ```

## Development

The project is a single executable file (`dls`) plus an automated check:

```bash
python3 test_dls.py   # prints "ok"
```

The test covers flag parsing, the file list, grid calibration and the help line. The graphical part was validated in a nested X server (Xephyr) with a real VTE terminal and a mouse simulated through XTest.

## License

[MIT](LICENSE) © 2026 Artur Endres
