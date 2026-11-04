# Calculation Constitution

## Calculation record requirements

Every governed calculation must define:

- Stable formula identifier and semantic version.
- Name and purpose.
- Mathematical expression.
- Input identifiers and dimensions.
- Output identifier and dimension.
- Preconditions and valid domain.
- Rounding and precision policy.
- Evidence requirements.
- Assumptions and limitations.
- Failure behavior.
- Golden examples.
- Owning phase and approval state.

## Numeric rules

- Monetary calculations use decimal arithmetic and an explicit currency.
- Physical quantities use typed dimensions and explicit conversion functions.
- Percentages are stored as normalized ratios unless a schema explicitly names percentage points.
- Time windows are explicit; monthly, annual, hourly, and instantaneous rates are never interchangeable.
- Binary and decimal storage units are distinct.
- Rounding occurs only at declared boundaries, never during intermediate calculations unless the formula requires it.
- Aggregation across currencies requires an identified FX observation and timestamp.
- Missing values never become zero unless zero is a verified value.

## Initial formula registry

The formulas below define semantic intent. Exact implementation awaits its owning phase plan and golden cases.

| Formula ID | Version | Owning phase | Approval state |
|---|---:|---:|---|
| CAP-001 | 0.1.0 | 2 | DEFINED |
| CAP-002 | 0.1.0 | 2 | DEFINED |
| CAP-003 | 0.1.0 | 2 | DEFINED |
| CAP-004 | 0.1.0 | 2 | DEFINED |
| CAP-005 | 0.1.0 | 2 | DEFINED |
| TCO-001 | 0.1.0 | 3 | DEFINED |
| TCO-002 | 0.1.0 | 3 | DEFINED |
| TCO-003 | 0.1.0 | 3 | DEFINED |
| ECO-001 | 0.1.0 | 4 | DEFINED |
| ECO-002 | 0.1.0 | 4 | DEFINED |
| PRC-001 | 0.1.0 | 4 | DEFINED |
| PRC-002 | 0.1.0 | 4 | DEFINED |
| API-001 | 0.1.0 | 5 | DEFINED |
| API-002 | 0.1.0 | 5 | DEFINED |
| HYB-001 | 0.1.0 | 5 | DEFINED |

### Capacity

#### CAP-001: Compatible benchmark predicate

An approved benchmark is compatible only when all identity-defining Serving Unit fields and required workload dimensions match within an explicitly allowed compatibility rule.

Failure behavior: `BENCHMARK_REQUIRED`.

#### CAP-002: Useful capacity predicate

`useful = ttft_pass AND tpot_pass AND error_rate_pass AND queue_pass AND stability_pass`

Useful capacity is the greatest measured load point satisfying every required predicate. A theoretical maximum is not eligible.

#### CAP-003: Constraint-specific Serving Units

For each capacity dimension `d`:

`serving_units_d = ceil(peak_demand_d / useful_capacity_per_serving_unit_d)`

Dimensions include input token rate, output token rate, request rate, and concurrency.

#### CAP-004: Productive Serving Units

`productive_serving_units = max(serving_units_input, serving_units_output, serving_units_requests, serving_units_concurrency)`

Headroom and resilience are applied after this bottleneck calculation and remain separately visible.

#### CAP-005: Utilization by constraint

`utilization_d = demand_d / sellable_capacity_d`

`bottleneck_utilization = max(utilization_d)`

Precondition: demand and capacity use the same dimension and time window.

### TCO

#### TCO-001: Monthly depreciable cost

`monthly_depreciation = (capitalized_cost - residual_value) / useful_life_months`

Capitalized cost, useful life, and residual value are asset-class specific.

#### TCO-002: Monthly facility energy

`monthly_facility_kwh = sum(measured_average_it_kw_i * quantity_i * active_hours_i) * pue`

`monthly_energy_cost = monthly_facility_kwh * electricity_price_per_kwh`

PUE includes facility energy overhead. Additional cooling energy is prohibited unless the cost boundary proves it is excluded from PUE.

#### TCO-003: Fully loaded monthly TCO

`monthly_tco = depreciation + capital_charge + fixed_opex + variable_opex + allocated_one_off + risk_view_adjustments`

Risk-adjusted and nominal TCO remain distinct outputs.

### Unit economics and pricing

#### ECO-001: Blended cost per million tokens

`blended_cost_per_million = allocated_monthly_tco / ((monthly_input_tokens + monthly_output_tokens) / 1_000_000)`

Precondition: the TCO boundary and token demand cover the same service and period.

#### ECO-002: Utilization sensitivity

`tokens_at_utilization = useful_monthly_token_capacity * utilization_ratio`

`cost_per_million_at_utilization = monthly_tco / (tokens_at_utilization / 1_000_000)`

#### PRC-001: Gross-margin price

`price = cost / (1 - target_gross_margin)`

Valid domain: `0 <= target_gross_margin < 1`.

#### PRC-002: Markup reporting

`markup = (price - cost) / cost`

Markup is informational and must never be labeled gross margin.

### External comparison

#### API-001: Equivalent API cost

`api_cost = input_millions * input_price + output_millions * output_price + cached_input_millions * cached_input_price + other_metered_costs`

The workload, period, currency, region, discounts, batch mode, and cache treatment must match the scenario.

#### API-002: Piecewise break-even

Within one private capacity step:

`break_even_volume = fixed_private_cost / (api_unit_cost - private_variable_unit_cost)`

The solution is valid only inside that step's capacity interval. Every discrete infrastructure step must be evaluated.

#### HYB-001: Hybrid monthly cost

`hybrid_cost = full_installed_private_block_cost + external_overflow_cost`

Private fixed cost is not multiplied by its traffic share.

## Formula change control

A formula change requires:

1. A new formula version.
2. Updated dimensional analysis.
3. Updated golden and property tests.
4. Impact analysis for stored scenarios.
5. Migration or explicit preservation of prior result versions.
6. Technical and financial review for financially material formulas.
