# Day25 v3 Integrity Patch Note

## Why the patch was required

Day25 v2 reported:

`fully_independent_external_claim_present = True`

This was a false positive.

The manuscript uses the phrase only in safe limitation / prohibition contexts,
including wording such as:

- `overlap-excluded cross-dataset validation`
- `not fully independent external validation`
- `rather than fully independent external validation`
- instructions to avoid fully independent external-validation wording

The v2 checker detected phrase occurrence rather than scientific assertion.

## v3 correction

The audit now detects only explicit positive claims such as:

- `we demonstrated fully independent external validation`
- `this study provides fully independent external validation`
- `constitutes fully independent external validation`

It separately verifies that the required phrase:

`overlap-excluded cross-dataset validation`

is present.

## Scientific impact

None.

No:
- model result,
- table,
- figure,
- metric,
- citation,
- manuscript evidence,
- conclusion

was changed.

Only the integrity-audit logic was corrected.
