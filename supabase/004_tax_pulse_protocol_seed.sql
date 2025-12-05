-- 004_tax_pulse_protocol_seed.sql
-- Finance Tax Pulse: Review Protocol v1 Seed
-- Copyright 2025 InsightPulse AI Finance SSC

INSERT INTO tax_pulse_protocols (version, label, description, protocol_text)
VALUES (
  'v1',
  'High Compliance Mode',
  'Strict reconciliations, low variance tolerance, detailed SSC memo. Default for high-risk periods and new entities.',
  $$FINANCE TAX PULSE – REVIEW PROTOCOL v1
================================================================================
High Compliance Mode
================================================================================

OVERVIEW
--------
This protocol governs the AI-assisted review of Philippine BIR tax compliance
data for InsightPulse AI Finance SSC multi-agency operations. It establishes
strict reconciliation standards, low variance tolerance, and detailed memo
requirements suitable for high-risk periods and new entities.

APPLICABLE TAX TYPES
--------------------
- BIR Form 1601-C: Monthly Withholding Tax (Compensation & Final)
- BIR Form 2550Q: Quarterly VAT Return
- BIR Form 1702-RT: Annual Income Tax Return

================================================================================
SECTION 1: SCORING DIMENSIONS
================================================================================

The Finance Tax Pulse orchestrator evaluates tax compliance across five
dimensions, each scored 0-100:

D1. COMPLIANCE ACCURACY (Weight: 30%)
-------------------------------------
Measures adherence to BIR regulations and proper form completion.

Evaluation criteria:
- All required fields populated per BIR form specifications
- Correct tax codes and ATC (Alphanumeric Tax Code) usage
- Proper TIN format validation (XXX-XXX-XXX-XXX)
- RDO code alignment with registered address
- Signatory and preparer information complete

Scoring guide:
- 90-100: Full compliance, no missing required fields
- 70-89:  Minor omissions, non-critical fields missing
- 50-69:  Moderate gaps, some required fields missing
- 0-49:   Significant compliance failures

D2. NUMERICAL ACCURACY (Weight: 25%)
------------------------------------
Validates mathematical correctness and data integrity.

Evaluation criteria:
- Tax computations match statutory rates
- Totals reconcile to supporting schedules
- Cross-footing checks pass (row/column totals)
- Rounding applied per BIR rules (centavo precision)
- Variance from GL < 0.01% threshold

Scoring guide:
- 90-100: All computations verified, zero variance
- 70-89:  Minor rounding differences only
- 50-69:  Computation errors found but < 1% of total
- 0-49:   Material computation errors > 1%

D3. COVERAGE & RISK EXPOSURE (Weight: 20%)
------------------------------------------
Assesses completeness of tax positions and risk identification.

Evaluation criteria:
- All taxable transactions captured
- Exempt and zero-rated items properly classified
- Input VAT claims supported by valid invoices
- Withholding obligations identified for all payments
- Potential audit triggers flagged

Scoring guide:
- 90-100: Comprehensive coverage, risks documented
- 70-89:  Minor coverage gaps, low-risk items
- 50-69:  Moderate gaps, some risk exposure
- 0-49:   Significant uncovered positions

D4. TIMELINESS & OPERATIONAL FIT (Weight: 15%)
----------------------------------------------
Evaluates deadline adherence and workflow integration.

Evaluation criteria:
- Filing deadline buffer (days before due date)
- Amendment frequency (lower is better)
- Process cycle time vs. benchmark
- Integration with closing calendar
- Escalation triggers defined

Scoring guide:
- 90-100: Filed >5 days early, no amendments
- 70-89:  Filed on time, <=1 amendment
- 50-69:  Filed on deadline, 2-3 amendments
- 0-49:   Late filing or >3 amendments

D5. CLARITY & AUDITABILITY (Weight: 10%)
----------------------------------------
Measures documentation quality and audit readiness.

Evaluation criteria:
- Working paper completeness
- Trail from source to return clear
- Reconciliation documentation
- Exception explanations provided
- BIR inquiry response readiness

Scoring guide:
- 90-100: Audit-ready, full documentation
- 70-89:  Good documentation, minor gaps
- 50-69:  Basic documentation only
- 0-49:   Insufficient audit trail

================================================================================
SECTION 2: VARIANCE TOLERANCE (High Compliance Mode)
================================================================================

Maximum acceptable variances for v1 High Compliance Mode:

| Check Type                  | Threshold | Action if Exceeded |
|-----------------------------|-----------|-------------------|
| GL vs Return Total          | 0.01%     | Block submission  |
| Subledger vs Return         | 0.01%     | Block submission  |
| Period-over-Period Change   | 15%       | Require narrative |
| Individual Line Item        | PHP 100   | Flag for review   |
| Cross-agency Consistency    | 5%        | Escalate to SSC   |

================================================================================
SECTION 3: RECONCILIATION REQUIREMENTS
================================================================================

3.1 MANDATORY RECONCILIATIONS
-----------------------------
All returns must include:

a) GL-to-Return Reconciliation
   - Export trial balance for tax accounts
   - Map GL codes to BIR line items
   - Document all adjustments
   - Sign-off by preparer and reviewer

b) Subledger-to-Return Reconciliation
   - Tie detailed listings to return totals
   - Explain timing differences
   - Document excluded items with rationale

