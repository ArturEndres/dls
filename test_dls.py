import importlib.machinery
import importlib.util
import sys
sys.dont_write_bytecode = True
import os
import subprocess
import tempfile
import threading

os.environ["LC_ALL"] = "C.UTF-8"  # predictable order in the asserts below
loader = importlib.machinery.SourceFileLoader(
    "dls", os.path.join(os.path.dirname(os.path.abspath(__file__)), "dls"))
dls = importlib.util.module_from_spec(importlib.util.spec_from_loader("dls", loader))
loader.exec_module(dls)

with tempfile.TemporaryDirectory() as t:
    os.chdir(t)
    os.mkdir("sub")
    for n in ("a.txt", ".h", "-x", "b\nc"):
        open(n, "w").close()
    rel = lambda fs: [os.path.relpath(f, t) for f in fs]

    assert rel(dls.parse([])[1]) == ["-x", "a.txt", "b\nc", "sub"]
    assert rel(dls.parse(["-la"])[1]) == ["-x", ".", "..", ".h", "a.txt", "b\nc", "sub"]
    assert rel(dls.parse(["-A"])[1]) == ["-x", ".h", "a.txt", "b\nc", "sub"]
    assert rel(dls.parse(["-ld", "sub"])[1]) == ["sub"]
    assert rel(dls.parse(["--", "-x"])[1]) == ["-x"]
    assert rel(dls.parse(["-w", "80", "a.txt"])[1]) == ["a.txt"]
    assert dls.parse(["-lh", "sub"])[0] == ["-l", "-h"]
    # one line per file, even with a line break in the name
    out = dls.render(["-l"], dls.parse([])[1])
    assert len(out) == 4 and not any("\n" in l for l in out), out
    assert len(dls.render(["-C"], dls.parse([])[1])) == 4  # -C doesn't join lines
    # sorting, the name with \n doesn't get lost
    assert len(dls.parse(["-t"])[1]) == 4

# sort flags: same order as ls
with tempfile.TemporaryDirectory() as t:
    for n, size, mtime in (("b", 2, 0), ("a", 0, 1), ("c", 1, 2)):
        with open(os.path.join(t, n), "w") as f:
            f.write("x" * size)
        os.utime(os.path.join(t, n), (mtime, mtime))
    names = lambda *args: [os.path.basename(f) for f in dls.parse([*args, t])[1]]
    assert names("-t") == ["c", "a", "b"]
    assert names("-ltr") == ["b", "a", "c"]
    assert names("--sort=size") == names("-S") == ["b", "c", "a"]
    assert names("-Itmp") == ["a", "b", "c"]  # the t of -Itmp isn't -t
    assert names("-U") == [n for n in subprocess.run(["ls", "-U", t], capture_output=True,
                                                     text=True).stdout.split()]
    # -c alone sorts by ctime; with -l it only changes the time shown (sorts by name)
    os.utime(os.path.join(t, "a"), (5, 5))  # ctime becomes now: a is the newest
    assert names("-c")[0] == "a" and names("-lc") == ["a", "b", "c"]
    assert names("-ltc")[0] == "a" and names("-tr")[-1] == "a"

# filters, -R, symlinks and flags with a separate argument, as in ls
with tempfile.TemporaryDirectory() as t:
    os.chdir(t)
    os.makedirs("d/sub")
    for n in ("a.txt", "b.o", "c~", "d/x", "d/sub/y", ".h"):
        open(n, "w").close()
    os.symlink("d", "lnk")
    names = lambda *args: rel(dls.parse(list(args))[1])
    assert names("-I", "*.o", "-B") == ["a.txt", "d", "lnk"]
    assert names("--hide", "*.txt") == ["b.o", "c~", "d", "lnk"]
    assert ".h" in names("-a", "--hide=.h")  # -a overrides --hide (not -I)
    assert names("-R", "d") == ["d/sub", "d/x", "d/sub/y"]
    assert names("lnk") == ["lnk/sub", "lnk/x"] and names("-l", "lnk") == ["lnk"]
    assert names("-F", "lnk") == ["lnk"] and names("-lH", "lnk") == ["lnk/sub", "lnk/x"]
    assert names("a.txt", "d", "b.o") == ["a.txt", "b.o", "d/sub", "d/x"]  # files first
    # -T 4 used to swallow the -1dU of render and drop the -l
    flags, files, fmt = dls.parse(["-T", "4", "-l", "a.txt"])
    assert fmt == "long" and "rw" in dls.render(flags, files)[0]
    flags, files, _ = dls.parse(["--color=never", "a.txt"])
    assert "\x1b" not in dls.render(flags, files)[0]
    flags, files, _ = dls.parse(["--hyperlink=always", "a.txt"])
    assert dls.cells(dls.render(flags, files)[0]) == 5
    assert dls.parse(["--help"])[0] == ["--help"]

assert dls.split_args(["-lI", "*.o", "-w80", "--hid", "x", "--", "-l"]) == (
    ["-l", "--ignore=*.o", "--width=80", "--hid=x"], ["-l"])
