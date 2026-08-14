#!/usr/bin/env python3
"""
Seed script for taxonomy_values table.
Fills Axis A, Axis B, and Axis C definitions into SQLite database.
"""

import sqlite3
import sys
from pathlib import Path

TAXONOMY_SEED = [
    # Axis A — Cognitive Demand
    ("A", "pamiec", "Pure recall: numbers, fines, periods, thresholds"),
    ("A", "rozumienie", "Understanding a mechanism, e.g. physics of braking"),
    ("A", "zastosowanie", "Apply a rule to a situation"),
    ("A", "analiza", "Multi-step reasoning"),

    # Axis B — Content Domain
    ("B", "znaki_i_sygnaly", "Road signs and traffic signals"),
    ("B", "pierwszenstwo", "Right of way rules"),
    ("B", "manewry_i_pozycja", "Vehicle maneuvers and lane position"),
    ("B", "predkosc_i_odleglosci", "Speed limits and safety distances"),
    ("B", "technika_pojazdu", "Vehicle operation and tech/physics"),
    ("B", "administracja_i_kary", "Administrative rules, documents, fines"),
    ("B", "pierwsza_pomoc", "First aid procedures"),
    ("B", "ekologia", "Eco-driving and environmental rules"),

    # Axis C — Item Quality
    ("C", "podwojne_przeczenie", "Double negative phrasing"),
    ("C", "pedanteria", "Overly pedantic phrasing (e.g. 'więcej niż 50' vs '50')"),
    ("C", "czysta_pamieciowka", "Pure memorization item"),
    ("C", "brak_pulapki", "Straightforward question with no trick phrasing")
]

def seed_taxonomy(db_path: Path):
    """Insert or replace taxonomy seed values into SQLite."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT OR REPLACE INTO taxonomy_values (axis, value, definition)
        VALUES (?, ?, ?)
        """,
        TAXONOMY_SEED
    )
    conn.commit()
    conn.close()
    print(f"Successfully seeded {len(TAXONOMY_SEED)} taxonomy values into {db_path}")

def main():
    project_root = Path(__file__).resolve().parent.parent
    db_path = project_root / "data" / "prawko.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    seed_taxonomy(db_path)

if __name__ == "__main__":
    main()
