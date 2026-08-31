"""FieldCharter / ScopeSpec construction.

Spec §7 (Construct the Object-Field), §23 (Supported corpus fractions),
§48 (FieldCharter/ScopeSpec schemas). Native filters combine through
union/intersection/difference into a machine-readable `ScopeSpec` (spec
§48: "a machine-readable expression tree"); derived fractions (spec §11,
§23.2 -- e.g. poet-life chronological proxies) are always labelled
`derived: True` with the exact rule stored, never silently presented as
native.
"""
from __future__ import annotations

import glob as _glob
import json
from dataclasses import dataclass, field as _dc_field
from pathlib import Path


@dataclass(frozen=True)
class PoemRecord:
    poem_id: int
    poet_slug: str
    poet_id: int
    cat_id: int
    path: Path


@dataclass(frozen=True)
class PoetRecord:
    poet_id: int
    slug: str
    birth_year_lunar_hijri: int | None
    death_year_lunar_hijri: int | None
    # the real corpus's own uncertainty flags (Phase 8 finding, P1.4
    # follow-up): a poet.json can carry a birth/death year that Ganjoor
    # itself marks estimated rather than certified. Exposed here, not yet
    # factored into `poet_life_overlaps_hijri_range()`'s matching logic --
    # that is a methodological call (should an estimated boundary still
    # count as a known one?) left for whoever next uses this field, not
    # silently decided here.
    valid_birth_date: bool | None = None
    valid_death_date: bool | None = None


def scan_poets(root: str | Path) -> list[PoetRecord]:
    """Real-corpus finding (Phase 8): the vendored corpus's poet.json uses
    `BirthYearInLHijri`/`DeathYearInLHijri` (plus `ValidBirthDate`/
    `ValidDeathDate` booleans) -- NOT `BirthYearLunarHijri`/
    `DeathYearLunarHijri`, which only the fixture (a naming error from
    P1.4, now corrected there too) ever used. Against the real corpus the
    old field names silently returned None for every poet, breaking the
    poet-life chronological proxy (spec §11/§23.2) with no error at all."""
    root = Path(root)
    poets: list[PoetRecord] = []
    for poet_json in sorted(root.glob("poets/*/poet.json")):
        data = json.loads(poet_json.read_text(encoding="utf-8"))
        poets.append(
            PoetRecord(
                poet_id=data["Id"],
                slug=poet_json.parent.name,
                birth_year_lunar_hijri=data.get("BirthYearInLHijri"),
                death_year_lunar_hijri=data.get("DeathYearInLHijri"),
                valid_birth_date=data.get("ValidBirthDate"),
                valid_death_date=data.get("ValidDeathDate"),
            )
        )
    return poets


def poet_life_overlaps_hijri_range(poets: list[PoetRecord], start: int, end: int) -> ScopeSpec:
    """Poet-life chronological proxy (spec §11, §23.2): "poets whose
    documented life interval overlaps a declared Hijri range." A poet
    missing either birth or death year is excluded (not silently assumed
    to overlap) -- an absent boundary is a blind zone, not evidence either
    way (spec §21: "date != Harmanian Time", and more basically, an
    unknown interval cannot be shown to overlap a known one)."""
    matching = [
        p
        for p in poets
        if p.birth_year_lunar_hijri is not None
        and p.death_year_lunar_hijri is not None
        and p.birth_year_lunar_hijri <= end
        and p.death_year_lunar_hijri >= start
    ]
    spec = ScopeSpec(kind="poet", poet_slug=matching[0].slug) if matching else ScopeSpec(kind="none")
    for p in matching[1:]:
        spec = union(spec, ScopeSpec(kind="poet", poet_slug=p.slug))
    return spec


def poet_life_proxy_charter(
    root: str | Path, start: int, end: int, purpose: str = "poet-life chronological proxy field"
) -> FieldCharter:
    """Builds a FieldCharter directly from a Hijri range, correctly
    labelled `derived=True` with the exact rule recorded (spec §11 —
    "The proxy rule becomes part of the Field Charter and travels with
    every result")."""
    poets = scan_poets(root)
    scope = poet_life_overlaps_hijri_range(poets, start, end)
    return FieldCharter(
        purpose=purpose,
        corpus_snapshot=str(root),
        scope_spec=scope,
        derived=True,
        derivation_rule=(
            f"poets whose documented life interval overlaps "
            f"{start}-{end} AH (poet-life chronological proxy, spec §11)"
        ),
    )


