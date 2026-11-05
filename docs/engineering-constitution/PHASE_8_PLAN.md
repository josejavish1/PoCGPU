# Phase 8 Plan: Production Hardening and Release Evidence

## Status

- Lifecycle state: `DRAFT FOR REVIEW`
- Implementation authority: `BLOCKED` until security, privacy, operations, architecture, product, and engineering reviews accept this plan.
- Primary requirements: `QLT-001` through `QLT-006`, `SEC-001` through `SEC-003`, `I18N-001`, and all Product Release Completion conditions.
- Formula ownership: Phase 8 changes no calculation semantics; formula changes return to their owning phase.

## Objective

Prove that the complete product can be built, deployed, operated, secured, upgraded, recovered, and released reproducibly while preserving deterministic calculations, tenant isolation, evidence integrity, interface parity, and historical replay. Produce auditable release evidence without unsupported readiness scores or self-certification claims.

## Entry conditions

- Phases 0-7 are complete and every regression and parity gate passes.
- Target deployment profiles, service-level policies, data classification, threat model, recovery objectives, and operational ownership are accepted as governed configuration.
- Release environments and credentials are provisioned through approved secret management outside the repository.
- No critical Phase 8 risk lacks preventive, detection, response, and recovery controls.

## Scope

- Threat model, abuse cases, privacy review, tenant-isolation verification, and least-privilege deployment.
- Reproducible build, provenance attestations, dependency lock, SBOM, license inventory, vulnerability reports, artifact signing, and verification.
- Pinned deployable artifacts, environment-specific rendering, secret references, and policy validation.
- Structured logs, metrics, traces, health, SLO monitoring, alert routing, and calculation-safe diagnostics.
- Load, endurance, concurrency, resource-exhaustion, resilience, and dependency-failure tests.
- Backup, restore, point-in-time recovery where applicable, disaster recovery, and integrity verification.
- Schema, database, policy, catalog, formula, and application upgrade/rollback procedures.
- Incident response, evidence preservation, key rotation, access review, and operational runbooks.
- Final cross-organization, vertical, locale, currency, deployment, and failure-mode release matrix.
- Versioned release manifest and completion report.

## Exclusions

- Adding product features, formulas, provider-specific business behavior, or customer-specific forks during hardening.
- Claiming universal production readiness without an explicit deployment profile and evidence.
- Storing secrets in manifests, source, build logs, test fixtures, or release artifacts.
- Treating vulnerability-scan absence of findings as complete security proof.

## Decisions required before implementation

Reviewers must accept:

1. Supported deployment profiles and their availability, scaling, locality, isolation, and dependency assumptions.
2. Data classification, retention, deletion, backup, residency, encryption, and key-management policies.
3. Threat model, trust boundaries, administrator model, integration permissions, and accepted residual risks.
4. Service SLOs, telemetry definitions, alert thresholds, escalation ownership, and incident severity policy.
5. Performance, load, endurance, resource, and recovery budgets.
6. Release signing, provenance, SBOM formats, vulnerability policy, exception expiry, and artifact retention.
7. Upgrade, rollback, compatibility, backup, restore, RPO, and RTO policies.
8. Release approval roles, evidence package, support window, and deprecation policy.

Environment-specific values remain configuration. Missing policy blocks the affected production profile.

## Security contracts

- `DeploymentProfile`: immutable environment capabilities, topology, dependencies, policy references, and support status.
- `SecretReference`: provider-neutral reference metadata; secret values never enter canonical records.
- `AuthorizationPolicyReference`: versioned external policy identity and validity.
- `ReleaseArtifact`: digest, media type, source commit, build identity, SBOM, provenance, signature, and verification status.
- `VulnerabilityAssessment`: scanner and database versions, artifact digest, findings, disposition, owner, and expiry.
- `OperationalEvent`: stable English key, severity, tenant-safe structured fields, correlation identity, and redaction status.
- `BackupRecord`: protected scope, snapshot identity, encryption reference, timestamp, retention, checksum, and restore verification.
- `ReleaseManifest`: exact artifacts, schemas, formulas, policies, catalogs, migrations, test evidence, approvals, and limitations.

## Operational invariants

- Deployed artifact digests match the release manifest and verified signatures.
- Runtime configuration cannot introduce formula or business-policy defaults outside governed records.
- Credentials are externally provisioned and never serialized into scenarios, logs, snapshots, or exports.
- Observability records contain enough identity to diagnose behavior without confidential payload content.
- Backup success is insufficient until restore and replay are verified.
- Upgrade and rollback preserve certified historical result replay or fail with an explicit version-resolution error.
- Dependency failure cannot silently replace evidence, policy, price, benchmark, time, or identity.
- Operational scaling and retries cannot cause duplicate approvals, audit events, or scenario mutations.

## Supply-chain and build gates

- Frozen dependency resolution and clean-room build.
- Source and artifact secret scan.
- Static analysis and dependency vulnerability scan with versioned databases.
- CycloneDX or SPDX SBOM for every released artifact.
- Build provenance tied to source commit and workflow identity.
- Artifact digest signing and verification using approved keyless or managed-key policy.
- License inventory and policy disposition.
- Installed-artifact tests independent of repository source paths.
- Reproduction or documented hermeticity evidence under the accepted build policy.

