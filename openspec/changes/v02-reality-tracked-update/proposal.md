# Proposal — v0.2 reality-tracked update

## Why

The Rostam user test (`20260901_193123`) produced a useful 17-episode × 15-label draft and a Persian dashboard, but it did not enter Ontograph's governed chain. The labels were agent proposals checked by spot-searching; there was no ResearchSituation, candidate catalog review, stable per-hit assessment, complete occurrence policy, OperationRecord, or Mapping Object. The result is legitimate candidate-tier material, not an apparatus result.

The defect is structural. A new study currently makes object registration and raw analysis easier than recording why the inquiry exists and reviewing what may count as an object. The downstream guards therefore never get a chance to fire. The update makes the governed route the shortest route from hunch to source-backed report while retaining the core non-equivalences: proposal is not evidence, Anchor Hit is not occurrence, and co-incidence is not relation.

This proposal does not assume future trust-repair work is already present. Stable Anchor Hit identity, per-hit assessments, complete assessed modes, OperationRecords, and self-contained releases arrive in T04–T12 and are dependencies of the W rows that use them.

## What changes

- Add `ontograph inquire <study> ...` as lossless intake. It persists the verbatim hunch and authored situation fields. The deterministic engine does not pretend to translate an English hunch into Persian motifs or infer battle strategies.
- Accept an attributed proposal file containing candidate Seeds, Object Addresses, lexical forms, contrast candidates, and non-object notes. Agent-authored material remains proposal-tier.
- Verify lexical forms against the pinned corpus and current Field scope. Supported forms receive stable hit counts and located examples; zero-support forms remain explicitly unsupported. Only verified seed anchors drive deterministic lexical-neighbor proposals from the cached index.
- Keep inquiry candidates in stores that census/object loaders cannot read. A separate, append-only human review is required before accepted candidates are materialized as provisional Object Addresses and approved retrieval anchors. Review approval is not an OccurrenceAssessment.
- Make a ResearchSituation a precondition for new governed-workspace Field construction, object promotion, walk, and analytical commands. Legacy unframed work remains readable, but is visibly limited and cannot support a Finding, Claim, Relation-Object, or scholarly release until rerun under a situation.
- Upgrade `walk` with an evidence tray of lexical cues and reviewed candidate objects. Cues are never called labels and never change the current hit's decision. The existing `a/r/u` decision remains strictly about whether that Anchor Hit may count for the selected Object Address.
- Add two distinct catalog artifacts:
  - an **InquiryCatalog**, containing proposal/review state and corpus support; and
  - a **DescriptiveCatalog**, an assessed-full object × object co-incidence arrangement produced only after scale-aware Mapping Object and Relation-Object guards exist.
- Append an amendment to the Hermes execution spec. T01–T13 remain first. Inquiry work is interleaved with the relevant U rows; V201 → V202 → V207 precedes the new descriptive catalog and later analytic surfaces.

## Path of least resistance

For a fresh study, `study status` offers exactly one first research action: `inquire`. `inquire` emits a review template and exact next commands; a sole active situation is inherited automatically. Multiple active situations require `--situation`, so the engine never guesses. The conversational skill does the file preparation and command execution, while the researcher only supplies the hunch and accepts, rejects, defers, splits, or revises candidates.

The official route is therefore:

```text
study new → inquire → field build/refresh evidence → review candidates
→ walk → assessed-full operations → catalog → source return → Finding → release
```

Raw `anchor` exploration remains available after intake, but is labeled lexical and cannot silently become object evidence. Outputs made outside the apparatus have no eligible OperationRecord/source manifest and therefore cannot enter higher-order records or a verified release.

## Capabilities

### New

- `inquiry-intake`: hunch → ResearchSituation → attributed InquiryCatalog → corpus verification → explicit review/promotion.
- `descriptive-catalog`: complete assessed co-incidence → deterministic, source-returnable catalog with denominators, ambiguity, typed refusals, and no relation promotion.

### Modified

- `guided-walk`: situation/catalog context and per-hit lexical evidence cues without answer-suggesting labels or automatic decisions.
- `operation-ledger`: governed operations carry situation provenance; unframed legacy operations remain visibly ineligible as higher-order evidence.

## Impact

- Planned implementation touches `inquiry.py`, `catalog.py`, `walk.py`, `records.py`, `cli.py`, status, release collection, reports, tests, and the researcher skill under their future ledger rows.
- Inquiry and review records are additive and append-only. Candidate stores are not source truth and never mutate the corpus.
- No new dependency, network request, or runtime LLM is introduced. The agent may author a proposal file, but the file records that authorship and the engine only validates/computes from declared corpus data.
- The Rostam workspace becomes the Gate G/H acceptance case: the ready-made flow must turn the hunch into a reviewed catalog, a researcher-driven walk, source returns, and a rendered release without asking the researcher to operate internal machinery.
