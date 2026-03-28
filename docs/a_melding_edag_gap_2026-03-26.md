# A-melding EDAG/Altinn Gap Analysis

Date: 2026-03-26

## Official anchors used

- Skatteetaten: The a-melding
- Skatteetaten: Deadlines and payment
- Skatteetaten: A-melding submission from payroll system (A02)
- Skatteetaten: The a-melding guide

## What the official guidance currently requires at a high level

- The a-melding is a monthly report about income, employment, withholding tax, employer's national insurance contributions, and financial activity tax.
- The deadline for ordinary submission is the 5th of the following month.
- For system-integrated payroll solutions, the intended submission path is A02 through Altinn-integrated system flow.
- Employers receive feedback after submission, and that feedback is used for payment handling and reconciliation.
- Employment information must be reported each month, including the month in which the employee quits.

## Current nordic_payroll XML coverage

Current implementation in [custom_addons/nordic_payroll/models/a_melding.py](c:/Temp/Git/Odoo/odoo/custom_addons/nordic_payroll/models/a_melding.py) produces:

- Delivery identity
  - `LeveranseId`
  - `Maaned`
  - `Orgnummer`
- Per-employee assignment
  - `Fodselsnummer`
  - `Arbeidsforhold` with employment identifier, start date, optional end date, position percentage, weekly hours, working hours scheme, and job title
- Income semantics
  - `Inntektslinje` for positive income lines using seeded EDAG code mappings
  - `TrekkLinje` for deductions normalized to positive absolute amounts using seeded EDAG code mappings
  - `ArbeidsgiveravgiftLinje` for employer contribution amounts using seeded EDAG code mappings

## Current lifecycle coverage

The module now supports an internal workflow for:

- `draft -> generated`
- `generated -> sent`
- `sent -> accepted`
- `sent -> rejected`

This is useful for administration and audit, and it now includes structured A03 feedback parsing. It is still not connected to Altinn transport or receipt retrieval.
This is useful for administration and audit, and it now includes structured A03 feedback parsing together with configurable Altinn transport submission and receipt polling hooks.

## Gaps between current implementation and official submission expectations

### 1. Employment reporting is now partial, not complete

Official guidance says employment information must be reported each month.

Current gap:

- The XML now contains an employment relationship block with identifier, start/end dates, position percentage, weekly hours, and working hours scheme.
- It still does not prove that the payload matches the full EDAG employment schema expected for all employment scenarios.

### 2. Income code mapping is now traceable, but still incomplete

Official guidance is organized around detailed salary and benefit reporting categories in the a-melding guide.

Current gap:

- The implementation now maps internal payroll codes through seeded EDAG mapping records with official labels and source URLs.
- Coverage now includes the core demo payroll lines plus overtime, holiday pay, bonus, per diem, mileage, and generic expense reimbursement.
- It still needs a broader validated catalog for additional benefits, absence-related reporting, and other real payroll events used outside the current module seed set.

### 3. Withholding tax semantics are incomplete

Official guidance treats withholding tax as part of the monthly reporting and feedback/payment flow.

Current gap:

- `TAX` is now separated into deduction lines, which is better than the previous generic income dump.
- The implementation still does not prove that the tax deduction is represented with the exact EDAG concepts expected by the receiving system.

### 4. Employer contribution and financial activity tax are incomplete

Official guidance explicitly includes employer's national insurance contributions and financial activity tax.

Current gap:

- `AGA` is separated into employer-contribution lines, but the implementation does not yet cover financial activity tax.
- There is no evidence yet that the generated employer-contribution structure matches the official EDAG payload expected for submission.

### 5. Altinn transport is now partial, while receipt semantics still need production validation

Official system-submission guidance points to A02 submission from payroll systems and feedback handling after submission.

Current gap:

- The module now supports configurable OAuth-based submission to an Altinn-style A02 endpoint and configurable receipt polling for structured feedback retrieval.
- `accepted` and `rejected` are derived from parsed A03 feedback instead of manual status buttons.
- The transport layer is still endpoint-config driven and has not yet been validated against a live Altinn integration contract, certificate flow, or production receipt payload variants.

### 6. Correction and replacement flows are now partial

The a-melding guide is explicit that changes and corrections are part of the reporting model.

Current gap:

- The module now records submission type together with correction and replacement references, and includes those identifiers in generated XML.
- It still lacks a richer amendment workflow for selecting prior deliveries automatically, tracking superseded submissions, and reconciling correction chains over time.

### 7. Forward reporting and deadline validation are now partial

Official guidance says reporting is monthly, due on the 5th of the following month, and can be submitted only up to two months ahead in the current year.

Current gap:

- The module now computes the ordinary submission deadline, flags late submissions, requires a late-submission reason, and enforces the two-month forward-reporting window in the current year.
- It still does not account for holiday calendars beyond weekend shifting and may need refinement once exact production business-day rules are validated against the official integration profile.

## Recommended next compliance batch

1. Validate the configurable A02/A03 transport contract against the real Altinn integration profile and production-grade authentication requirements.
2. Validate the new employment block against exact EDAG schema expectations and add missing employment attributes.
3. Broaden the EDAG mapping catalog further for additional benefits, leave scenarios, and sector-specific payroll events.
4. Add first-class amendment workflow support that links corrections and replacements to prior submissions automatically.
5. Refine deadline logic for official non-working-day rules and add stronger reconciliation around receipt/payment outcomes.
