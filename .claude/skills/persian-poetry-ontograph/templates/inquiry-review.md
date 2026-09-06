# Inquiry Review Template

The researcher supplies these decisions. The agent writes the file and runs `ontograph inquire --review`.

```json
[
  {
    "candidate_id": "<candidate-id-from-refreshed-catalog>",
    "decision": "accept",
    "rationale": "human reason for promoting this provisional route"
  },
  {
    "candidate_id": "<candidate-id>",
    "decision": "reject",
    "rationale": "human reason for not tracking it now"
  }
]
```

Allowed decisions: accept, accept-unsupported, reject, defer, revise, split. Review does not assess hits and does not prove an occurrence.