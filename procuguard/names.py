"""Nombres ficticios para los sourcings sintéticos. Ningún proveedor, PN ni proyecto es real."""
from __future__ import annotations

# (razón social, planta, km a Zárate)
SUPPLIERS: list[tuple[str, str, float]] = [
    ("Estampados del Litoral S.A.", "Campana", 25),
    ("Metalúrgica Paranaense S.R.L.", "San Nicolás", 115),
    ("Troqueles Pampa S.A.", "Pilar", 55),
    ("Autopartes Río Luján S.A.", "Luján", 70),
    ("Matricería Del Plata S.R.L.", "Escobar", 40),
    ("Conformados Sur S.A.", "Baradero", 50),
    ("Industrias Cuyo Metal S.A.", "Villa Mercedes", 720),
    ("Estampería Norte Grande S.R.L.", "Tigre", 60),
    ("Herrajes Centeno S.A.", "Zárate", 8),
    ("Prensados Mesopotamia S.A.", "Gualeguaychú", 190),
    ("Metalmecánica Arroyo Seco S.A.", "Rosario", 215),
    ("Chapas y Matrices Garay S.R.L.", "Campana", 20),
]

CONTACTS = ["M. Ferreyra", "L. Quiroga", "S. Benítez", "P. Iturralde", "R. Almada", "C. Villalba",
            "N. Sosa", "A. Ledesma", "F. Carrizo", "G. Medina", "J. Acuña", "V. Paz"]

TOOLMAKERS_LOCAL = ["Matricería Belgrano", "Troqueles Rivadavia", "Herramental Sarmiento", "Matrices Ituzaingó"]
TOOLMAKERS_CHINA = ["Ningbo Daxing Mould", "Suzhou Hengli Tooling", "Dongguan Yuanfeng Die"]

PART_NAMES = [
    "REINFORCEMENT, FR SIDE MEMBER",
    "BRACKET, ENGINE MOUNTING",
    "MEMBER, FR SEAT INNER",
    "ARM, RR BUMPER, OUTER",
    "SUPPORT, RADIATOR UPPER",
    "GUSSET, QUARTER PANEL",
    "BRACKET, FUEL TANK BAND",
    "REINFORCEMENT, ROCKER OUTER",
    "MEMBER SUB-ASSY, RR FLOOR SIDE",
    "BRACKET, HEADLAMP MOUNTING",
    "PLATE, DOOR HINGE",
    "SUPPORT, BATTERY CARRIER",
]

PROJECT = "Proyecto 9ZZ (sintético)"
PACKAGE = "9ZZ"
TIS_ECOAT = "SPEC-ECOAT-01"
