import importlib.machinery
import importlib.util
import sys
sys.dont_write_bytecode = True
import os
import subprocess
import tempfile
import threading

os.environ["LC_ALL"] = "C.UTF-8"  # ordem previsivel nos asserts abaixo
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
    assert rel(dls.parse(["-la"])[1]) == ["-x", ".h", "a.txt", "b\nc", "sub"]
    assert rel(dls.parse(["-ld", "sub"])[1]) == ["sub"]
    assert rel(dls.parse(["--", "-x"])[1]) == ["-x"]
    assert rel(dls.parse(["-w", "80", "a.txt"])[1]) == ["a.txt"]
    assert dls.parse(["-lh", "sub"])[0] == ["-lh"]
    # 1 linha por arquivo, mesmo com quebra de linha no nome
    out = dls.render(["-l"], dls.parse([])[1])
    assert len(out) == 4 and not any("\n" in l for l in out), out
    assert len(dls.render(["-C"], dls.parse([])[1])) == 4  # -C nao junta linhas

# grade igual a do ls -C: mesmo numero de linhas em cada largura
with tempfile.TemporaryDirectory() as t:
    for n in ("a", "bb", "ccc", "d" * 10, "e", "f" * 6, "g", "h" * 17, "i", "jj", "k" * 3):
        open(os.path.join(t, n), "w").close()
    w = [len(n) for n in subprocess.run(["ls", "-1", t], capture_output=True,
                                        text=True).stdout.split()]
    for cols in (5, 10, 20, 23, 30, 45, 80, 200):
        ls = subprocess.run(["ls", "-C", "-w", str(cols), t], capture_output=True, text=True)
        assert dls.columns(w, cols)[0] == len(ls.stdout.splitlines()), (cols, ls.stdout)
assert dls.columns([5, 5, 5], 80) == (1, [5, 5, 5])
assert dls.one_per_line(["-la"]) and dls.one_per_line(["--format=long"])
assert not dls.one_per_line(["-a", "--color=never", "-h"])

# mesma ordem do ls num idioma real: maiusculas misturadas, pontuacao ignorada
os.environ["LC_ALL"] = "en_US.UTF-8"
with tempfile.TemporaryDirectory() as t:
    for n in ("B.txt", "a.txt", "_c", "Ç.txt", "d"):
        open(os.path.join(t, n), "w").close()
    ls = subprocess.run(["ls", "-1", t], capture_output=True, text=True).stdout.split("\n")[:-1]
    assert [os.path.basename(f) for f in dls.parse([t])[1]] == ls, ls

# grade com origem 100 e celula 18: eventos na borda convergem para 100
a = dls.Axis(18)
for cell, p in [(3, 140), (4, 154), (3, 153), (5, 172)]:
    a.feed(cell, p)
assert a.start(1) == 100 and a.cell(135) == 2, (a.lo, a.hi)
a.feed(1, 500)  # janela moveu: recomeca sem quebrar e sem acusar desalinhamento
assert a.lo <= 500 <= a.hi and a.misses == 0
# celula de 10 px medida como 9: o erro acumula e e detectado
b = dls.Axis(9)
for cell in range(1, 41):
    b.feed(cell, 100 + (cell - 1) * 10 + 5)
assert b.misses >= 3, b.misses
# celula certa, mas o ponteiro andou ate 4 px entre o evento e a leitura: nao acusa
c = dls.Axis(18)
for k in range(400):
    y = 100 + (k * 37) % 900
    c.feed((y - 100) // 18 + 1, y + (k * 7) % 9 - 4)
assert c.misses == 0 and c.start(1) - 100 in range(-4, 5), (c.misses, c.lo)

# dica cabe na largura e mantem o essencial
plain = lambda h: dls.ANSI.sub("", h)
assert "ctrl/shift" in plain(dls.hint(200))
assert len(plain(dls.hint(80))) <= 80 and "envia" in plain(dls.hint(80))
assert "envia" in plain(dls.hint(10))
assert dls.cells("\x1b[01;34mpasta\x1b[0m 日本") == 10

# leitura que corta uma sequencia de mouse espera o resto; Esc sozinho e tecla
r, w = os.pipe()
os.write(w, b"\x1b[<35;2;3Ma\x1b")
threading.Timer(0.01, os.write, (w, b"[<35;4;5M")).start()
assert dls.read_input(r) == ([(35, 2, 3), (35, 4, 5)], b"a")
os.write(w, b"\x1b")
assert dls.read_input(r) == ([], b"\x1b")
# teclas de rolar, com modificador ou nao; foco e letras nao sao navegacao
assert dls.NAV.findall(b"\x1b[A\x1b[1;5B\x1b[5~\x1b[6;2~\x1b[H\x1b[F") == [
    (b"A", b""), (b"B", b""), (b"", b"5"), (b"", b"6"), (b"H", b""), (b"F", b"")]
assert dls.NAV.sub(b"", b"\x1b[Oq\x1b[5;2~a") == b"\x1b[Oqa"
print("ok")
