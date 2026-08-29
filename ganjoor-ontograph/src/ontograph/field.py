"""FieldCharter / ScopeSpec construction.

Spec §7 (Construct the Object-Field), §23 (Supported corpus fractions),
§48 (FieldCharter/ScopeSpec schemas). Native filters (poet/category/poem/
format/metre/rhyme/source) combine through intersection, union, and
difference; derived fractions (e.g. poet-life chronological proxies, spec
§11/§23.2) are always labelled "derived" with the exact rule stored.

Implemented in ledger row P1.3 (native filters) and P1.4 (derived fractions).
"""
