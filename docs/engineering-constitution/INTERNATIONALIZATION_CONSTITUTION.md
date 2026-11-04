# Internationalization Constitution

## Language boundary

Executable source, identifiers, comments, docstrings, technical logs, schemas, test names, migration scripts, and canonical technical documentation use English only.

User-facing language is stored in versioned locale resources. Locale resources and localized deliverables may contain any supported language.

## Source rules

- User-facing messages are referenced by stable semantic keys.
- Source code must not contain fallback display sentences.
- Technical exception objects expose stable error codes, structured parameters, and localization keys.
- Log events use stable English event names and structured fields.
- Translations never change calculation behavior.
- Domain identifiers remain stable when display labels change.

## Standards

- BCP 47 language tags.
- Unicode text processing.
- CLDR-compatible number, date, time, plural, and unit formatting.
- ISO 4217 currency codes.
- IANA time zone identifiers.
- ISO 8601 machine timestamps.
- Explicit support for left-to-right and right-to-left layouts.

## Locale pack contract

Each locale pack contains:

- Locale identifier.
- Parent fallback locale.
- Version.
- Translation key map.
- Plural and grammatical variants where required.
- Placeholder names and types.
- Directionality.
- Review status and reviewer role.

All supported locale packs must preserve key and placeholder parity with the source locale. Missing mandatory keys block release for that locale.

## Formatting rules

- Canonical serialized values remain locale neutral.
- Display formatting occurs only at interface boundaries.
- Input parsing must never infer ambiguous decimal or grouping separators without a declared locale.
- Currency conversion and currency formatting are separate operations.
- Time zone conversion and date formatting are separate operations.
- Exported machine-readable data uses canonical units and formats.

## Testing

- English-only source scan.
- User-facing literal scan.
- Locale key parity and placeholder type tests.
- Pseudolocalization.
- Long-text layout tests.
- Right-to-left layout tests.
- Unicode normalization and non-Latin input tests.
- Currency, number, date, time zone, and pluralization matrix.
- Accessibility checks for localized interfaces.