## Reliability and recovery gates

- Load and endurance under accepted workload profiles.
- Bounded behavior for malformed, oversized, concurrent, and adversarial requests.
- Dependency timeout, partial failure, retry, circuit, and recovery behavior.
- Process, node, zone, database, queue, object-store, identity-provider, and external-provider failure tests as applicable.
- Backup restoration into an isolated environment followed by schema validation, hash verification, and historical replay.
- Upgrade from every supported version and rollback under failure injection.
- Runbook execution by an operator who did not author the procedure.

## Planned implementation boundary

- `deploy/` or an accepted deployment package for rendered, validated, secret-free deployment definitions.
- `src/pocgpu/operations/` only for product-owned health, telemetry, redaction, and release contracts; no formulas.
- `.github/workflows/` for pinned build, test, security, provenance, and release workflows.
- `docs/operations/` for English runbooks, threat model, recovery, upgrade, rollback, and incident procedures.
- `tests/phase8/` for security, load, resilience, recovery, migration, supply-chain, and release verification.
- `release/` for schema-controlled manifests and public evidence, excluding credentials and confidential reports.

Tool and platform selection remains a reviewed decision. All third-party actions and images are pinned by immutable digest or commit.

## Test-first verification matrix

| Area | Required evidence |
|---|---|
| Security | Threat cases, authorization bypass, tenant isolation, secret/privacy scans, SAST, and dependency findings. |
| Supply chain | Lock, clean build, installed artifact, SBOM, provenance, signature, digest, and license checks. |
| Performance | Accepted latency, throughput, concurrency, export, and resource budgets under representative profiles. |
| Resilience | Dependency, process, node, zone, and external-provider failure and recovery where applicable. |
| Recovery | Backup integrity, isolated restore, historical replay, RPO, and RTO evidence. |
| Migration | Supported-version upgrade, failed migration rollback, compatibility, and data integrity. |
| Operations | Health, metrics, traces, redaction, alert routing, runbooks, incident, and key-rotation exercises. |
| Product matrix | Organization, vertical, locale, currency, deployment, scenario state, and interface parity. |

Mandatory tests cannot be skipped, retried into success, or waived without an approved expiring exception recorded in the release manifest.

## Migration and compatibility

- Every persistent schema and result contract has an explicit forward and rollback strategy.
- Formula versions and historical snapshots remain immutable.
- Unsupported old versions fail with documented resolution behavior rather than silent coercion.
- Deployment changes use staged rollout and verified rollback under accepted policy.
- Legacy infrastructure manifests are either migrated to governed deployment packages or removed with evidence.

## Delivery increments

1. Accept deployment profiles, threat model, operational policies, budgets, and release evidence contract.
2. Establish reproducible signed artifacts, SBOM, provenance, vulnerability, and license gates.
3. Implement secret-free deployment rendering, least privilege, and environment validation.
4. Implement safe observability, health, alerts, and operational diagnostics.
5. Execute load, endurance, security, resource-exhaustion, and resilience campaigns.
6. Execute backup, restore, upgrade, rollback, disaster-recovery, and runbook exercises.
7. Complete the product matrix, residual-risk review, release manifest, and Phase 8 completion report.

## Requirements traceability

- `QLT-001` through `QLT-005` govern all hardening and release tests.
- `QLT-006` maps to SBOM and vulnerability evidence.
- `SEC-001` maps to secret, privacy, redaction, and data-boundary controls.
- `SEC-002` maps to tamper-evident provenance and replay verification.
- `SEC-003` maps to least privilege, authorization, and integration threat tests.
- Product Release Completion conditions map to the final release manifest and product matrix.

## Risk controls

- `RSK-014`, `RSK-016`, and `RSK-022`: source-policy, single-engine, immutable-version, and replay gates.
- `RSK-018`: independent evidence and mutation history remain release prerequisites.
- `RSK-023` and `RSK-029`: privacy, redaction, tenant isolation, and least privilege.
- `RSK-030`: frozen lock, clean build, installed artifacts, provenance, and digest verification.
- Phase 8 review must add deployment-specific failure modes before implementation.

## Acceptance criteria

- Every supported artifact has verified digest, SBOM, provenance, signature, vulnerability disposition, and installed-artifact evidence.
- Threat model and security tests cover every accepted trust boundary and tenant path.
- Performance, resilience, recovery, RPO, RTO, upgrade, rollback, and runbook exercises meet accepted policies.
- Observability is actionable, tenant-safe, and free of confidential payloads and credentials.
- The complete product matrix passes across representative organizations, verticals, locales, currencies, deployments, interfaces, and failure states.
- All phase regression, parity, coverage, mutation, governance, and release gates pass without unexplained exceptions.
- The release manifest identifies exact code, artifacts, formulas, policies, catalogs, schemas, evidence, approvals, limitations, and residual risks.
- A Phase 8 completion report demonstrates every Product Release Completion condition.

## Stop conditions

Stop if a secret enters the repository or artifact, tenant isolation fails, an artifact cannot be traced to source, a critical vulnerability lacks accepted disposition, backup cannot be restored, rollback is unproven, historical replay changes, operational telemetry leaks confidential data, a mandatory gate is bypassed, or release evidence cannot support a concrete deployment profile.
