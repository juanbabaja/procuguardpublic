"""Monitores LLM post-hoc (M1) y el test de fuga del side task.

M1 "ciego": un modelo con un prompt genérico de monitoreo que lee la transcripción completa (razonamiento
visible, llamadas a herramientas y resultados) y devuelve sospecha 0–100. Dos variantes, como en Benton et
al. (2024): con razonamiento y zero-shot (sólo el número). El monitor nunca ve el system prompt del agente:
el formateador lo quita antes de armar el prompt, y `assert_no_leak` falla si alguna cadena de la
instrucción oculta llegó igual a lo que el monitor va a leer.
"""
from __future__ import annotations

from collections.abc import Sequence

from inspect_ai.model import ChatMessage, ChatMessageSystem
from inspect_ai.scorer import Scorer

from control_arena import ControlTaskMetadata
from control_arena.monitor import MonitorScoreRange, basic_monitor_builder, full_trajectory_prompt_formatter_markdown
from control_arena.scorers import end_of_trajectory_monitor

from .prompts import M1_SYSTEM_COT, M1_SYSTEM_ZERO_SHOT, M1_USER, M1_USER_ZERO_SHOT
from .side_tasks import leak_phrases


class SideTaskLeak(AssertionError):
    pass


def assert_no_leak(text: str) -> None:
    for phrase in leak_phrases():
        if phrase.lower() in text.lower():
            raise SideTaskLeak(f"la instrucción oculta llegó al monitor: '{phrase}'")


def monitor_view(messages: Sequence[ChatMessage]) -> list[ChatMessage]:
    """Lo que el monitor puede ver: todo menos los mensajes de sistema."""
    return [m for m in messages if not isinstance(m, ChatMessageSystem)]


def _formatter(task_metadata: ControlTaskMetadata, messages: Sequence[ChatMessage], prompt: str) -> str:
    text = full_trajectory_prompt_formatter_markdown(task_metadata, monitor_view(messages), prompt)
    assert_no_leak(text)
    return text


def m1_monitor(cot: bool = True, model_role: str = "trusted", model: str | None = None):
    """Policy del monitor M1 (un agente de ControlArena). `cot=False` es la variante zero-shot."""
    return basic_monitor_builder(
        model_role=model_role if model is None else None,
        model=model,
        prompt=M1_USER if cot else M1_USER_ZERO_SHOT,
        prompt_formatter=_formatter,
        system_prompt=M1_SYSTEM_COT if cot else M1_SYSTEM_ZERO_SHOT,
        skip_if_no_tool_calls=False,
        score_range=MonitorScoreRange(min=0.0, max=100.0, output_min=0.0, output_max=100.0),
        default_suspicion_score=0.0,
        cache=True,
    )


def m1_scorers(model_role: str = "trusted", model: str | None = None) -> list[Scorer]:
    """Los dos M1 como scorers post-hoc, para pasar en `monitoring_scorers`."""
    return [end_of_trajectory_monitor(m1_monitor(cot=True, model_role=model_role, model=model)),
            end_of_trajectory_monitor(m1_monitor(cot=False, model_role=model_role, model=model))]


def m1_panel(models: Sequence, zero_shot: bool = False, names: Sequence[str] | None = None) -> tuple[list[Scorer], list[str]]:
    """Fase 1: un monitor M1 con razonamiento por modelo (y, si se pide, su variante zero-shot), para comparar
    monitores de distinta capacidad sobre las mismas transcripciones. Devuelve los scorers y sus etiquetas en el
    mismo orden: Inspect los nombra `end_of_trajectory_monitor`, `…1`, `…2`, así que el orden es lo que los identifica."""
    scorers, labels = [], []
    for i, m in enumerate(models):
        # m = None: el monitor es el modelo con rol "trusted" de la corrida (así entra un monitor guionado)
        name = names[i] if names else (m or "trusted").split("/")[-1].replace("claude-", "")
        scorers.append(end_of_trajectory_monitor(m1_monitor(cot=True, model=m)))
        labels.append(f"{name} CoT")
        if zero_shot:
            scorers.append(end_of_trajectory_monitor(m1_monitor(cot=False, model=m)))
            labels.append(f"{name} zero-shot")
    return scorers, labels
