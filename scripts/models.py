#!/usr/bin/env python3
"""Lista, seleciona e importa modelos do Ollama.

  python scripts/models.py           lista o Ollama e importa todos os .gguf de Models/
  python scripts/models.py <modelo>  seleciona <modelo>; se não estiver no Ollama, importa da pasta
"""

import argparse
import difflib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    import ollama  # noqa: F401
except ModuleNotFoundError:
    venv_python = ROOT / ".venv" / "bin" / "python"
    if venv_python.exists() and Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
        os.execv(venv_python, [str(venv_python), __file__, *sys.argv[1:]])  # reexecuta no .venv
    sys.exit(
        "ERRO: a biblioteca 'ollama' não está instalada. Rode na pasta do projeto:\n"
        "  python -m venv .venv && .venv/bin/pip install -r requirements.txt"
    )

from services.models import ModelError, find_file, find_ollama, import_gguf, list_ollama, ollama_name, scan  # noqa: E402

CONFIG = ROOT / ".lexgraph" / "config.json"


def select(name: str) -> None:
    CONFIG.parent.mkdir(exist_ok=True)
    CONFIG.write_text(json.dumps({"selected_model": name}, indent=2))
    print(f"Modelo selecionado: {name}")


def import_all(folder: Path) -> int:
    names = list_ollama()
    print("Modelos no Ollama:", *names or ["(nenhum)"], sep="\n  ")
    registered = {n.split(":")[0] for n in names}
    errors = 0
    for display, parts in scan(folder).items():
        if ollama_name(display) in registered:
            print(f"[já registrado] {display}")
            continue
        print(f"[importando] {display}…")
        try:
            print(f"  ok: {import_gguf(display, parts)}")
        except ModelError as e:
            errors += 1
            print(f"  ERRO: {e}")
    if errors:
        print(f"\n{errors} modelo(s) falharam; veja as mensagens acima.")
    return 3 if errors else 0


def use(query: str, folder: Path) -> int:
    names = list_ollama()
    if name := find_ollama(query, names):
        select(name)
        return 0
    found = find_file(query, folder)
    if not found:
        close = difflib.get_close_matches(query, names + list(scan(folder)), n=3, cutoff=0.5)
        hint = f" Você quis dizer: {', '.join(close)}?" if close else ""
        raise ModelError(f"'{query}' não está no Ollama nem em '{folder}'.{hint}")
    print(f"Importando {found[0]} para o Ollama…")
    select(import_gguf(*found))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("model", nargs="?", help="nome no Ollama, arquivo .gguf da pasta ou caminho")
    parser.add_argument("--models-dir", type=Path, default=ROOT / "Models")
    args = parser.parse_args()
    try:
        return use(args.model, args.models_dir) if args.model else import_all(args.models_dir)
    except ModelError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompido.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
