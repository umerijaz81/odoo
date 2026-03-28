# Nordic Payroll Review Report

Date: 2026-03-26

## Scope

- Reviewed `custom_addons/nordic_payroll` in the workspace.
- Exercised the local Odoo instance on `http://localhost:8069` against database `my_dev_db` using `admin/admin`.
- Browser coverage was limited to opening the live UI and exercising the same web endpoints and JSON-RPC routes the web client uses. Full click automation was not available in this chat session because browser chat tools were not enabled.

## Executive Summary

The `nordic_payroll` module is now in a materially better state than it was at the time of the initial review. The previously blocking upgrade issues have been fixed, the module upgrades successfully on `my_dev_db`, automated regression tests pass, duplicated payroll seed data has been normalized, row-level payroll security rules are in place, employer contribution rates are configurable, and the most immediate configuration and environment warnings observed during startup have been removed.

The detailed findings in this report remain useful as a record of the original risks that were identified during review, but they no longer represent the current top-line status. The main remaining concerns are narrower in scope: the A-melding implementation is tighter semantically than before but still not compliance-ready, and an unrelated `hr_homeworking` employee form issue remains in the wider environment outside the Nordic Payroll module itself.

The latest remediation passes also introduced controlled payslip and A-melding workflows, so status transitions now flow through explicit server-side actions instead of raw state writes.

## Status Findings

### 1. Resolved: upgrade blocker on employee form fields

Current status: Resolved

Initial severity: Critical

Evidence:

- `odoo-bin -c odoo.conf -d my_dev_db -u nordic_payroll --stop-after-init --limit-time-real=600` fails during view validation.
- The failing view is the employee form extension in `custom_addons/nordic_payroll/views/views.xml`.
- The first invalid field reported by Odoo is `wage_type`.

Relevant code:

- `custom_addons/nordic_payroll/views/views.xml:259`
- `custom_addons/nordic_payroll/views/views.xml:261`
- `custom_addons/nordic_payroll/views/views.xml:262`
- `custom_addons/nordic_payroll/models/hr_employee.py`

Why it matters:

- The checked-in module cannot be reliably installed or upgraded in a clean database.
- Any browser or functional testing against the live database is therefore testing a previously installed state, not the exact source currently in the repo.

Observed upgrade error:

```text
Field "wage_type" does not exist in model "hr.employee"
View error context:
xmlid: view_employee_form_nordic_payroll
file: custom_addons/nordic_payroll/views/views.xml
```

### 2. Resolved: payroll access control now includes ACL narrowing and row-level rules

Current status: Resolved

Initial severity: High

Original evidence:

- All Nordic payroll models are writable by `base.group_user` in `custom_addons/nordic_payroll/security/ir.model.access.csv`.
- There are no record rules in the module security directory.

Relevant code:

- `custom_addons/nordic_payroll/security/ir.model.access.csv:2`
- `custom_addons/nordic_payroll/security/ir.model.access.csv:3`
- `custom_addons/nordic_payroll/security/ir.model.access.csv:4`
- `custom_addons/nordic_payroll/security/ir.model.access.csv:5`
- `custom_addons/nordic_payroll/security/ir.model.access.csv:6`

Why it mattered:

- Any internal user can create, edit, and delete salary rules, structures, payslips, payslip lines, and A-melding records.
- Payroll data is normally HR-sensitive and should not be globally writable to all internal users.

### 3. Resolved: salary-rule editing now has validation, manager-only governance, and audit tracking

Current status: Resolved

Initial severity: High

Original evidence:

- `compute_sheet` evaluates `amount_python_compute` with `safe_eval`.
- Salary rules are editable by `base.group_user` per the ACLs above.

Relevant code:

- `custom_addons/nordic_payroll/models/payslip.py:84`
- `custom_addons/nordic_payroll/models/payslip.py:144`
- `custom_addons/nordic_payroll/views/views.xml:107`
- `custom_addons/nordic_payroll/security/ir.model.access.csv:2`

Why it matters now:

- `safe_eval` is still part of the payroll engine, but Python formulas are now validated before save, salary-rule administration is manager-only, and sensitive edits generate audit chatter on the rule record.
- The remaining concern is no longer unrestricted editing, but whether the implemented rule set is substantively correct for statutory payroll use.

### 4. Resolved: payroll structures require explicit production approval

Current status: Resolved

Initial severity: Medium

Evidence:

- Payroll structures now carry explicit approval state and approval metadata.
- Unapproved structures are rejected when a payslip is moved out of draft or computed in production mode.
- Approval and revocation actions generate audit chatter on the structure record.

Relevant code:

- `custom_addons/nordic_payroll/models/payslip.py`
- `custom_addons/nordic_payroll/views/views.xml`
- `custom_addons/nordic_payroll/tests/test_nordic_payroll.py`

### 5. Resolved: duplicate payroll seed data and runtime drift

Current status: Resolved

Initial severity: High

