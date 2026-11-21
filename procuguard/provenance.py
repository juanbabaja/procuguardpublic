"""Identidad de los datos, el motor y las muestras de evaluación."""
from __future__ import annotations

import json
from functools import lru_cache
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

import comparativas
from comparativas.infrastructure.paths import BENCHMARKS_FILE, RULES_FILE


def fingerprint(value) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(data.encode("utf-8")).hexdigest()


def _files_fingerprint(root: Path, paths) -> str:
    entries = [(path.relative_to(root).as_posix(), sha256(path.read_bytes()).hexdigest())
               for path in sorted(paths) if path.is_file()]
    return fingerprint(entries)


@lru_cache(maxsize=1)
def engine_fingerprint() -> str:
    package = Path(comparativas.__file__).resolve().parent
    settings = {p.name: sha256(p.read_bytes()).hexdigest() if p.is_file() else None
                for p in (BENCHMARKS_FILE, RULES_FILE)}
    return fingerprint({"code": _files_fingerprint(package, package.rglob("*.py")), "settings": settings,
                        "versions": {name: version(name) for name in ("comparativas", "inspect-ai", "control-arena")}})


def case_fingerprint(folder: Path) -> str:
    inputs = [folder / "rfq.json", *folder.glob("quotes/*.json"), *folder.glob("ts/*.json"),
              *folder.glob("source_docs/*.cbd.txt"), *folder.glob("oracle/*.json"), *folder.glob("oracle/quotes/*.json")]
    return _files_fingerprint(folder, inputs)


def sample_reference(log, sample) -> str:
    return fingerprint({"eval": log.eval.eval_id, "run": log.eval.run_id, "sample": str(sample.id),
                        "epoch": sample.epoch, "metadata": sample.metadata,
                        "messages": [message.model_dump(mode="json") for message in sample.messages]})
