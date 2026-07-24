# 02. Confirmation/Intent Parser

**Responsibility:** Parse a spoken response to a confirmation prompt into a strict, deterministic decision.

Full contract: see [`Component_IO_Spec.md`](../../docs/Component_IO_Spec.md), section 2.

## Input

```json
{"transcript": "yes go ahead"}
```

## Output

```json
{"confirmed": true, "match_rule": "affirmative_phrase"}
```

A confident no:

```json
{"confirmed": false, "match_rule": "negative_phrase"}
```

Anything that isn't a confident yes or no — including mixed signals like
"yes no wait cancel that" — is never guessed at:

```json
{"confirmed": false, "match_rule": "no_match", "needs_reprompt": true}
```

## Implementation notes

Pure regex matching against affirmative/negative phrase lists — no model
call anywhere. One deliberate wrinkle: a small set of "hedge" phrases
(`"not sure"`, `"not certain"`, `"i don't know"`, ...) suppress an
affirmative match rather than counting as a negative one, because naive
word matching would otherwise read "sure" inside "not sure" as a yes. Mixed
signals (both affirmative and negative phrases present) fall through to
`no_match`/`needs_reprompt` rather than picking one — the whole point of
this component is to never guess on something that gates a real write or
delete.

## Standalone test

Run this component's tests in isolation, without anything else in the repo running:

```bash
pytest components/c02_confirmation_parser
```

Table-driven per the spec: ~20 transcript → decision cases covering clear
affirmatives, clear negatives, the "not sure" hedge case, empty/unrelated
input, and mixed signals — plus two exact-shape checks against the spec's
own JSON examples.

Shared cross-component JSON shapes live in [`schemas/examples/`](../../schemas/examples/).

## Dependencies

_None — pure Python._

Own requirements file: [`requirements.txt`](requirements.txt) (don't add
deps here to other components' files, and don't expect other components'
deps in yours).
