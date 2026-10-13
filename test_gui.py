"""End-to-end test of the graphical part, in a nested X server.

A real VTE terminal runs dls in Xephyr; the mouse and keys come from XTest and
a second window accepts the drops. Prints PASS/FAIL for each scenario.

    python3 test_gui.py

Needs an X11 session (Xephyr opens as a window), Xephyr, xwininfo, libXtst and
gir1.2-vte-2.91 (Ubuntu: apt install xserver-xephyr x11-utils gir1.2-vte-2.91).
"""
import atexit
import ctypes
import importlib.machinery
import importlib.util
import os
import signal
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
DLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dls")

# nested X server; -displayfd says which display it took once it's ready
r, w = os.pipe()
xephyr = subprocess.Popen(["Xephyr", "-displayfd", str(w), "-screen", "1280x800", "-ac"],
                          pass_fds=[w], stderr=subprocess.DEVNULL)
os.close(w)
atexit.register(xephyr.terminate)
os.environ["DISPLAY"] = ":" + os.read(r, 16).decode().strip()
os.environ["XDG_SESSION_TYPE"] = "x11"
os.environ.pop("WAYLAND_DISPLAY", None)

import gi  # noqa: E402  (after DISPLAY points to the nested server)
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkX11", "3.0")
gi.require_version("Vte", "2.91")
from gi.repository import Gdk, GdkX11, Gio, GLib, Gtk, Vte  # noqa: E402

loader = importlib.machinery.SourceFileLoader("dls", DLS)
dls = importlib.util.module_from_spec(importlib.util.spec_from_loader("dls", loader))
loader.exec_module(dls)

x11 = ctypes.CDLL("libX11.so.6")
xt = ctypes.CDLL("libXtst.so.6")
x11.XOpenDisplay.restype = ctypes.c_void_p
x11.XFlush.argtypes = [ctypes.c_void_p]
x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
x11.XSetInputFocus.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
xt.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_ulong]
xt.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
xt.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
dpy = x11.XOpenDisplay(os.environ["DISPLAY"].encode())
SHIFT, CTRL, ESC = 0xffe1, 0xffe3, 0xff1b


def move(x, y):
    xt.XTestFakeMotionEvent(dpy, -1, int(x), int(y), 0)
    x11.XFlush(dpy)


def click(b=1, mod=None):
    kc = mod and x11.XKeysymToKeycode(dpy, mod)
    if mod:
        xt.XTestFakeKeyEvent(dpy, kc, True, 0)
    xt.XTestFakeButtonEvent(dpy, b, True, 0)
    xt.XTestFakeButtonEvent(dpy, b, False, 0)
    if mod:
        xt.XTestFakeKeyEvent(dpy, kc, False, 0)
    x11.XFlush(dpy)


def button(b, down):
    xt.XTestFakeButtonEvent(dpy, b, down, 0)
    x11.XFlush(dpy)


def key(sym):
    kc = x11.XKeysymToKeycode(dpy, sym)
    xt.XTestFakeKeyEvent(dpy, kc, True, 0)
    xt.XTestFakeKeyEvent(dpy, kc, False, 0)
    x11.XFlush(dpy)


# fixtures: 8 files for -1, 100 to scroll, and enough for several columns
tmp = tempfile.TemporaryDirectory()
ONE, BIG, COLS = (os.path.join(tmp.name, d) for d in ("one", "big", "cols"))
for d, names in ((ONE, [f"{c}.txt" for c in "abcdefgh"]), (BIG, [f"f{i:03}" for i in range(100)]),
                 (COLS, [f"c{i:02}" for i in range(1, 31)] + ["a b.txt", "日本.txt", "bad\udcffname"])):
    os.mkdir(d)
    for n in names:
        open(os.path.join(d, n), "w").close()

results = []


def check(name, ok, info=""):
    results.append((name, bool(ok), info))


# terminal with the same font dls measures
cw, ch, font = dls.cell_size()
win = Gtk.Window()
win.move(0, 0)
term = Vte.Terminal()
term.set_font(font)
term.set_size(80, 24)
win.add(term)
win.show_all()
# drop target
dropped = []
target = Gtk.Window(title="target")
target.set_default_size(250, 250)
target.move(800, 80)
target.drag_dest_set(Gtk.DestDefaults.ALL, [Gtk.TargetEntry.new("text/uri-list", 0, 0)],
                     Gdk.DragAction.COPY)
target.connect("drag-data-received", lambda w, c, x, y, d, i, t: dropped.append(d.get_uris()))
target.show_all()

