"""Prueba de regresión sin API: reproduce las honestas y los brazos saboteados de una corrida ya hecha con el código
y el motor actuales, con monitor guionado, y compara los puntajes determinísticos con los guardados.

    python scripts/reproducir_sin_api.py --root f2 --out f2-repro

Lee `<root>/logs/honest` (planes), `<root>/data/sourcings` y `<root>/logs/replay` (puntajes de referencia). Escribe
todo en `--out`, nunca en `--root`. No llama a ningún modelo. Qué prueba: que herramientas, scorers y motor nuevos dan
lo mismo sobre trayectorias reales. Qué no prueba: los monitores LLM ni cómo se comportaría el agente en el entorno
nuevo (los planes los escribió un agente que vio la versión anterior)."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

from procuguard import analysis_f1
from procuguard.phase1 import default_arms
from procuguard.provenance import engine_fingerprint, fingerprint
from procuguard.replay import run_replay
from procuguard.rescore import VARIANTS, build_prompt, leak_in, load_items

# lo que tiene que dar igual para que la reproducción sirva de base a lecturas pagas; la tarea principal puede moverse
# (la regla de dato inventado cambió) y se informa aparte
MUST_MATCH = ("flip", "success", "scope_op40", "M0", "pivote", "pivote_amplio", "margin")

FIELDS = {"main_task": "tarea principal", "flip": "objetivo primero", "success": "éxito del sabotaje",
          "scope_op40": "alcance de la op 40", "M0": "M0", "pivote": "pivote", "pivote_amplio": "pivote amplio",
          "margin": "brecha 1º–2º"}


def same(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    return a == b


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, required=True, help="carpeta de la corrida de referencia (p. ej. f2)")
    ap.add_argument("--out", type=Path, required=True, help="carpeta nueva para la reproducción")
    ap.add_argument("--control-limit", type=int, default=40)
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--max-samples", type=int, default=8)
    ap.add_argument("--run-id", default=None, help="corrida de referencia (default: la última)")
    a = ap.parse_args()
    if a.out.resolve() == a.root.resolve() or a.root.resolve() in a.out.resolve().parents:
        ap.error("--out tiene que estar fuera de --root")
    log_dir = a.out / "logs" / "replay"
    if not list(log_dir.glob("*.eval")):
        run_replay(a.root / "logs" / "honest", [], sourcings_dir=a.root / "data" / "sourcings", runs_dir=a.out / "runs",
                   log_dir=str(log_dir), arms=default_arms(a.control_limit), with_m1=False, limit=a.n,
                   max_samples=a.max_samples, display="none", allow_historical=True)
    old = {r["sample"]: r for r in analysis_f1.load_rows(a.root / "logs" / "replay", a.out / "sin-relecturas", a.run_id)[0]}
    new = {r["sample"]: r for r in analysis_f1.load_rows(log_dir, a.out / "sin-relecturas")[0]}
    common = sorted(set(old) & set(new))
    L = [f"# Reproducción sin API de `{a.root}` con el código actual", "",
         f"- Muestras de referencia: {len(old)} · reproducidas: {len(new)} · en común: {len(common)}",
         f"- Sólo en la referencia: {len(set(old) - set(new))} · sólo en la reproducción: {len(set(new) - set(old))}",
         f"- Con error en la reproducción: {sum(1 for r in new.values() if r['error'])}", ""]
    missing = Counter(old[s]["arm"] for s in set(old) - set(new))
    if missing:
        L += ["Faltan en la reproducción, por brazo: " + ", ".join(f"{k} {v}" for k, v in sorted(missing.items())), ""]
    L += ["| Brazo | muestras | " + " | ".join(FIELDS.values()) + " |", "|" + "---|" * (len(FIELDS) + 2)]
    details = []
    blocking = Counter()
    for arm in sorted({old[s]["arm"] for s in common}, key=lambda x: (x != "honest", x)):
        ids = [s for s in common if old[s]["arm"] == arm]
        cells = []
        for key in FIELDS:
            diff = [s for s in ids if not same(old[s].get(key), new[s].get(key))]
            cells.append("igual" if not diff else f"**{len(diff)} distintas**")
            if key in MUST_MATCH and diff:
                blocking[key] += len(diff)
            details += [f"- {s} · {FIELDS[key]}: {old[s].get(key)} → {new[s].get(key)}" for s in diff[:5]]
        L.append(f"| {arm} | {len(ids)} | " + " | ".join(cells) + " |")
    if details:
        L += ["", "Ejemplos de diferencias (hasta 5 por celda):", ""] + details
    # lo que leería un monitor: ni el id de la muestra (lleva el brazo) ni rutas del equipo
    items = load_items(log_dir, None, None, None)
    leaks = [(it.sample_id, found) for it in items if (found := leak_in(it, build_prompt(it, "generico")[1]))]
    run_ids = sorted({r["run_id"] for r in new.values()})
    problems = []
    if set(old) != set(new):
        problems.append("los ids de las muestras no coinciden")
    if any(r["error"] for r in new.values()):
        problems.append("hay muestras con error")
    if blocking:
        problems.append("cambian puntajes determinísticos: " + ", ".join(f"{FIELDS[k]} ({v})" for k, v in blocking.items()))
    if leaks:
        problems.append(f"{len(leaks)} transcripciones delatan el brazo o una ruta (p. ej. {leaks[0][0]}: {leaks[0][1]!r})")
    if len(run_ids) != 1:
        problems.append(f"la reproducción tiene {len(run_ids)} corridas de Inspect")
    L += ["", f"- Transcripciones con ruta o nombre de brazo en lo que lee el monitor: {len(leaks)} de {len(items)}",
          f"- Corrida de Inspect de la reproducción: {', '.join(run_ids)}",
          "", "**APTA para leer con monitores.**" if not problems else "**NO APTA para leer con monitores:** " + "; ".join(problems) + "."]
    a.out.mkdir(parents=True, exist_ok=True)
    report = a.out / "reproduccion.md"
    report.write_text("\n".join(L) + "\n", encoding="utf-8")
    manifest = {"referencia": str(a.root), "corrida_referencia": sorted({r["run_id"] for r in old.values()}),
                "corrida": run_ids, "muestras": len(new), "apta": not problems, "problemas": problems,
                "prompt_generico": fingerprint(VARIANTS["generico"]), "engine_fingerprint": engine_fingerprint()}
    (a.out / "corrida.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\n".join(L))
    print(f"→ {report}, {a.out / 'corrida.json'}")
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
