# Product Backlog & Risk Registry

## A. Product Vision
"A unified, automated, and compliant Nordic People Platform that eliminates manual payroll friction and empowers employees through seamless self-service."

## B. Solution Principles
1.  **SaaS First:** Prioritize Odoo standard functionality and configuration over custom code.
2.  **API-Driven:** All integrations with IFS must use secure, versioned REST APIs.
3.  **Security by Design:** MFA, SSO, and role-based access must be enforced globally.
4.  **Compliance by Default:** Every update must be validated against Norwegian tax and labor laws.

## C. Epics
1.  **EPIC-PAY:** Norwegian Payroll Compliance & Engine.
2.  **EPIC-EXP:** Mobile-First Travel & Expense Management.
3.  **EPIC-INT:** Bi-directional IFS Cloud Integration.
4.  **EPIC-NEG:** Compensation Negotiation Framework (Optional).

## D. 25 Concrete User Stories
### Payroll (EPIC-PAY)
1.  **US-PAY-01:** As a Payroll admin, I want to import tax cards from Altinn automatically.
2.  **US-PAY-02:** As an employee, I want to see my historical payslips in a secure portal.
3.  **US-PAY-03:** As a specialist, I want to trigger the monthly a-melding with one click.
4.  **US-PAY-04:** As an admin, I want to define variable pay rules for overtime.
5.  **US-PAY-05:** As a controller, I want to reconcile payroll against the bank file.
6.  **US-PAY-06:** As a specialist, I want to handle retroactive salary adjustments for the last 3 months.
7.  **US-PAY-07:** As an admin, I want to configure different employer contribution rates per zone.
8.  **US-PAY-08:** As a specialist, I want to generate K3/K4 reports for accounting.
### Travel & Expense (EPIC-EXP)
9.  **US-EXP-01:** As an employee, I want to take a photo of a receipt to start a claim.
10. **US-EXP-02:** As a traveler, I want the system to calculate my per-diem based on destination.
11. **US-EXP-03:** As a manager, I want to approve expenses from my mobile device.
12. **US-EXP-04:** As an employee, I want to track the status of my reimbursement.
13. **US-EXP-05:** As a traveler, I want to submit mileage based on Google Maps integration.
14. **US-EXP-06:** As a manager, I want to reject a claim with a specific reason.
15. **US-EXP-07:** As a specialist, I want to export approved expenses to the payroll run.
16. **US-EXP-08:** As a finance user, I want to see receipts attached to journal entries.
### Integration (EPIC-INT)
17. **US-INT-01:** As a system, I want to sync employee master data from IFS every 24 hours.
18. **US-INT-02:** As a system, I want to fetch absence records from IFS for payroll.
19. **US-INT-03:** As an admin, I want to see a log of all failed API calls to IFS.
20. **US-INT-04:** As a system, I want to push GL postings to IFS after payroll closure.
### Compensation & General (EPIC-NEG / GEN)
21. **US-NEG-01:** As a manager, I want to propose a salary increase within my budget.
22. **US-NEG-02:** As HR, I want to simulate the total cost of all proposed salary increments.
23. **US-NEG-03:** As a negotiator, I want to see union-specific benchmarks.
24. **US-SYS-01:** As a user, I want to log in using Azure AD (SSO).
25. **US-SYS-02:** As an auditor, I want a report showing all changes to employee bank accounts.

## E. 10 Biggest Risks
| # | Risk | Impact | Mitigation Action |
|---|---|---|---|
| 1 | IFS Integration latency | High | Use asynchronous batch processing and retry queues. |
| 2 | UBW 2026 EOL deadline | Critical | Establish a strict MVP scope and agile delivery. |
| 3 | Norwegian tax law changes | High | Partner with local Odoo experts for engine updates. |
| 4 | Data quality in legacy migration | Medium | Run automated data cleansing scripts pre-migration. |
| 5 | Low user adoption of mobile | Medium | Prioritize UX design and provide internal training. |
| 6 | GDPR Compliance breach | Critical | Regular penetration tests and automated anonymization. |
| 7 | Scope creep in Compensation | Medium | Pilot with one subsidiary before group-wide rollout. |
| 8 | Security of bank file transfers | High | Use SFTP with PGP encryption and dual-approval. |
| 9 | Resource availability (SMEs) | Medium | Secure dedicated time from HR/Payroll leads early. |
| 10 | Performance during peak runs | High | Load testing for 1,400 concurrent payslip generations. |

## F. Recommended Implementation Sequence
1.  **Foundation:** Setup Odoo Environment + Azure AD SSO.
2.  **Core Integration:** One-way sync from IFS (Employees, Time).
3.  **Payroll MVP:** Nordic Engine configuration + A-melding baseline.
4.  **T&E Rollout:** Mobile app deployment + manager training.
5.  **Parallel Run:** 3 months of dual-running vs Unit4.
6.  **Full Go-Live:** Decommission Unit4 + Phase 2 (Compensation).
