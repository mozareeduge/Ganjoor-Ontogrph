# Operation packs → CLI verbs (spec Part V, §71)

Each row: operation, CLI verb, required inputs, result-card sentence template.
Do not report a number without also stating its denominator and mode
(anchor / assessed-full / assessed-rule / estimated — spec §8.1).

| Operation | CLI verb | Requires | Sentence template |
|---|---|---|---|
| Anchor-hit census | `ontograph census` | approved anchors, field | "`{anchor}` occurs in {n} eligible units under {mode} mode." |
| Prevalence / spread / concentration | `ontograph map recurrence` | Object Address, unit | "{object} occurs in {n} of {denom} eligible {unit}s ({pct}%). Top {k} sources supply {share}%." |
| Typed co-incidence | `ontograph companions` | two+ Object Addresses, scale | "{A} and {B} co-occur in {n} eligible {scale}s." |
| Conditional association | `ontograph companions --assoc` | as above | "P({B}\|{A}) = {x}; P({A}\|{B}) = {y}." Never call this direction or causation. |
| Relation scale profile | `ontograph companions --scale-ladder` | relation, scale list | Show raw counts at every scale; no verdict on which scale is "real." |
| Compare fields | `ontograph compare` | two Field Charters | Raw incidence + prevalence in both; no bare log-ratio without raw support shown alongside. |
| Ablation | `ontograph ablate` | component to remove, metric | "Removing {X} takes {M} from {before} to {after} ({retention}% retention)." Never state *why* without a Finding. |
| Release | `ontograph release` | study id, version | Produces a `ResearchRelease`; confirm `data_license_notice` is populated before treating it as exportable. |

Every card ends with: source-return button, action choices, "How was this
made?" disclosure (spec §43). No exceptions for a "quick" answer.
