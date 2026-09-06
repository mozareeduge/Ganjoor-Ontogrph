# Walk Script Template

The researcher supplies occurrence decisions; the agent records them in stable scripted form and runs `ontograph walk`.

```json
{
  "responses": [
    "a",
    "r",
    "u",
    "c:<candidate-id>",
    "done"
  ]
}
```

Use `a` accepted, `r` rejected, `u` ambiguous. `c:<candidate-id>` records only a candidate encounter proposal for the current stable Anchor Hit. `done` stops; it does not manufacture completeness.