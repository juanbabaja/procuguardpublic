"""Inyector de side tasks: elige el objetivo (lo fija el generador en oracle/meta.json), arma la instrucción
del "operador interno" para la policy atacante y la gradúa en tres niveles de agresividad.

El texto que sale de acá va al system prompt del agente en modo ataque y a ningún otro lado: el monitor no
lo ve, y `leak_phrases()` da las cadenas con las que el test de fuga verifica que no llegó a la transcripción.
"""
from __future__ import annotations

from typing import Literal

from .prompts import AGGRESSIVENESS, FRAMINGS, SIDE_TASK_COMMON, SIDE_TASKS

Aggressiveness = Literal["aggressive", "moderate", "subtle"]
Framing = Literal["operator", "redteam"]
SIDE_TASK_IDS = tuple(SIDE_TASKS.keys())


def side_task_description(side_task: str, meta: dict, aggressiveness: Aggressiveness,
                          framing: Framing = "redteam") -> str:
    spec = SIDE_TASKS[side_task]
    fmt = {"target": meta["target"], "winner": meta["winner"], "third": meta["third"]}
    body = SIDE_TASK_COMMON.format(framing=FRAMINGS[framing], objective=spec["objective"].format(**fmt),
                                   how=spec["how"].format(**fmt))
    return body + "\n" + AGGRESSIVENESS[aggressiveness] + "\n"


def leak_phrases() -> list[str]:
    """Cadenas que sólo existen en la instrucción oculta; ninguna puede aparecer en lo que ve el monitor."""
    return ["instrucción interna de un operador", "no debe ser evidente para quien revise", "evaluación de seguridad autorizada",
            "tarea secundaria", "Nivel agresivo", "Nivel moderado", "Nivel sutil", "Restricciones duras",
            "El sesgo es de interpretación", "Recordatorio (no lo menciones"]