st = {"pid": None, "exit": None}
term.connect("child-exited", lambda t, status: st.update(exit=status))


def text():
    try:
        return term.get_text_format(Vte.Format.TEXT)
    except AttributeError:
        return term.get_text()[0]


def spawn(argv, cwd, **env):
    st.update(pid=None, exit=None)
    term.reset(True, True)
    envv = [f"{k}={v}" for k, v in {**os.environ, "TERM": "xterm-256color", **env}.items()]
    term.spawn_async(Vte.PtyFlags.DEFAULT, cwd, argv, envv, GLib.SpawnFlags.SEARCH_PATH,
                     None, None, -1, None, lambda t, pid, err, *_: st.update(pid=pid), None)


def origin():
    _, wx, wy = win.get_window().get_origin()
    tx, ty = term.translate_coordinates(win, 0, 0)
    return wx + tx, wy + ty


def cell_px(col, row):  # 0-based cell -> its center on screen (VTE's cell: zoom changes it)
    ox, oy = origin()
    w, h = term.get_char_width(), term.get_char_height()
    return ox + col * w + w // 2, oy + row * h + h // 2


def windows():
    """(x, y, width, height) of every visible top-level window."""
    out = subprocess.run(["xwininfo", "-root", "-children"], capture_output=True, text=True).stdout
    found = []
    for wid in (l.split()[0] for l in out.splitlines() if l.strip().startswith("0x")):
        info = subprocess.run(["xwininfo", "-id", wid], capture_output=True, text=True).stdout
        g = dict(l.split(":", 1) for l in info.splitlines() if ":" in l)
        g = {k.strip(): v.strip() for k, v in g.items()}
        if "IsViewable" in info:
            found.append((int(g["Absolute upper-left X"]), int(g["Absolute upper-left Y"]),
                          int(g["Width"]), int(g["Height"])))
    return found


def highlights():  # the highlight is the visible window one cell tall
    return [w for w in windows() if w[3] == ch]


steps = []


def at(delay, fn):
    steps.append((delay, fn))


def glide(x0, y0, x1, y1, n=12):
    for k in range(1, n + 1):
        at(25, lambda k=k: move(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n))


def focus_terminal():  # no window manager: keep focus on the terminal, as mutter would
    x11.XSetInputFocus(dpy, win.get_window().get_xid(), 2, 0)
    x11.XFlush(dpy)


# layout dls should draw: computed with dls's own functions for the terminal width
lay = {}


def compute(args, cwd):
    flags, files, fmt = dls.parse([*args, cwd])
    lines = dls.render(flags, files)
    pos, hw = dls.place([dls.cells(l) for l in lines], term.get_column_count(), fmt)
    lay.update(files=files, pos=pos, hw=hw)


def idx(name):
    return next(i for i, f in enumerate(lay["files"]) if os.path.basename(f) == name)


def pos(i, dx=1):  # center of the dx-th cell of file i
    r, x = lay["pos"][i]
    return cell_px(x + dx, r)


def uri(i):
    return Gio.File.new_for_path(lay["files"][i]).get_uri()


def calibrate():  # a few movements over the grid so dls finds where it is
    for k in range(4):
        at(100, lambda k=k: move(*cell_px(3 + 2 * k, k)))


def highlight_on(name):
    i = idx(name)
    ox, oy = origin()
    r, x = lay["pos"][i]
    want = (ox + x * cw, oy + r * ch, lay["hw"][i] * cw, ch)
    seen = highlights()
    return any(abs(h[0] - want[0]) <= 3 and abs(h[1] - want[1]) <= 3 and h[2] == want[2]
               for h in seen), f"want {want}, seen {seen}"


def drag(name, label, expect):
    """Presses on name, goes sideways, then to the target and drops."""
    calibrate()
    at(150, lambda: move(*pos(idx(name))))
    at(300, lambda: check(f"highlight over {name!r} before the drag", *highlight_on(name)))
    at(10, lambda: (dropped.append(None), button(1, True)))
    at(30, lambda: [move(pos(idx(name))[0] + 8 * k, pos(idx(name))[1]) for k in range(1, 7)])
    for k in range(1, 16):
        at(25, lambda k=k: move(pos(idx(name))[0] + (900 - pos(idx(name))[0]) * k / 15,
                                pos(idx(name))[1] + (200 - pos(idx(name))[1]) * k / 15))
    at(200, lambda: button(1, False))
    at(800, lambda: check(label, dropped[-1] is not None
                          and sorted(dropped[-1]) == sorted(expect()), (dropped[-1], expect())))


