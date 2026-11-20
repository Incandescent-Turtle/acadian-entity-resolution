"""lib_staging ne dépend que de genealogie_acadienne et de bibliothèques légères,
jamais du reste d'acadian_er ni de torch / PyG / LLM."""

import ast
import sys
from pathlib import Path

import acadian_er.lib_staging as staging

AUTORISES = {"genealogie_acadienne", "pandas", "pyarrow", "numpy", "pymysql"}


def test_imports_de_lib_staging():
    for fichier in Path(staging.__file__).parent.glob("*.py"):
        for noeud in ast.walk(ast.parse(fichier.read_text(encoding="utf-8"))):
            if isinstance(noeud, ast.Import):
                modules = [a.name for a in noeud.names]
            elif isinstance(noeud, ast.ImportFrom) and not noeud.level:
                modules = [noeud.module]
            else:  # imports relatifs : restent dans lib_staging
                continue
            for m in modules:
                racine = m.split(".")[0]
                assert racine in AUTORISES or racine in sys.stdlib_module_names, (fichier.name, m)