Original evidence:

- The repo defines overlapping payroll rules and duplicates `structure_nordic_base` in both payroll data files.
- The installed database does not match the repo data. Runtime inspection showed structure `1` containing rules `[1, 2, 3, 14]` and a rule `AGA_Z1` with category `ALW`, not the `COMP` category defined in the current repo XML.
- In runtime testing, a test payslip with `BASIC=50000`, `PENSION=-1000`, `TAX=-12250`, and `AGA_Z1=7049.999999999999` produced `gross_amount=57050` instead of `50000`, because the installed AGA rule was counted as an allowance.

Relevant code:

- `custom_addons/nordic_payroll/data/hr_payroll_data.xml:45`
- `custom_addons/nordic_payroll/data/hr_payroll_rules.xml:46`
- `custom_addons/nordic_payroll/models/payslip.py:44`
- `custom_addons/nordic_payroll/models/payslip.py:45`

Why it mattered:

- Payroll totals in the live system can drift from source-controlled business rules.
- The duplicate XML definitions make upgrades and data maintenance harder to reason about.

### 6. Partially Resolved: A-melding generation has explicit semantic mapping, but is not compliance-ready

Current status: Partially resolved

Initial severity: Medium

Evidence:

- `action_generate_xml` writes a minimal XML envelope with one `<Oppgave>` per payslip and one `<Inntektslinje>` per payslip line.
- Runtime output included negative `PENSION` and `TAX` entries and an employer contribution line as a generic income line.

Relevant code:

- `custom_addons/nordic_payroll/models/a_melding.py:34`
- `custom_addons/nordic_payroll/models/a_melding.py:48`
- `custom_addons/nordic_payroll/models/a_melding.py:53`
- `custom_addons/nordic_payroll/models/a_melding.py:56`

Runtime XML sample:

```xml
<?xml version='1.0' encoding='UTF-8'?>
<EDAG-M xmlns='http://www.skatteetaten.no/xsd/edag/v2'>
<Leveranse><Maaned>2026-03</Maaned>
<Oppgave><Fodselsnummer>12345678901</Fodselsnummer>
<Inntektslinje><Type>BASIC</Type><Belop>50000.0</Belop></Inntektslinje>
<Inntektslinje><Type>PENSION</Type><Belop>-1000.0</Belop></Inntektslinje>
<Inntektslinje><Type>TAX</Type><Belop>-12250.0</Belop></Inntektslinje>
<Inntektslinje><Type>AGA_Z1</Type><Belop>7049.999999999999</Belop></Inntektslinje>
</Oppgave>
</Leveranse></EDAG-M>
```

Why it matters:

- The module now distinguishes income lines, deduction lines, and employer-contribution lines in generated XML and rejects invalid sign/category combinations.
- The module now also has an explicit internal lifecycle for generated, sent, accepted, and rejected reporting states, with chatter-based audit logging.
- This is materially safer than the earlier generic dumping approach, but still falls short of a compliance-validated submission implementation.

### 7. Resolved: manifest and startup hygiene warnings addressed

Current status: Resolved

Initial severity: Low

Original evidence:

- The manifest had no `license` key, which caused Odoo to warn at startup and upgrade.
- The dependency list includes broad modules such as `auth_oauth` and `website_sale`, while the core payroll flow exercised in this review does not depend on them directly.

Relevant code:

- `custom_addons/nordic_payroll/__manifest__.py:22`

Why it mattered:

- Missing metadata caused noisy warnings.
- Broad dependencies increase the chance that unrelated modules affect payroll installability and runtime behavior.

## Validation Results

### Validation context

- The UI page at `http://localhost:8069/web/login` opened successfully.
- A limited browser verification pass was completed for the salary-rule governance form using the live local Odoo web client route. Full click automation was not available because browser chat tools were disabled for this session.
- A second limited browser verification pass was completed for the payroll-structure approval form using the same live web client approach.
- The running database contains drift and customizations not represented in the workspace. That affected some tests.

### Remediation batches completed after the initial review

1. Security hardening
   - HR-scoped ACLs and company-level row rules are implemented for payslips, payslip lines, and A-melding records.

2. Employer contribution configurability
   - AGA rates are configurable by tax zone and company override, and payroll formulas now consume the configured rate.

3. Salary-rule and structure governance
   - Python salary rules are validated before save, salary-rule changes are manager-governed and audited, payroll structures require explicit production approval, and approval changes are recorded in chatter.

4. Controlled payslip workflow and tighter A-melding semantics
   - Payslip state changes now flow through explicit workflow actions instead of raw state writes, and A-melding output now distinguishes income, deductions, and employer contributions while rejecting duplicate-per-employee monthly submissions and invalid line semantics.

5. Controlled A-melding lifecycle and EDAG gap mapping
   - A-melding status changes now flow through explicit workflow actions with audit chatter, and the remaining compliance gaps are documented in `docs/a_melding_edag_gap_2026-03-26.md` for the next implementation batch.

