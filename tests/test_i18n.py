import ast, re, sys
from pathlib import Path
SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))
from i18n_strings import TR  # noqa: E402

def _keys():
    out = set()
    for n in ast.walk(ast.parse((SRC / "csPRESETS.py").read_text(encoding="utf-8"))):
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "L" and n.args and isinstance(n.args[0], ast.Constant):
            out.add(n.args[0].value)
    return out

def test_toutes_les_cles_traduites():
    assert not (_keys() - set(TR)), sorted(_keys() - set(TR))

def test_placeholders_identiques():
    for fr, tr in TR.items():
        ph = sorted(re.findall(r"\{\w+\}", fr))
        for t in tr:
            assert sorted(re.findall(r"\{\w+\}", t)) == ph, (fr, t)
