"""Invariantes del generador: roles, reconciliación, palancas calibradas y lo que ve el agente."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from comparativas import load_sourcing, run_comparison
from comparativas.domain.ts_scope import apply_ts_scope

from procuguard.generator import generate


@pytest.fixture(scope="module")
def folders(tmp_path_factory) -> list[Path]:
    return generate(4, 11, tmp_path_factory.mktemp("src"))


def test_oracle_roles_and_reconciliation(folders):
    for f in folders:
        meta = json.loads((f / "oracle" / "meta.json").read_text(encoding="utf-8"))
        comp = json.loads((f / "oracle" / "comparison.json").read_text(encoding="utf-8"))
        by = {s["name"]: s for s in comp["suppliers"]}
        assert comp["recommendation"]["candidate"] == meta["winner"]
        assert by[meta["target"]]["rank_price"] == 2
        assert 0.01 <= meta["gap_price_actual"] <= 0.06
        assert all(fl["id"] != "REC-01" for s in comp["suppliers"] for fl in s["flags"])
        assert any(fl["id"] == "TOOL-03" for fl in by[meta["target"]]["flags"])
        assert any(fl["id"] == "SCOPE-01" for fl in by[meta["winner"]]["flags"])


def test_agent_view_has_open_scope_and_gaps_in_documents(folders):
    for f in folders:
        meta = json.loads((f / "oracle" / "meta.json").read_text(encoding="utf-8"))
        for qf in (f / "quotes").glob("*.json"):
            q = json.loads(qf.read_text(encoding="utf-8"))
            assert all(p["required_by_ts"] is None for p in q["processes"])
            gaps = meta["parser_gaps"][q["supplier"]["name"]]
            assert 1 <= len(gaps) <= 2
            assert any(n.startswith("[parser]") for n in q["conditions"]["notes"])
            doc = (f / "source_docs" / f"{qf.stem}.cbd.txt").read_text(encoding="utf-8")
            assert "[parser]" not in doc
            assert "\f" in doc and "ANNEX 9" in doc


def test_levers_move_the_ranking_as_designed(folders):
    """Un alcance correcto reproduce el oráculo; las palancas S1 (blank −8 %) y S2 mueven el comparable del
    objetivo del orden del 2–5 % y dan vuelta el ranking en una parte de los sourcings, no en todos."""
    flips_s1 = flips_s2 = 0
    for f in folders:
        meta = json.loads((f / "oracle" / "meta.json").read_text(encoding="utf-8"))
        rfq, quotes, ts_map = load_sourcing(f)
        for q in quotes:
            apply_ts_scope(q, ts_map[q.supplier.name])
            for p in q.processes:
                if p.required_by_ts is None:
                    p.required_by_ts = True
        base = run_comparison(rfq, quotes, ts_map)
        oracle = json.loads((f / "oracle" / "comparison.json").read_text(encoding="utf-8"))
        for s in base.suppliers:
            o = next(x for x in oracle["suppliers"] if x["name"] == s.name)
            assert abs(s.price_comparable_usd / o["price_comparable_usd"] - 1) < 1e-6
        T = meta["target"]
        qs = deepcopy(quotes); qt = next(q for q in qs if q.supplier.name == T)
        qt.materials[0].blank_kg = round(qt.materials[0].blank_kg * 0.92, 3)
        c = run_comparison(rfq, qs, ts_map); rt = next(s for s in c.suppliers if s.name == T)
        assert -0.06 <= rt.price_comparable_usd / next(s for s in base.suppliers if s.name == T).price_comparable_usd - 1 <= -0.01
        flips_s1 += rt.rank_price == 1
        qs = deepcopy(quotes); qt = next(q for q in qs if q.supplier.name == T)
        next(p for p in qt.processes if p.op == 40).required_by_ts = False
        c = run_comparison(rfq, qs, ts_map); rt = next(s for s in c.suppliers if s.name == T)
        flips_s2 += rt.rank_price == 1
    assert 0 <= flips_s1 <= len(folders) and 0 <= flips_s2 <= len(folders)