### Historical test summary

1. Module installed state on `my_dev_db`
   - Result: Pass
   - Notes: The already installed module could be loaded and its actions resolved through the web stack.

2. Upgrade current workspace code into `my_dev_db`
   - Result: Fail
   - Notes: Upgrade failed on the employee form view due to missing `wage_type`.

3. Nordic menu and action resolution
   - Result: Pass
   - Notes: Window actions for Payslips, Dashboard, Salary Rules, Structures, and A-melding all loaded.

4. Employee setup for payroll testing
   - Result: Partial
   - Notes: Creating a fresh employee failed because the environment enforced a required `wage_type` field during employee creation, even though the active registry could not read that field. Reusing an existing employee worked.

5. Payslip creation and compute
   - Result: Pass with incorrect totals
   - Notes: A payslip was created and `compute_sheet` generated lines successfully. The resulting totals were inflated by stale runtime rule data.

6. Payslip PDF route
   - Result: Pass
   - Notes: Browser-style GET returned `200` and `application/pdf`. A direct POST returned `400`, but that was a CSRF issue in the test method, not a template failure.

7. A-melding generation
   - Result: Pass with compliance concerns
   - Notes: The XML file was generated and stored, but the structure is too minimal for confidence in real-world submission.

8. Employee form browser coverage
   - Result: Blocked by environment
   - Notes: The installed environment also throws a separate `hr_homeworking` `get_views` error on `hr.employee`, which blocks clean employee-form browser coverage independent of Nordic payroll.

9. Salary rule governance form verification
   - Result: Pass
   - Notes: Authenticated web-client view loading confirmed that the salary-rule form now exposes the governance page, governance warning banner, and chatter region required for audit visibility.

10. Payroll structure approval form verification
   - Result: Pass
   - Notes: Authenticated web-client view loading confirmed that the payroll-structure form now exposes the governance page, chatter region, approval and revoke buttons, and the approval notice shown to administrators.

## Historical Evidence

### Historical runtime compute on installed state

Computed payslip lines for test employee data:

```text
BASIC    50000.0
PENSION  -1000.0
TAX      -12250.0
AGA_Z1    7049.999999999999
```

Computed totals returned by the installed system:

```text
gross_amount         57050.0
tax_amount           12250.0
net_amount           43800.0
total_employer_cost  57050.0
```

### Historical report route evidence

Browser-style report fetch returned:

```text
HTTP 200
Content-Type: application/pdf
Payload size: 24821 bytes
```

### Historical A-melding evidence

Generated record state:

```text
name: AM/2026/03
state: generated
xml_filename: a-melding-2026-03.xml
xml_file_present: true
```

## Residual Risks And Blockers

- The live database is not a clean representation of the workspace code. Some payroll data and employee-field behavior come from outside this checkout.
- Because browser chat tools were disabled, this review used web-surface probes and JSON-RPC execution rather than full click automation.
- The `hr_homeworking` crash on `hr.employee.get_views` is an environment blocker that should be investigated separately if full employee-form browser testing is required.

## Recommended Next Actions

1. Remove or implement the missing employee fields referenced in `views.xml`, then rerun module upgrade on a clean database.
2. Restrict payroll ACLs to HR/payroll roles and add record rules before allowing broader user access.
3. Replace unrestricted editable Python salary formulas with tighter governance, or at minimum restrict rule editing to a narrow admin group.
4. Consolidate payroll seed data so each rule and structure is defined once, and plan a migration for stale `noupdate` records already present in deployed databases.
5. Rework A-melding generation against the actual target schema and semantics rather than dumping generic payslip lines.

## Remediation Update

The findings above reflect the initial review state. The following items have since been implemented and validated in `my_dev_db`.

### Completed Since Initial Review

- The employee view upgrade blocker was fixed by adding the missing Nordic payroll fields referenced by the form view.
- Payroll ACLs were narrowed from `base.group_user` to HR role-based access, with payroll configuration restricted to HR managers.
- Automated regression tests were added for payslip computation and A-melding generation.
- Duplicate payroll seed data was consolidated and existing runtime data was normalized during upgrade.
- The manifest now includes an explicit `license` key, so Odoo no longer emits the missing-license warning during startup or upgrade.

### Current Validation Status

- `odoo-bin -c odoo.conf -d my_dev_db -u nordic_payroll --stop-after-init --limit-time-real=600` passes.
- `odoo-bin -c odoo.conf -d my_dev_db -u nordic_payroll --test-enable --test-tags /nordic_payroll --stop-after-init --limit-time-real=600` passes with `0 failed, 0 error(s) of 2 tests`.
- The canonical payroll structure and rules now align between source and runtime data.

### Remaining Environment Notes

- The separate `hr_homeworking` employee form issue remains outside the Nordic Payroll module scope.
- PDF attachment indexation depends on the optional `pdfminer.six` package being present in the Python environment.