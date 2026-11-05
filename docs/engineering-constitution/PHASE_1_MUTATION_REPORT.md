# Phase 1 Mutation Report

## Scope

Mutation testing covered every covered line under `src/pocgpu/domain` with mutmut 3.8.1. The selected tests were the Phase 1 domain and property suites. The clean-test and forced-failure controls passed before mutation execution.

## Result

- Generated mutants: 870.
- Killed mutants: 849.
- Surviving mutants before adjudication: 21.
- Behavior-changing survivors: 0.
- Equivalent or semantically inert survivors: 21.
- Adjusted mutation score: 100 percent.

The test improvements made during review reduced unreviewed survivors from 277 to 21. They added exact error-code and path contracts, all collection-path cases, non-finite numeric boundaries, every rounding mode, affine unit offsets, host-timezone independence, canonical byte and hash fixtures, mixed-type set ordering, Unicode ordering, and exact serialization errors.

## Formal adjudication

### Decimal textual equivalence

The following mutants are equivalent for finite `Decimal` values:

- `numeric.x_canonical_decimal__mutmut_15`: the `f` and `F` Decimal format specifiers produce identical fixed-point text.
- `numeric.x_canonical_decimal__mutmut_23`: mutmut changes the `rstrip` character set from `0` to `X0`, which still removes exactly the reachable trailing character `0`; canonical decimal text cannot end in `X`.
- `numeric.x_canonical_decimal__mutmut_24`: mutmut changes the second `rstrip` character set from `.` to `X.`, which still removes exactly the reachable trailing character `.`; canonical decimal text cannot end in `X`.
- `numeric.xRoundingPolicyxapply__mutmut_11`: `Decimal(1).scaleb(-scale)` and `Decimal(2).scaleb(-scale)` have the same exponent. `Decimal.quantize` uses the operand exponent, not its coefficient, so both define the same rounding quantum.

### Timestamp grammar equivalence

The canonical timestamp input is generated with `timespec="microseconds"`, so it contains exactly one decimal point and exactly six fractional digits:

- `serialization.x__canonical_timestamp__mutmut_16`: omitting `maxsplit=1` is equivalent with one delimiter.
- `serialization.x__canonical_timestamp__mutmut_17`: `split` and `rsplit` are equivalent with one delimiter.
- `serialization.x__canonical_timestamp__mutmut_19`: `maxsplit=2` is equivalent with one delimiter.
- `serialization.x__canonical_timestamp__mutmut_27`: the mutated `rstrip` set contains `0` plus an unreachable `X`, so observable output is unchanged.

### Set ordering key equivalence

The following mutations affect only JSON text used as an internal sort key. They do not alter the serialized payload. Exhaustive representative comparison across canonical scalar values and heterogeneous object shapes confirmed that whitespace and replacement delimiter tokens preserve the lexicographic ordering relation. Sorted-key removal is covered separately and is killed by object-order tests.

- `serialization.x__canonicalize__mutmut_58`
- `serialization.x__canonicalize__mutmut_59`
- `serialization.x__canonicalize__mutmut_60`
- `serialization.x__canonicalize__mutmut_63`
- `serialization.x__canonicalize__mutmut_64`
- `serialization.x__canonicalize__mutmut_66`
- `serialization.x__canonicalize__mutmut_67`
- `serialization.x__canonicalize__mutmut_68`

`ensure_ascii=None` is false by Python truth-value semantics and is equivalent to `ensure_ascii=False`. `sort_keys=None` is likewise equivalent to false for canonical scalar set members. The remaining survivors change only whitespace or substitute constant delimiter sequences in a comparison key without changing ordering.

### Unreachable serializer options and encoding alias

- `serialization.x_canonical_json_bytes__mutmut_11`: `ensure_ascii=None` is equivalent to false.
- `serialization.x_canonical_json_bytes__mutmut_12`
- `serialization.x_canonical_json_bytes__mutmut_17`
- `serialization.x_canonical_json_bytes__mutmut_21`

The three `allow_nan` variants are unreachable: floats are prohibited before `json.dumps`, integers and booleans cannot be non-finite, and `Decimal` values pass through `require_decimal`, which rejects non-finite values. Property and negative tests cover all of those boundaries.

- `serialization.x_canonical_json_bytes__mutmut_26`: Python treats `utf-8` and `UTF-8` as aliases for the same codec and produces identical bytes.

## Decision

Every behavior-changing mutant is killed. The 21 survivors are formally accepted as equivalent or semantically inert for the declared canonical input domain. No mutation suppressions, coverage exclusions, weakened assertions, or reduced mutation scope were used to obtain this result.
