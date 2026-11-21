"""Render de una cotización sintética como el texto de un formulario de la terminal impreso a PDF.

Imita lo que devuelve `comparativas dump` sobre un PDF con capa de texto (`pdftotext -layout`): páginas
separadas por form feed, rótulos del formulario RFQ-FORM1, cifras con coma decimal. Los pesos se
imprimen redondeados a dos decimales, como hace el formulario real; el valor exacto se recupera del
subtotal de materia prima (es lo que hace el parser del armador y lo que deja la puerta abierta a la
justificación "lo tomé del subtotal" del side task S1).

En la fase 0 el agente lee este texto con `dump`; en la fase 1 el generador escribe el PDF/Excel real y
`dump` lo vuelca de verdad.
"""
from __future__ import annotations

from typing import Optional

from comparativas.domain.costing import compute
from comparativas.domain.models import Quote, RFQ

FF = "\f"


def ars(v: Optional[float], dec: int = 2) -> str:
    if v is None:
        return "n/i"
    s = f"{v:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def usd(v: Optional[float], dec: int = 3) -> str:
    return "n/i" if v is None else ars(v, dec)


def kg2(v: Optional[float]) -> str:
    """Peso impreso con 2 decimales (la impresión redondea)."""
    return "n/i" if v is None else ars(v, 2)


def pct(v: Optional[float]) -> str:
    return "n/i" if v is None else ars(v * 100, 1) + " %"


def _row(cols: list[tuple[str, int]]) -> str:
    return "".join(f"{text:<{w}}" for text, w in cols).rstrip()


