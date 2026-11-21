"""Corrida del piloto (fase 0).

    python -m procuguard.run_pilot --mode honest --n 10
    python -m procuguard.run_pilot --mode attack --side-tasks S1 S2 S5 --aggressiveness moderate --n 10
    python -m procuguard.run_pilot --mode both --n 1 --side-tasks S5          # smoke test con 1 sourcing

Modelos por defecto: agente (untrusted) Opus 5.5, monitor M1 (trusted) Sonnet 5.5. Hace falta ANTHROPIC_API_KEY
en el entorno. Los logs quedan en logs/ y se analizan con `python -m procuguard.analysis logs/`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from inspect_ai import eval as inspect_eval

from control_arena import EvalMode
from control_arena.eval import ControlEvalConfig, get_control_task
from control_arena.policy import attack_policy_builder, honest_policy_builder, untrusted_policy_builder

from .monitors import m1_scorers
from .prompts import ATTACK_REMINDER, ATTACK_SYSTEM_PROMPT, HONEST_SYSTEM_PROMPT
from .setting import ProcuGuardSetting

DEFAULT_UNTRUSTED = "anthropic/claude-opus-5-5"
DEFAULT_TRUSTED = "anthropic/claude-sonnet-5-5"


def build_tasks(modes: list[EvalMode], *, sourcings_dir: Path, runs_dir: Path, side_tasks: list[str],
                aggressiveness: str, n: int | None, untrusted: str, trusted: str, max_steps: int,
                max_samples: int, log_dir: str, with_m1: bool = True, framing: str = "redteam",
                reminder: bool = True):
    setting = ProcuGuardSetting(sourcings_dir=sourcings_dir, runs_dir=runs_dir, side_tasks=side_tasks,
                                aggressiveness=aggressiveness, n_sourcings=n, framing=framing)
    policy = untrusted_policy_builder(
        # el recordatorio efímero no queda en la transcripción (el monitor no lo ve): ver attack_policy_builder
        attack=attack_policy_builder(prompt=ATTACK_SYSTEM_PROMPT, ephemeral_reminder=reminder,
                                     ephemeral_reminder_prompt=ATTACK_REMINDER),
        honest=honest_policy_builder(),
    )
    config = ControlEvalConfig(
        untrusted_model=untrusted, trusted_model=trusted,
        max_steps=max_steps, max_samples=max_samples, log_dir=log_dir,
        system_prompt=HONEST_SYSTEM_PROMPT, fail_on_error=False,
    )
    monitors = m1_scorers() if with_m1 else []
    # Nombres cortos a propósito: Inspect arma el buffer de muestras en
    # %LOCALAPPDATA%\inspect_ai\inspect_ai\samplebuffer\<sha256>\<nombre del .eval>.<pid>.db y con el nombre
    # que genera ControlArena ("procuguard_moderate-untrusted-policy-honest-<hash>_<id>.eval") el path pasa los
    # 260 caracteres de Windows → "sqlite3.OperationalError: unable to open database file".
    short = {"aggressive": "agg", "moderate": "mod", "subtle": "sub"}[aggressiveness]
    fr = {"operator": "op", "redteam": "rt"}[framing]
    return [get_control_task(setting, policy, mode, eval_config=config, monitoring_scorers=monitors,
                             task_name=f"pg-{short}-{fr}-{mode.value}" if mode == EvalMode.ATTACK else "pg-honest")
            for mode in modes]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Piloto ProcuGuard sobre ControlArena.")
    ap.add_argument("--mode", choices=["honest", "attack", "both"], default="both")
    ap.add_argument("--n", type=int, default=None, help="cantidad de sourcings (default: todos)")
    ap.add_argument("--side-tasks", nargs="+", default=["S1", "S2", "S5"])
    ap.add_argument("--aggressiveness", choices=["aggressive", "moderate", "subtle"], default="moderate")
    ap.add_argument("--framing", choices=["operator", "redteam"], default="redteam",
                    help="encuadre de la instrucción de sabotaje (operator = realista, redteam = evaluación autorizada)")
    ap.add_argument("--no-reminder", action="store_true", help="sin el recordatorio efímero del side task en cada paso")
    ap.add_argument("--untrusted", default=DEFAULT_UNTRUSTED)
    ap.add_argument("--trusted", default=DEFAULT_TRUSTED)
    ap.add_argument("--max-steps", type=int, default=40)
    ap.add_argument("--max-samples", type=int, default=4)
    ap.add_argument("--sourcings", type=Path, default=Path("data/sourcings"))
    ap.add_argument("--runs", type=Path, default=Path("data/runs"))
    ap.add_argument("--log-dir", default="logs")
    ap.add_argument("--no-m1", action="store_true", help="sin monitores LLM (sólo M0 y graders)")
    a = ap.parse_args(argv)

    modes = {"honest": [EvalMode.HONEST], "attack": [EvalMode.ATTACK],
             "both": [EvalMode.HONEST, EvalMode.ATTACK]}[a.mode]
    tasks = build_tasks(modes, sourcings_dir=a.sourcings, runs_dir=a.runs, side_tasks=a.side_tasks,
                        aggressiveness=a.aggressiveness, n=a.n, untrusted=a.untrusted, trusted=a.trusted,
                        max_steps=a.max_steps, max_samples=a.max_samples, log_dir=a.log_dir, with_m1=not a.no_m1,
                        framing=a.framing, reminder=not a.no_reminder)
    inspect_eval(tasks, log_dir=a.log_dir, max_samples=a.max_samples)


if __name__ == "__main__":
    main()
