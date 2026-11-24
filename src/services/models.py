"""Descoberta e importação de modelos GGUF no Ollama (sem inferência)."""

import re
from pathlib import Path

import ollama

SPLIT = re.compile(r"(.+)-(\d{5})-of-(\d{5})\.gguf$", re.I)
client = ollama.Client()  # lê OLLAMA_HOST


class ModelError(Exception):
    """Erro com mensagem pronta para o usuário."""


def ollama_name(filename: str) -> str:
    stem = re.sub(r"(-\d{5}-of-\d{5})?\.gguf$", "", filename, flags=re.I)
    return re.sub(r"[^a-z0-9._/-]+", "-", stem.lower()).strip("-._") or "modelo"


def list_ollama() -> list[str]:
    try:
        return sorted(m.model for m in client.list().models)
    except ollama.ResponseError as e:
        raise ModelError(f"O Ollama respondeu com erro ao listar modelos: {e.error}") from None
    except ConnectionError:
        raise ModelError(
            "Não foi possível conectar ao Ollama. Inicie com 'sudo systemctl start ollama' "
            "ou 'ollama serve' (ou ajuste OLLAMA_HOST se ele usa outro endereço)."
        ) from None


def find_ollama(query: str, names: list[str]) -> str | None:
    q = query.lower() if ":" in query else ollama_name(query)
    if q in names or f"{q}:latest" in names:
        return q if q in names else f"{q}:latest"
    same = [n for n in names if n.split(":")[0] == q]
    if len(same) > 1:
        raise ModelError(f"'{query}' é ambíguo: {', '.join(same)}. Informe a tag completa.")
    return same[0] if same else None


def scan(folder: Path) -> dict[str, list[Path]]:
    """Agrupa os .gguf da pasta por modelo: {arquivo exibido: [partes]}."""
    if not folder.is_dir():
        raise ModelError(f"A pasta de modelos '{folder}' não existe. Crie-a ou use --models-dir.")
    groups: dict[str, list[Path]] = {}
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() != ".gguf" or path.name.lower().startswith("mmproj"):
            continue  # mmproj é projetor de visão, não modelo de texto
        split = SPLIT.match(path.name)
        groups.setdefault(f"{split[1]}.gguf" if split else path.name, []).append(path)
    return groups


def find_file(query: str, folder: Path) -> tuple[str, list[Path]] | None:
    path = Path(query).expanduser()
    if path.is_file():  # caminho direto; modelo dividido leva as partes vizinhas
        split = SPLIT.match(path.name)
        parts = sorted(path.parent.glob(f"{split[1]}-*-of-{split[3]}.gguf")) if split else [path]
        return (f"{split[1]}.gguf" if split else path.name), parts
    wanted = {query.lower(), f"{query.lower()}.gguf"}
    return next(
        ((k, v) for k, v in scan(folder).items() if wanted & {k.lower(), *(p.name.lower() for p in v)}),
        None,
    )


def validate(parts: list[Path]) -> None:
    for p in parts:
        if p.suffix.lower() != ".gguf":
            raise ModelError(f"'{p.name}' não é .gguf; este script só importa GGUF (veja o README).")
        if p.stat().st_size == 0:
            raise ModelError(f"'{p.name}' está vazio. O download falhou; baixe novamente.")
        with p.open("rb") as f:
            magic = f.read(4)
        if magic != b"GGUF":
            raise ModelError(f"'{p.name}' não é um GGUF válido (corrompido ou HTML salvo por engano).")
    if split := SPLIT.match(parts[0].name):
        if len(parts) != int(split[3]):
            raise ModelError(f"Modelo dividido incompleto: {len(parts)} de {int(split[3])} partes.")


def import_gguf(display: str, parts: list[Path]) -> str:
    """Envia o(s) arquivo(s) e registra no Ollama. Registrar não garante que o modelo execute."""
    name = ollama_name(display)
    try:
        validate(parts)
        files = {p.name: client.create_blob(p) for p in parts}
        client.create(model=name, files=files)
    except ollama.ResponseError as e:
        raise ModelError(f"O Ollama recusou '{display}': {e.error}") from None
    except ConnectionError:
        raise ModelError("O Ollama ficou indisponível durante a importação.") from None
    except OSError as e:  # vem depois de ConnectionError (subclasse de OSError)
        raise ModelError(f"Não foi possível ler '{e.filename or display}': {e.strerror or e}") from None
    return name