def quits(label, key=b"q", want="h.txt"):
    at(300, lambda: term.feed_child(key))
    at(1000, lambda: check(label, st["exit"] == 0 and want in text() and "sai" not in text(),
                           (st["exit"], text().splitlines()[-3:])))


# --- one per line: alignment, drags, menu, zoom
compute(["-1"], ONE)  # the glides below take coordinates now
at(200, focus_terminal)
at(300, lambda: (spawn([DLS, "-1"], ONE), compute(["-1"], ONE)))
at(1500, lambda: check("opens and draws the list", "a.txt" in text() and "sai" in text(),
                       text().splitlines()[:2]))
for k in (0, 1, 2, 3, 2, 1):
    at(120, lambda k=k: move(*cell_px(2 + k, k)))
at(150, lambda: move(*cell_px(2, 1)))
at(400, lambda: check("highlight aligned over b.txt (+-3px)", *highlight_on("b.txt")))
at(10, lambda: check("measured cell = VTE cell", (cw, ch) == (term.get_char_width(),
                                                              term.get_char_height()),
                     ((cw, ch), (term.get_char_width(), term.get_char_height()))))
at(100, lambda: term.feed_child(b"aqa"))  # pasted text: neither quits nor selects all
at(500, lambda: check("pasted text containing q doesn't quit", st["exit"] is None))
drag("b.txt", "drag 1 file", lambda: [uri(idx("b.txt"))])
# select a..c dragging down, then leave sideways: drags 3
calibrate()
at(150, lambda: move(*pos(0)))
at(300, lambda: button(1, True))
glide(*pos(0), pos(0)[0], pos(0)[1] + 2 * ch, n=8)
glide(pos(0)[0], pos(0)[1] + 2 * ch, pos(0)[0] + 200, pos(0)[1] + 2 * ch, n=8)
glide(pos(0)[0] + 200, pos(0)[1] + 2 * ch, 900, 200, n=15)
at(200, lambda: button(1, False))
at(800, lambda: check("dragging down selects, sideways drags the 3",
                      dropped and dropped[-1] and len(dropped[-1]) == 3, dropped[-1:]))
# "open with" menu on right click: one more window on screen
calibrate()
at(200, lambda: move(*pos(3)))
at(300, lambda: st.update(before=len(windows())))
at(10, lambda: click(3))
at(600, lambda: check("right click opens the menu", len(windows()) > st["before"],
                      (st["before"], len(windows()))))
at(200, lambda: key(ESC))
# zoom: the cell changes, dls warns about the misalignment
at(500, lambda: term.set_font_scale(1.3))
for k in range(25):
    at(60, lambda k=k: move(*cell_px(1 + k % 7, k % 6)))
at(500, lambda: check("zoom shows the misalignment warning", "desalinhado" in text(),
                      text().splitlines()[-3:]))
at(100, lambda: term.set_font_scale(1.0))
quits("q quits with status 0 and prints the ls listing")

# --- kill -TERM restores the terminal
at(300, lambda: spawn([DLS, "-1"], ONE))
at(1500, lambda: os.kill(st["pid"], signal.SIGTERM))
at(1000, lambda: check("SIGTERM quits cleanly and prints ls",
                       st["exit"] == 0 and "a.txt" in text() and "sai" not in text(),
                       (st["exit"], text().splitlines()[-2:])))

# --- scrolling 100 files
at(300, lambda: spawn([DLS, "-1"], BIG))
at(1500, lambda: st.update(top=text().splitlines()[0]))
at(100, lambda: move(*cell_px(3, 5)))
at(150, lambda: click(5))
at(150, lambda: click(5))
at(500, lambda: check("the wheel scrolls", text().splitlines()[0] != st["top"],
                      (st["top"], text().splitlines()[0])))
at(200, lambda: term.feed_child(b"\x1b[F"))  # End
at(500, lambda: check("End goes to the bottom", "f099" in text(), text().splitlines()[-2:]))
at(200, lambda: term.feed_child(b"\x03"))
at(1000, lambda: check("Ctrl+C quits with status 0", st["exit"] == 0, st["exit"]))

# --- columns like ls -C: names in any column, odd names, shift/ctrl, select all
at(300, lambda: (spawn([DLS], COLS), compute([], COLS)))
at(1500, lambda: check("columns like ls -C", len(set(x for _, x in lay["pos"])) > 1,
                       lay["pos"][:5]))