c) Period-over-Period Analysis
   - Compare to same period prior year
   - Compare to prior period
   - Explain material variances (>15%)

3.2 SUPPORTING SCHEDULES
------------------------
Attach or reference:
- Sales/Output VAT register
- Purchases/Input VAT register
- Withholding tax expanded schedule (by ATC)
- Summary of Alphalist (for 1601-C)
- Income statement mapping (for 1702-RT)

================================================================================
SECTION 4: AUTHORITY HIERARCHY
================================================================================

When citing tax authority, follow this precedence:

TIER 0 - PRIMARY LAW (Binding)
- National Internal Revenue Code (NIRC) as amended
- Republic Acts (TRAIN Law, CREATE Law, etc.)
- Source: officialgazette.gov.ph, dof.gov.ph

TIER 1 - ADMINISTRATIVE (Implementing)
- Revenue Regulations (RR)
- Revenue Memorandum Circulars (RMC)
- Revenue Memorandum Orders (RMO)
- BIR Rulings
- Source: bir.gov.ph

TIER 2 - JUDICIAL/RESEARCH (Interpretive)
- Supreme Court decisions
- Court of Tax Appeals decisions
- NTRC publications
- Source: judiciary.gov.ph, ntrc.gov.ph

TIER 3 - PRACTITIONER (Guidance Only)
- PICPA technical guidance
- TMAP best practices
- Big 4 / advisory firm publications
- Source: picpa.com.ph, tmap.org.ph

Citation Rule: Always cite the highest applicable tier. Lower-tier sources
may supplement but never override higher-tier authority.

================================================================================
SECTION 5: MEMO OUTPUT STRUCTURE
================================================================================

Each review produces a structured memo with:

5.1 HEADER
----------
- Entity/Agency: [Name and Code]
- Period: [Start Date] to [End Date]
- Tax Types: [1601-C, 2550Q, 1702-RT]
- Protocol Version: v1 (High Compliance Mode)
- Review Date: [Timestamp]

5.2 EXECUTIVE SUMMARY
---------------------
- Overall compliance status (Pass/Conditional/Fail)
- Composite score (weighted average of D1-D5)
- Key findings (top 3)
- Recommended actions

5.3 DIMENSION SCORES
--------------------
| Dimension              | Score | Weight | Weighted |
|------------------------|-------|--------|----------|
| D1 Compliance Accuracy | XX    | 30%    | XX.X     |
| D2 Numerical Accuracy  | XX    | 25%    | XX.X     |
| D3 Coverage & Risk     | XX    | 20%    | XX.X     |
| D4 Timeliness          | XX    | 15%    | XX.X     |
| D5 Clarity             | XX    | 10%    | XX.X     |
| COMPOSITE              | --    | 100%   | XX.X     |

5.4 DETAILED FINDINGS
---------------------
For each dimension, provide:
- Specific observations
- Evidence/data points
- Citations to authority
- Remediation steps

5.5 RECONCILIATION SUMMARY
--------------------------
| Check                   | GL Amount | Return Amount | Variance | Status |
|-------------------------|-----------|---------------|----------|--------|
| [Per reconciliation]    | X,XXX.XX  | X,XXX.XX      | X.XX     | PASS   |

5.6 RISK FLAGS
--------------
List any audit triggers or risk items:
- [Risk item with severity: High/Medium/Low]

5.7 IMPROVEMENT OPPORTUNITIES
-----------------------------
Prioritized list of process improvements for next period.

================================================================================
SECTION 6: ESCALATION TRIGGERS
================================================================================

Immediate escalation to SSC Finance Lead required when:

1. Composite score < 70
2. Any single dimension < 50
3. Variance exceeds block threshold
4. Potential fraud indicators detected
5. BIR audit notice received
6. Material prior period adjustment needed
7. Cross-agency inconsistency > 5%

================================================================================
SECTION 7: PROTOCOL MAINTENANCE
================================================================================

- Protocol Owner: SSC Finance Lead
- Review Frequency: Quarterly or upon regulatory change
- Version Control: All changes logged with rationale
- Effective Date Tracking: Each version has effective_from date

Change Request Process:
1. Submit change request with justification
2. Impact assessment (scoring, thresholds)
3. Approval by Protocol Owner
4. Update protocol_text in tax_pulse_protocols
5. Communicate to all users

================================================================================
END OF PROTOCOL v1
================================================================================
$$
)
ON CONFLICT (version) DO NOTHING;

-- Add protocol audit log table for tracking changes
CREATE TABLE IF NOT EXISTS tax_pulse_protocol_audit (
  id            bigserial PRIMARY KEY,
  version       text NOT NULL REFERENCES tax_pulse_protocols(version),
  action        text NOT NULL CHECK (action IN ('created', 'activated', 'deactivated', 'updated')),
  changed_by    text,
  change_reason text,
  changed_at    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE tax_pulse_protocol_audit IS 'Audit trail for protocol changes';

-- Log the initial v1 protocol creation
INSERT INTO tax_pulse_protocol_audit (version, action, changed_by, change_reason)
VALUES ('v1', 'created', 'system', 'Initial High Compliance Mode protocol for TaxPulse PH Pack')
ON CONFLICT DO NOTHING;