assert dls.split_args(["-I", "", "-a"])[0] == ["--ignore=", "-a"]
fmt = lambda *flags: dls.ls_format(list(flags))
assert fmt() == ("vertical", False) and fmt("-l", "-1") == ("long", False)
assert fmt("-1", "-l")[0] == "long"
assert fmt("-l", "-x")[0] == "across" and fmt("-lf")[0] == "vertical"
assert fmt("--format=commas")[0] == "commas" and fmt("-F", "-p") == ("vertical", False)
assert fmt("--classify=never")[1] is False and fmt("--full-time")[0] == "long"

# layout equal to ls -C, -x and -m, at every width
with tempfile.TemporaryDirectory() as t:
    for n in ("a", "bb", "ccc", "d" * 10, "e", "f" * 6, "g", "h" * 17, "i", "jj", "k" * 3):
        open(os.path.join(t, n), "w").close()
    names = subprocess.run(["ls", "-1", t], capture_output=True, text=True).stdout.split()
    for flag, form in (("-C", "vertical"), ("-x", "across"), ("-m", "commas")):
        for cols in (5, 10, 20, 23, 30, 45, 80, 200):
            ls = subprocess.run(["ls", flag, "-T0", "-w", str(cols), t],
                                capture_output=True, text=True).stdout
            pos, hw = dls.place([len(n) for n in names], cols, form)
            rows = [""] * (max(r for r, _ in pos) + 1)
            for i, (n, (r, x)) in enumerate(zip(names, pos)):
                comma = "," if form == "commas" and i < len(names) - 1 else ""
                rows[r] = rows[r].ljust(x) + n + comma
            assert rows == [l.rstrip() for l in ls.splitlines()], (flag, cols, rows, ls)
            assert all(w >= len(n) or w == cols for n, w in zip(names, hw))
assert dls.columns([5, 5, 5], 80) == (1, [5, 5, 5])

# same order as ls in a real locale: mixed case, punctuation ignored
os.environ["LC_ALL"] = "en_US.UTF-8"
with tempfile.TemporaryDirectory() as t:
    for n in ("B.txt", "a.txt", "_c", "Ç.txt", "d"):
        open(os.path.join(t, n), "w").close()
    ls = subprocess.run(["ls", "-1", t], capture_output=True, text=True).stdout.split("\n")[:-1]
    assert [os.path.basename(f) for f in dls.parse([t])[1]] == ls, ls

# grid at origin 100 with 18px cells: events at the edges converge to 100
a = dls.Axis(18)
for cell, p in [(3, 140), (4, 154), (3, 153), (5, 172)]:
    a.feed(cell, p)
assert a.start(1) == 100 and a.cell(135) == 2, (a.lo, a.hi)
a.feed(1, 500)  # the window moved: starts over without breaking or flagging misalignment
assert a.lo <= 500 <= a.hi and a.misses == 0
# a 10px cell measured as 9: the error adds up and is detected
b = dls.Axis(9)
for cell in range(1, 41):
    b.feed(cell, 100 + (cell - 1) * 10 + 5)
assert b.misses >= 3, b.misses
# right cell, but the pointer moved up to 4px between the event and the reading: no flag
c = dls.Axis(18)
for k in range(400):
    y = 100 + (k * 37) % 900
    c.feed((y - 100) // 18 + 1, y + (k * 7) % 9 - 4)
assert c.misses == 0 and c.start(1) - 100 in range(-4, 5), (c.misses, c.lo)

# the help line fits the width and keeps the essentials
plain = lambda h: dls.ANSI.sub("", h)
assert "ctrl/shift" in plain(dls.hint(200))
assert len(plain(dls.hint(80))) <= 80 and "envia" in plain(dls.hint(80))
assert "envia" in plain(dls.hint(10))
assert dls.cells("\x1b[01;34mpasta\x1b[0m 日本") == 10
assert dls.cells("\x1b]8;;file://h/a\aa\x1b]8;;\a") == 1  # OSC 8 link, from --hyperlink

# a read that cuts a mouse sequence waits for the rest; Esc alone is a key
r, w = os.pipe()
os.write(w, b"\x1b[<35;2;3Ma\x1b")
threading.Timer(0.01, os.write, (w, b"[<35;4;5M")).start()
assert dls.read_input(r) == ([(35, 2, 3), (35, 4, 5)], b"a")
os.write(w, b"\x1b")
assert dls.read_input(r) == ([], b"\x1b")
# scroll keys, with or without a modifier; focus and letters aren't navigation
assert dls.NAV.findall(b"\x1b[A\x1b[1;5B\x1b[5~\x1b[6;2~\x1b[H\x1b[F") == [
    (b"A", b""), (b"B", b""), (b"", b"5"), (b"", b"6"), (b"H", b""), (b"F", b"")]
assert dls.NAV.sub(b"", b"\x1b[Oq\x1b[5;2~a") == b"\x1b[Oqa"

# Wayland warns, even without XWayland (no DISPLAY)
os.environ.pop("DISPLAY", None)
os.environ["WAYLAND_DISPLAY"] = "wayland-0"
assert "X11" in dls.missing_requirement()
# a display that can't be reached: ls instead of GTK aborting in raw mode
os.environ.pop("WAYLAND_DISPLAY")
os.environ["DISPLAY"] = ":99"
try:
    import gi  # noqa: F401  (without PyGObject, e.g. on CI, there's no GTK to check)
except ImportError:
    pass
else:
    assert "display" in dls.missing_requirement()
print("ok")
