# Research Release Template

Generate through `ontograph release`; reports and release verification read staged records and source manifests. Do not reconstruct counts during rendering.

Confirm before release:

- ResearchSituation records are present and active or explicitly superseded.
- InquiryCatalog and InquiryReview history is staged, including unsupported/deferred/revised candidates.
- Seed/Object Address/Lexical Anchor records entered through human review or equivalent confirmation.
- Walk or other valid assessment route gives the mode claimed by each operation.
- OperationRecords carry situation_id and inquiry_status.
- Source manifests resolve through `source show` or `source export`.
- Findings cite governed OperationRecords/sources and state pressure, operation, observation, consequence, and limits.
- `data_license_notice` is populated from the corpus/fork licensing chain.
- reopening_conditions and residue are explicit.

Do not export a scholarly release from known-stale, unknown, unsupported-only, or legacy-unframed support without making that limitation prominent.