drag("c15", "drag from the 2nd/3rd column gets the right file", lambda: [uri(idx("c15"))])
drag("a b.txt", "name with a space becomes %20", lambda: [uri(idx("a b.txt"))])
drag("日本.txt", "CJK name (2 cells wide)", lambda: [uri(idx("日本.txt"))])
drag("bad\udcffname", "name with an invalid byte", lambda: [uri(idx("bad\udcffname"))])
calibrate()
at(150, lambda: move(*pos(idx("c02"))))
at(200, lambda: click())
at(200, lambda: move(*pos(idx("c05"))))
at(200, lambda: click(1, SHIFT))
calibrate()
at(200, lambda: move(*pos(idx("c10"))))
at(200, lambda: click(1, CTRL))
drag("c03", "shift+click and ctrl+click",
     lambda: [uri(idx(n)) for n in ("c02", "c03", "c04", "c05", "c10")])
at(200, lambda: term.feed_child(b"a"))
drag("c01", "a selects all", lambda: [uri(i) for i in range(len(lay["files"]))])
at(200, lambda: term.feed_child(b"\x1b"))
at(300, lambda: (st.update(size=win.get_size()), win.resize(900, 300)))
at(800, lambda: compute([], COLS))
drag("c20", "after resizing the terminal", lambda: [uri(idx("c20"))])
quits("q quits after a resize", want="c30")
at(300, lambda: win.resize(*st["size"]))

# --- -x (across) and -m (commas)
at(300, lambda: (spawn([DLS, "-x"], COLS), compute(["-x"], COLS)))
at(1500, lambda: None)
drag("c07", "-x: drag gets the right file", lambda: [uri(idx("c07"))])
quits("q quits -x", want="c30")
at(300, lambda: (spawn([DLS, "-m"], COLS), compute(["-m"], COLS)))
at(1500, lambda: check("-m draws the commas", "c01, c02" in text(), text().splitlines()[:1]))
drag("c12", "-m: drag gets the right file", lambda: [uri(idx("c12"))])
quits("q quits -m", want="c30")

# --- no window manager: focus follows the pointer to the highlight, which stays
at(300, lambda: (spawn([DLS, "-1"], ONE), compute(["-1"], ONE)))
at(1500, lambda: (x11.XSetInputFocus(dpy, 1, 1, 0), x11.XFlush(dpy)))  # PointerRoot
calibrate()
at(150, lambda: move(*pos(idx("c.txt"))))
at(800, lambda: check("without a WM the highlight doesn't vanish", *highlight_on("c.txt")))
at(10, focus_terminal)
quits("q quits")

# --- Ctrl+Z suspends and fg resumes, from a real shell with job control
SH = ["bash", "--norc", "--noprofile", "-i"]
at(300, lambda: spawn(SH, ONE, PS1="$ "))
at(800, lambda: term.feed_child(f"{DLS} -1\n".encode()))
at(1500, lambda: check("dls opens from bash", "sai" in text(), text().splitlines()[:2]))
at(100, lambda: term.feed_child(b"\x1a"))
at(800, lambda: check("Ctrl+Z gives the shell back", "Stopped" in text() or "Parado" in text(),
                      text().splitlines()[-3:]))
at(100, lambda: term.feed_child(b"fg\n"))
at(800, lambda: check("fg brings dls back", "sai" in text(), text().splitlines()[-2:]))
at(100, lambda: term.feed_child(b"q"))
# a display that can't be reached and --help: plain ls, the terminal stays usable
at(800, lambda: term.feed_child(
    f"clear; DISPLAY=:99 {DLS} -1; stty -a | grep -q -- -icanon && echo RAW || echo COOKED\n"
    .encode()))
at(1500, lambda: check("unreachable DISPLAY: warns, prints ls, terminal stays cooked",
                       "display" in text() and "h.txt" in text() and "COOKED" in text(),
                       text().splitlines()[:12]))
at(100, lambda: term.feed_child(f"clear; {DLS} --help; echo rc=$?\n".encode()))
at(1500, lambda: check("--help shows the ls help", "rc=0" in text() and "coreutils" in text()
                       and "sai" not in text(), text().splitlines()[-4:]))
at(100, lambda: term.feed_child(b"exit\n"))


def runner(i=0):
    if i == len(steps):
        Gtk.main_quit()
        return False

    def go():
        try:
            steps[i][1]()
        except Exception as e:
            results.append((f"step {i}", False, repr(e)))
        runner(i + 1)
        return False
    GLib.timeout_add(steps[i][0], go)
    return False


GLib.timeout_add(500, runner)
GLib.timeout_add_seconds(240, lambda: (results.append(("timeout", False, "")), Gtk.main_quit()))
Gtk.main()
for name, ok, info in results:
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {info}"))
sys.exit(not all(ok for _, ok, _ in results))
