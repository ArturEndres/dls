<div align="center">

**English** · [Português (Brasil)](README.pt-BR.md)

<h1>dls</h1>

<h3>The <code>ls</code> you can drag.</h3>

<p>List files as usual and drag them <b>straight out of the terminal</b> into your browser,<br>file manager, WhatsApp Web or any app that accepts files.</p>

<p>
<a href="https://github.com/ArturEndres/dls/actions/workflows/test.yml"><img alt="tests" src="https://github.com/ArturEndres/dls/actions/workflows/test.yml/badge.svg"></a>
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
- **Visual cues**: the name under the mouse is highlighted (translucent with a compositor, solid without one, as in the demos), the cursor turns into a hand, the selection is shown in reverse video and the drag icon shows how many files are coming along.
- **Open**: double-click opens with the default app. Right-click shows an *open with…* menu listing the apps installed for that file type.
- **Keeps the `ls` look**: colors, layouts (`-C`, `-x`, `-m`, `-l`, `-1`), `-h`, `-F` and the other display flags, plus the order and the filters, because `ls` itself picks the files (`-t`, `-S`, `-r`, `-U`, `-a`, `-I`, `--hide`, `-R`…).
- **Lightweight**: a single Python file, nothing to install on a standard GNOME desktop. The listing shows up in ~30 ms and interaction is ready in ~150 ms.
- **Never leaves the terminal broken**: quitting with `q`, closing the tab or receiving `kill` all restore the terminal. `Ctrl+Z` suspends it like any program.

## Requirements

**Works out of the box:** Ubuntu and GNOME-based derivatives (Zorin, Pop!_OS…) on an X11 session, using gnome-terminal.
**Doesn't work:** Wayland sessions (the Ubuntu 22.04+ default) and terminals that don't use the gnome-terminal profile font (Konsole, xfce4-terminal, Ptyxis with its own font). In those cases `dls` doesn't break: it's just misaligned or falls back to `ls`. On Wayland, see [Alternatives](#alternatives).

| | |
|---|---|
| Session | **X11** (on Ubuntu 22.04/24.04 pick *Ubuntu on Xorg* on the login screen; Ubuntu 25.10+ no longer ships an X11 GNOME session) |
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

While open, `dls` takes over the terminal screen, like `less`: the terminal has no scrollback to move the list out from under the highlight. When you quit, the listing is printed in the terminal just like `ls`. Files are laid out like `ls` lays them out: in columns, across with `-x`, comma-separated with `-m`, one per line with `-l` or `-1`.

### Mouse

![Selecting several files by dragging over the names and with Ctrl+click, then sending them all at once](assets/selecao-multipla.gif)

| Action | Result |
|---|---|
| Hover over a name | highlights the name; the cursor turns into a hand |
| Press on a name and move **sideways** | drags that file |
| Press and move **up/down** | selects the files you pass over in that column (the first movement decides between dragging and selecting) |
| …then leave the column sideways | drags everything selected |
| Click | selects just that file |
| Shift + click | selects the range from the last click |
| Ctrl + click | adds to or removes from the selection |
| Drag a file that's already selected | drags the whole selection |
| Double-click | opens with the default app |
| Right-click | *open with…* menu |
| Mouse wheel | scrolls the list |

### Keyboard

| Key | Result |
|---|---|
| `↑` `↓` `PgUp` `PgDn` `Home` `End` | scroll the list |
| `a` | select all |
| `Esc` | clear the selection (with nothing selected, quit) |
| `Ctrl+Z` | suspend (`fg` brings it back) |
| `q` / `Ctrl+C` | quit |

### Outside an interactive terminal

With output redirected (`dls | grep x`) or without a reachable graphical display (SSH, TTY, a stale `DISPLAY` in tmux), `dls` behaves exactly like `ls`. So does `dls --help`. `ls` errors (a missing path, for example) are shown and the exit code is preserved.

## How it works

No program running *inside* a terminal can start a drag: while the button is held, X11 hands the pointer to the terminal window. `dls` works around this:

1. **Mouse tracking.** `dls` turns on the terminal's mouse tracking mode (`?1003` + `?1006`). From then on, the terminal reports which cell (row, column) the mouse is in.
2. **Calibration.** The cell size comes from your gnome-terminal profile font, measured with Pango the same way VTE (gnome-terminal's engine) measures it. The grid's position on screen is deduced by matching each terminal event with the real pointer position. Each event narrows the origin down to an interval, and the intersection converges to the exact pixel within a few movements.
3. **Transparent window.** A borderless, semi-transparent window is placed exactly over the name under the mouse. It, not the terminal, receives the click, so the drag is a native GTK/XDND drag.
4. **Selection.** Kept inside `dls` and drawn in the terminal itself with ANSI sequences (reverse video).
5. **Full screen.** The list is drawn on the terminal's alternate screen (`?1049`), which has no scrollback: the scrollbar and `Shift+PgUp` can't move the list behind `dls`'s back, so the highlight is always over the right file.

## Limitations

- **X11 only.** On Wayland, a window can't place itself at absolute coordinates or read the global pointer position. On a Wayland session `dls` warns and behaves like `ls`.
- **Terminal zoom** (`Ctrl +` / `Ctrl -`) or a non-default profile misaligns the highlight, since the measurement comes from the default profile font. `dls` notices it and shows a warning in place of the help line.
- **While open**, `-l` doesn't show the `total` line, and several folders (or `-R`) aren't split under headers. The listing printed on exit has both.
- **If the terminal is left blank or prints numbers when you click** (only happens if `dls` is killed with `kill -9`), restore it with `reset` or with:

  ```bash
  printf '\e[?1003l\e[?1006l\e[?1004l\e[?7h\e[?25h\e[?1049l'
  ```

## Alternatives

[dragon](https://github.com/mwh/dragon) and [ripdrag](https://github.com/nik012003/ripdrag) solve the same problem differently: you pass them file names and they open a small window to drag from. They work on Wayland and in any terminal, so use them if `dls` doesn't run on your setup.

On [kitty](https://sw.kovidgoyal.net/kitty/) 0.47+, [`kitten dnd file`](https://sw.kovidgoyal.net/kitty/kittens/dnd/) lets you drag that file straight out of the kitty window, with no extra window, even over SSH.

| | `dls` | dragon / ripdrag | `kitten dnd` |
|---|---|---|---|
| Where you drag from | the listing itself | a separate window | the kitty window |
| Picking files | mouse: click, Shift/Ctrl, drag over names | type the names (or a glob) | type the names (or a glob) |
| Session | X11 only | X11 and Wayland | X11, Wayland and macOS |
| Terminal | gnome-terminal (VTE) | any | kitty 0.47+ |

## Development

The project is a single executable file (`dls`) plus two checks:

```bash
python3 test_dls.py   # prints "ok"; runs on CI with Python 3.8 and 3.13
python3 test_gui.py   # prints PASS/FAIL per scenario
```

`test_dls.py` covers flag parsing, the file list with its order and filters (checked against `ls`), the `-C`/`-x`/`-m` layouts (checked against `ls` at several widths), grid calibration, terminal input reading and the help line.

`test_gui.py` runs `dls` in a real VTE terminal inside a nested X server (Xephyr), with the mouse and keys simulated through XTest and a window that accepts drops: highlight alignment, dragging one or several files from any column, odd names, Shift/Ctrl+click, the menu, the zoom warning, scrolling, resizing, `Ctrl+Z`/`fg` and every way out. It needs an X11 session and `sudo apt install xserver-xephyr x11-utils gir1.2-vte-2.91`.

## License

[MIT](LICENSE) © 2026 Artur Endres
