import importlib.machinery
import sys
sys.dont_write_bytecode = True
import os
import tempfile

dls = importlib.machinery.SourceFileLoader(
    "dls", os.path.join(os.path.dirname(os.path.abspath(__file__)), "dls")).load_module()

with tempfile.TemporaryDirectory() as t:
    os.chdir(t)
    os.mkdir("sub")
    for n in ("a.txt", ".h", "-x"):
        open(n, "w").close()
    rel = lambda fs: [os.path.relpath(f, t) for f in fs]

    assert rel(dls.parse([])[1]) == ["-x", "a.txt", "sub"]
    assert rel(dls.parse(["-la"])[1]) == ["-x", ".h", "a.txt", "sub"]
    assert rel(dls.parse(["-ld", "sub"])[1]) == ["sub"]
    assert rel(dls.parse(["--", "-x"])[1]) == ["-x"]
    assert rel(dls.parse(["-w", "80", "a.txt"])[1]) == ["a.txt"]
    assert dls.parse(["-lh", "sub"])[0] == ["-lh"]
    assert len(dls.render(["-l"], dls.parse([])[1])) == 3

# grade com origem 100 e celula 18: eventos na borda convergem para 100
a = dls.Axis(18)
for cell, p in [(3, 140), (4, 154), (3, 153), (5, 172)]:
    a.feed(cell, p)
assert a.start(1) == 100 and a.cell(135) == 2, (a.lo, a.hi)
a.feed(1, 500)  # janela moveu: recomeca sem quebrar
assert a.lo <= 500 <= a.hi
# dica cabe na largura e mantem o essencial
plain = lambda h: dls.ANSI.sub("", h)
assert "ctrl/shift" in plain(dls.hint(200))
assert len(plain(dls.hint(80))) <= 80 and "envia" in plain(dls.hint(80))
assert "envia" in plain(dls.hint(10))
print("ok")