def scan_corpus(root: str | Path) -> list[PoemRecord]:
    """Walk `root/poets/<slug>/**/p*.json` (mini-ganjoor's own layout;
    real-corpus poem filenames differ but the same poets/<slug>/... shape
    holds, per ledger row P0.5's spot check) and return one PoemRecord per
    poem file. `_cat.json` and `poet.json` are skipped -- only poem files
    (whatever isn't one of those two reserved names) are picked up."""
    root = Path(root)
    records: list[PoemRecord] = []
    poet_ids: dict[str, int] = {}
    for poet_json in sorted(root.glob("poets/*/poet.json")):
        slug = poet_json.parent.name
        poet_ids[slug] = json.loads(poet_json.read_text(encoding="utf-8"))["Id"]

    for poem_path in sorted(root.glob("poets/*/**/*.json")):
        if poem_path.name in ("poet.json", "_cat.json"):
            continue
        slug = poem_path.parts[poem_path.parts.index("poets") + 1]
        data = json.loads(poem_path.read_text(encoding="utf-8"))
        records.append(
            PoemRecord(
                poem_id=data["Id"],
                poet_slug=slug,
                poet_id=poet_ids.get(slug, -1),
                cat_id=data["CatId"],
                path=poem_path,
            )
        )
    return records


@dataclass(frozen=True)
class ScopeSpec:
    """A machine-readable expression tree (spec §48). `kind` is one of
    "all", "poet", "union", "intersect", "difference". Atomic leaves
    (currently just "poet") resolve against a `list[PoemRecord]`; the
    combinators recurse over `left`/`right`."""

    kind: str
    poet_slug: str | None = None
    left: "ScopeSpec | None" = None
    right: "ScopeSpec | None" = None

    def resolve(self, records: list[PoemRecord]) -> set[int]:
        if self.kind == "none":
            return set()
        if self.kind == "all":
            return {r.poem_id for r in records}
        if self.kind == "poet":
            return {r.poem_id for r in records if r.poet_slug == self.poet_slug}
        if self.kind == "union":
            return self.left.resolve(records) | self.right.resolve(records)
        if self.kind == "intersect":
            return self.left.resolve(records) & self.right.resolve(records)
        if self.kind == "difference":
            return self.left.resolve(records) - self.right.resolve(records)
        raise ValueError(f"unknown ScopeSpec kind: {self.kind!r}")


def all_poems() -> ScopeSpec:
    return ScopeSpec(kind="all")


def poet(slug: str) -> ScopeSpec:
    return ScopeSpec(kind="poet", poet_slug=slug)


def union(a: ScopeSpec, b: ScopeSpec) -> ScopeSpec:
    return ScopeSpec(kind="union", left=a, right=b)


def intersect(a: ScopeSpec, b: ScopeSpec) -> ScopeSpec:
    return ScopeSpec(kind="intersect", left=a, right=b)


def difference(a: ScopeSpec, b: ScopeSpec) -> ScopeSpec:
    return ScopeSpec(kind="difference", left=a, right=b)


@dataclass(frozen=True)
class FieldCharter:
    """Spec §48. `derived` and `derivation_rule` exist so a derived
    fraction (spec §11/§23.2) is never silently presented as a native one
    -- the interface must show `derived: true` and the exact rule when
    set (ledger row P1.4)."""

    purpose: str
    corpus_snapshot: str
    scope_spec: ScopeSpec
    derived: bool = False
    derivation_rule: str | None = None
    version: str = "0.1"

    def poem_ids(self, records: list[PoemRecord]) -> set[int]:
        return self.scope_spec.resolve(records)

    def poem_count(self, records: list[PoemRecord]) -> int:
        return len(self.poem_ids(records))
