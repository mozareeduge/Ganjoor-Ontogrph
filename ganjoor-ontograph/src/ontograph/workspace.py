"""Study workspace management.

Spec §60: each study receives an isolated workspace under
`ontograph-workspaces/<study-id>/` (charter/, objects/, corpus/, research/,
mappings/, events/, releases/). Per the v2.3.0 addition to §60, each
workspace SHOULD itself be a git repository, with each release a tagged
commit -- reusing the same commit-pin discipline the corpus layer already
imposes on itself (spec §56), applied reflexively to the research layer.

Implemented in ledger row P1.7.
"""
