# Use-Status and Claim Permission (spec §16)

Two separate fields. Never merge them into one "confidence" number.

**Use-Status** — what the record may currently *do*:
descriptive · heuristic · documentary · artistic · technical · scholarly · residual · blocked

**Claim Permission** — how far a proposition may *travel*:
preserve only → describe locally → describe distribution under declared conditions → argue cautiously → argue → block

Rules for the agent:

- Never assign `argue` or `argue cautiously` on your own initiative — that is a
  researcher decision. Propose the level; let the researcher set it.
- An AI-proposed description, anchor, or candidate companion starts at
  `preserve only` until a researcher acts on it (spec Appendix A: "AI
  proposal ≠ evidence").
- A field-wide claim is never permitted from `assessed-rule` or `estimated`
  mode data about a *pair* of objects (spec §27.2's v0.1 restriction:
  pairwise object-level matrices require `assessed-full` or `assessed-rule`
  for *all* participating addresses).
- If a claim's permission level is unclear, default to the more restrictive
  option and say why.
