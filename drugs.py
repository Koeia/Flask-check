"""Drug data store.

The original Express app wiped and reseeded a SQLite table from drugData.json on
every start, so the JSON file was already the source of truth. Here it is simply
loaded into memory once; ~200 records need no database.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "drugData.json"


@dataclass(frozen=True)
class SideEffect:
    effect: str
    prevalence: str  # COMMON | UNCOMMON | RARE


@dataclass(frozen=True)
class Drug:
    id: int
    name: str
    generic_name: str
    medline_id: str
    drug_class: str
    common_use: list[str] = field(default_factory=list)
    side_effects: list[SideEffect] = field(default_factory=list)
    precautions: list[str] = field(default_factory=list)
    notes: str | None = None

    @property
    def medline_url(self) -> str:
        return f"https://medlineplus.gov/druginfo/meds/{self.medline_id}.html"

    @property
    def show_generic(self) -> bool:
        return bool(self.generic_name) and self.generic_name.lower() != self.name.lower()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "genericName": self.generic_name,
            "medlineID": self.medline_id,
            "drugClass": self.drug_class,
            "commonUse": self.common_use,
            "sideEffects": [
                {"effect": s.effect, "prevalence": s.prevalence} for s in self.side_effects
            ],
            "precautions": self.precautions,
            "notes": self.notes,
        }


class DrugStore:
    def __init__(self, drugs: list[Drug]):
        self.drugs = drugs

    @classmethod
    def from_json(cls, path: Path = DATA_PATH) -> "DrugStore":
        raw = json.loads(path.read_text(encoding="utf-8"))
        drugs = [
            Drug(
                id=i,
                name=d["name"],
                generic_name=d.get("genericName") or "",
                medline_id=d["medlineID"],
                drug_class=d["drugClass"],
                common_use=list(d.get("commonUse", [])),
                side_effects=[SideEffect(**s) for s in d.get("sideEffects", [])],
                precautions=list(d.get("precautions", [])),
                notes=d.get("notes"),
            )
            for i, d in enumerate(raw, start=1)
        ]
        return cls(drugs)

    def find(self, query: str) -> Drug | None:
        """Exact brand name, then exact generic name, then first substring match."""
        q = query.strip().lower()
        if not q:
            return None
        for d in self.drugs:
            if d.name.lower() == q:
                return d
        for d in self.drugs:
            if d.generic_name.lower() == q:
                return d
        for d in self.drugs:
            if q in d.name.lower() or q in d.generic_name.lower():
                return d
        return None

    def search(self, names: list[str]) -> list[Drug | None]:
        return [self.find(n) for n in names]

    def autocomplete(self, query: str, limit: int = 8) -> list[Drug]:
        q = query.strip().lower()
        if len(q) < 2:
            return []
        return [
            d for d in self.drugs if q in d.name.lower() or q in d.generic_name.lower()
        ][:limit]

    def common_uses(self) -> list[str]:
        return sorted({u for d in self.drugs for u in d.common_use}, key=str.lower)
