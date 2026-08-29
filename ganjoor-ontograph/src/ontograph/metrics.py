"""Unit incidence, prevalence, spread, concentration, dispersion.

Spec §27.3 (unit incidence I(u,o)), §27.4 (prevalence, denominator always
displayed), §27.5 (spread), §27.6 (concentration/top-source share), §27.7
(dispersion -- a named, versioned Gries DP-family measure, never rendered
without raw counts and partition sizes alongside, spec §27.7 and Appendix
A: "high frequency != wide dispersion").

Implemented in ledger rows P3.1 (incidence/prevalence/spread/concentration)
and P3.2 (dispersion).
"""