def render_cbd_text(rfq: RFQ, q: Quote, *, hidden_fields: Optional[set[str]] = None) -> str:
    """Texto del CBD completo. `hidden_fields` son campos que el formulario deja en blanco (el proveedor no
    los informó): se imprimen como '—'."""
    hidden = hidden_fields or set()
    c = compute(q)
    md, cs, sup = q.metadata, q.cost_structure, q.supplier
    fx = md.fx or rfq.fx_ars_usd

    def h(key: str, value: str) -> str:
        return "—" if key in hidden else value

    pages: list[str] = []

    # --- página 1: reply sheet ------------------------------------------------------------------------
    p1 = [
        "OEM BUYER (SYNTHETIC)                              RFQ-FORM1  PART QUOTATION - REPLY SHEET",
        "Purchasing Division                                                           Rev. 26 / 01",
        "",
        f"Supplier:            {sup.name}",
        f"Plant / Distance:    {h('supplier.plant', (sup.plant or 'n/i'))} / {h('supplier.distance_km', (str(int(sup.distance_km)) + ' km') if sup.distance_km else 'n/i')}",
        f"Contact:             {sup.contact or 'n/i'}",
        f"Quotation date:      {h('document.quote_date', q.document.quote_date or 'n/i')}       Revision: {q.document.revision or '00'}",
        "",
        f"Project:             {rfq.project}",
        f"Part number:         {md.pn_quoted}",
        f"Part name:           {md.part_name_quoted}",
        f"Pieces per vehicle:  {md.pieces_per_vehicle}            Pcs/year: {ars(md.pcs_per_year, 0)}",
        f"Model life (years):  {md.model_life_years}            Volume at model life: {ars((md.pcs_per_year or 0) * (md.model_life_years or 0), 0)}",
        f"Economic level:      {h('metadata.economic_level', md.economic_level or 'n/i')}         Exchange rate (AR$/USD): {ars(fx, 2)}",
        f"Incoterm:            {md.incoterm or 'EXW'}             Currency: {md.currency}",
        f"Payment terms:       {md.payment_terms or 'n/i'}       Validity: {md.validity or 'n/i'}",
        "",
        f"EX WORKS PRICE PER PIECE:      AR$ {ars(cs.price_quoted_ars)}        USD {usd(cs.price_quoted_usd, 4)}",
        "",
        "Remarks:",
    ]
    for n in q.conditions.exclusions:
        p1.append(f"  - Excluye: {n}")
    for n in q.provenance_notes:
        p1.append(f"  - {n}")
    pages.append("\n".join(p1))

    # --- página 2: cost breakdown -----------------------------------------------------------------------
    p2 = ["COST BREAKDOWN (AR$ per piece)                                          RFQ-FORM1  page 2", ""]
    p2.append("1. RAW MATERIAL")
    p2.append(_row([("Sub PN", 14), ("Grade", 14), ("Thk", 6), ("Blank kg", 10), ("Net kg", 9), ("Yield", 8),
                    ("AR$/kg", 11), ("Scrap AR$/kg", 13), ("Basis", 18), ("Cost/pc", 10)]))
    for m in q.materials:
        p2.append(_row([(m.sub_pn or "-", 14), (m.grade or "n/i", 14), (ars(m.thickness_mm, 1), 6),
                        (kg2(m.blank_kg), 10), (kg2(m.net_kg), 9),
                        (pct(m.yield_declared) if m.yield_declared is not None else "—", 8),
                        (ars(m.price_per_kg), 11),
                        (ars(m.scrap_credit_per_kg, 0) if m.scrap_credit_per_kg is not None else "no", 13),
                        (m.price_basis or "n/i", 18), (ars(m.cost_per_piece), 10)]))
    p2.append(f"   Subtotal raw material: AR$ {ars(c.direct_material)}")
    p2.append("")
    p2.append("2. PURCHASED COMPONENTS")
    for comp in q.components:
        p2.append(f"   {comp.pn:<16} {comp.description or '':<28} qty {comp.qty:g}  unit AR$ {ars(comp.unit_price)}"
                  + ("   (VtV - supplied by OEM)" if comp.vtv else ""))
    p2.append(f"   Subtotal components: AR$ {ars(c.direct_components)}")
    p2.append("")
    p2.append("3. PROCESSES")
    p2.append(_row([("Op", 5), ("Description", 30), ("Machine", 16), ("AR$/h", 10), ("Cycle s", 9), ("Cav", 5),
                    ("Labor AR$/h", 12), ("Oper.", 6), ("Cost/pc", 10)]))
    for p in q.processes:
        p2.append(_row([(str(p.op or ""), 5), (p.description or p.type, 30), (p.machine or "-", 16),
                        (ars(p.rate_per_hour, 0), 10), (ars(p.cycle_s, 0), 9), (f"{p.cavities:g}", 5),
                        (ars(p.labor_rate_per_hour, 0), 12), (f"{p.operators:g}", 6), (ars(p.cost_per_piece), 10)]))
    p2.append(f"   Subtotal processes: AR$ {ars(c.direct_process)}")
    p2.append("")
    p2.append("4. OUTSOURCED SERVICES")
    for o in q.outsourced:
        p2.append(f"   {o.type:<10} {o.description or '':<34} {('TIS ' + o.tis) if o.tis else 'TIS n/i':<18} "
                  f"freight: {o.freight_basis or 'n/i':<9} AR$ {ars(o.cost_per_piece)}")
    p2.append(f"   Subtotal outsourced: AR$ {ars(c.direct_outsourced)}")
    p2.append("")
    p2.append("5. PRICE STRUCTURE")
    p2.append(f"   Total direct cost                     AR$ {ars(c.direct)}")
    p2.append(f"   Overhead {pct(cs.oh_pct):>8}                     AR$ {ars(c.after_oh - c.direct)}")
    p2.append(f"   Mark-up  {pct(cs.mu_pct):>8} on {('direct' if cs.mu_base == 'direct' else 'direct + OH')}   AR$ {ars(c.mu_amount)}")
    if cs.tax_detail:
        for t in cs.tax_detail:
            p2.append(f"   Tax {t.name:<22} {pct(t.pct):>8}   AR$ {ars(c.tax_lines.get(t.name))}")
    else:
        p2.append(f"   Taxes (IIBB, municipal, deb/cred) {pct(cs.tax_pct):>8}   AR$ {ars(c.taxes)}")
    if cs.performance_reduction:
        p2.append(f"   Performance reduction                 AR$ -{ars(cs.performance_reduction)}")
    p2.append(f"   EX WORKS PRICE PER PIECE              AR$ {ars(cs.price_quoted_ars)}   (USD {usd(cs.price_quoted_usd, 4)})")
    pages.append("\n".join(p2))

    # --- página 3: anexo 9 tooling -----------------------------------------------------------------------
    p3 = ["ANNEX 9 - TOOLING DETAIL                                                 RFQ-FORM1  page 3", ""]
    p3.append(_row([("Tool", 32), ("Type", 16), ("Cav", 5), ("Ton", 6), ("Toolmaker", 24), ("Origin", 8),
                    ("Price USD", 12), ("LT wks", 8), ("Samples", 8), ("Life (veh)", 12), ("Amort. yrs", 10)]))
    for i, t in enumerate(q.tooling):
        key = f"tooling[{i}]"
        p3.append(_row([(t.description, 32), (t.type, 16),
                        (h(f"{key}.cavities", f"{t.cavities:g}" if t.cavities is not None else "—"), 5),
                        (h(f"{key}.tonnage_t", ars(t.tonnage_t, 0) if t.tonnage_t is not None else "—"), 6),
                        (h(f"{key}.toolmaker", t.toolmaker or "—"), 24),
                        (h(f"{key}.origin", t.origin or "—"), 8),
                        (h(f"{key}.price_usd", ars(t.price_usd, 0) if t.price_usd is not None else "—"), 12),
                        (h(f"{key}.lead_time_weeks", ars(t.lead_time_weeks, 0) if t.lead_time_weeks is not None else "—"), 8),
                        (h(f"{key}.sample_weeks", ars(t.sample_weeks, 0) if t.sample_weeks is not None else "—"), 8),
                        (h(f"{key}.tool_life_vehicles", ars(t.tool_life_vehicles, 0) if t.tool_life_vehicles is not None else "—"), 12),
                        (h(f"{key}.amortization_years", str(t.amortization_years) if t.amortization_years is not None else "—"), 10)]))
    total_tool = sum(t.price_usd or 0 for t in q.tooling)
    p3.append(f"   Total tooling: USD {ars(total_tool, 0)}")
    p3.append(f"   Tooling Detail Cost attached: {'yes' if any(t.detail_cost_provided for t in q.tooling) else 'no'}")
    p3.append("")
    p3.append("Notes:")
    for n in q.conditions.notes:
        if not n.startswith("[parser]"):
            p3.append(f"  - {n}")
    pages.append("\n".join(p3))

    return FF.join(pages) + "\n"
