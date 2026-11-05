# Engineering Constitution

This directory is the normative design authority for the Universal AI Infrastructure Economics Platform.

The constitution exists to ensure that implementation begins only after product semantics, calculation rules, data contracts, architecture boundaries, quality gates, and failure handling have been defined. Runtime code, interfaces, exports, and localized deliverables must conform to these documents.

## Authority order

When two artifacts conflict, the following order applies:

1. Product Constitution
2. Calculation Constitution
3. Data Governance Policy
4. Architecture and accepted Architecture Decision Records
5. Quality Strategy and Definition of Done
6. Phase plans
7. Implementation documentation

An unresolved conflict blocks implementation or release. It must never be resolved by a silent default.

## Documents

- [Governance Manifest](constitution.manifest.json)
- [Phase 0 Plan](PHASE_0_PLAN.md)
- [Phase 0 Completion Report](PHASE_0_COMPLETION_REPORT.md)
- [Phase 1 Plan](PHASE_1_PLAN.md)
- [Phase 1 Completion Report](PHASE_1_COMPLETION_REPORT.md)
- [Phase 1 Mutation Report](PHASE_1_MUTATION_REPORT.md)
- [Delivery Roadmap: Phases 0-8](DELIVERY_ROADMAP.md)
- [Phase 2 Plan](PHASE_2_PLAN.md)
- [Phase 3 Plan](PHASE_3_PLAN.md)
- [Phase 4 Plan](PHASE_4_PLAN.md)
- [Phase 5 Plan](PHASE_5_PLAN.md)
- [Phase 6 Plan](PHASE_6_PLAN.md)
- [Phase 7 Plan](PHASE_7_PLAN.md)
- [Phase 8 Plan](PHASE_8_PLAN.md)
- [Product Constitution](PRODUCT_CONSTITUTION.md)
- [Domain Glossary](DOMAIN_GLOSSARY.md)
- [Requirements Traceability](REQUIREMENTS_TRACEABILITY.md)
- [Calculation Constitution](CALCULATION_CONSTITUTION.md)
- [Data Governance](DATA_GOVERNANCE.md)
- [No Hardcoding Policy](NO_HARDCODING_POLICY.md)
- [Internationalization Constitution](INTERNATIONALIZATION_CONSTITUTION.md)
- [Target Architecture](ARCHITECTURE.md)
- [Quality Strategy](QUALITY_STRATEGY.md)
- [Risk Register and FMEA](RISK_REGISTER.md)
- [Migration Baseline](MIGRATION_BASELINE.md)
- [Definition of Done](DEFINITION_OF_DONE.md)
- [Architecture Decision Records](adr/README.md)

## Mandatory lifecycle

Every delivery phase must follow this sequence:

1. Publish a phase plan.
2. Resolve mathematical, data, and interface contracts.
3. Identify failure modes and migration impact.
4. Define tests and acceptance evidence.
5. Implement the approved scope.
6. Run all phase and regression gates.
7. Publish a phase completion report.

No phase may claim completion while a required gate is failing, skipped, disabled, or supported only by unverified assumptions.

## Automated enforcement

The versioned governance manifest declares the complete document inventory, stable identifier registries, table contracts, phase ownership, link policy, canonical text policy, localized resources, and temporary legacy ratchet.

Run the standard-library validator from the repository root:

```bash
python3 scripts/validate_engineering_constitution.py
```

Run its isolated control tests:

```bash
python3 -m unittest discover -s tests/governance -p 'test_*.py'
```

The CI governance workflow executes both commands and the existing lexical source gate. A frozen legacy file may remain only while its content hash matches the Phase 0 baseline. The ratchet expires when the governance phase advances to Phase 1; remediation is required and rebaselining is prohibited.
