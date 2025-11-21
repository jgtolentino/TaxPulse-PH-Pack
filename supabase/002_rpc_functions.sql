-- Copyright 2025 InsightPulse AI Finance SSC
-- RPC Functions for Odoo-Supabase synchronization

-- =====================================================
-- Function: upsert_bir_1601c
-- Purpose: Upsert BIR Form 1601-C from Odoo
-- =====================================================
CREATE OR REPLACE FUNCTION upsert_bir_1601c(
    p_odoo_id INTEGER,
    p_agency_code TEXT,
    p_agency_name TEXT,
    p_form_number TEXT,
    p_period_start DATE,
    p_period_end DATE,
    p_month TEXT,
    p_year TEXT,
    p_compensation_tax NUMERIC DEFAULT NULL,
    p_final_tax NUMERIC DEFAULT NULL,
    p_total_tax_withheld NUMERIC DEFAULT NULL,
    p_state TEXT DEFAULT 'draft',
    p_tin TEXT DEFAULT NULL,
    p_rdo_code TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_form_id UUID;
BEGIN
    -- Upsert with odoo_id as conflict key
    INSERT INTO bir.form_1601c (
        odoo_id, agency_code, agency_name, form_number,
        period_start, period_end, month, year,
        compensation_tax, final_tax, total_tax_withheld,
        state, tin, rdo_code
    ) VALUES (
        p_odoo_id, p_agency_code, p_agency_name, p_form_number,
        p_period_start, p_period_end, p_month, p_year,
        p_compensation_tax, p_final_tax, p_total_tax_withheld,
        p_state, p_tin, p_rdo_code
    )
    ON CONFLICT (odoo_id)
    DO UPDATE SET
        agency_code = EXCLUDED.agency_code,
        agency_name = EXCLUDED.agency_name,
        form_number = EXCLUDED.form_number,
        period_start = EXCLUDED.period_start,
        period_end = EXCLUDED.period_end,
        month = EXCLUDED.month,
        year = EXCLUDED.year,
        compensation_tax = EXCLUDED.compensation_tax,
        final_tax = EXCLUDED.final_tax,
        total_tax_withheld = EXCLUDED.total_tax_withheld,
        state = EXCLUDED.state,
        tin = EXCLUDED.tin,
        rdo_code = EXCLUDED.rdo_code,
        updated_at = NOW()
    RETURNING id INTO v_form_id;

    RETURN v_form_id;
END;
$$;

-- =====================================================
-- Function: upsert_bir_2550q
-- Purpose: Upsert BIR Form 2550Q from Odoo
-- =====================================================
CREATE OR REPLACE FUNCTION upsert_bir_2550q(
    p_odoo_id INTEGER,
    p_agency_code TEXT,
    p_agency_name TEXT,
    p_form_number TEXT,
    p_quarter_start DATE,
    p_quarter_end DATE,
    p_quarter TEXT,
    p_year TEXT,
    p_output_vat NUMERIC DEFAULT NULL,
    p_input_vat NUMERIC DEFAULT NULL,
    p_vat_payable NUMERIC DEFAULT NULL,
    p_state TEXT DEFAULT 'draft',
    p_tin TEXT DEFAULT NULL,
    p_rdo_code TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_form_id UUID;
BEGIN
    -- Upsert with odoo_id as conflict key
    INSERT INTO bir.form_2550q (
        odoo_id, agency_code, agency_name, form_number,
        quarter_start, quarter_end, quarter, year,
        output_vat, input_vat, vat_payable,
        state, tin, rdo_code
    ) VALUES (
        p_odoo_id, p_agency_code, p_agency_name, p_form_number,
        p_quarter_start, p_quarter_end, p_quarter, p_year,
        p_output_vat, p_input_vat, p_vat_payable,
        p_state, p_tin, p_rdo_code
    )
    ON CONFLICT (odoo_id)
    DO UPDATE SET
        agency_code = EXCLUDED.agency_code,
        agency_name = EXCLUDED.agency_name,
        form_number = EXCLUDED.form_number,
        quarter_start = EXCLUDED.quarter_start,
        quarter_end = EXCLUDED.quarter_end,
        quarter = EXCLUDED.quarter,
        year = EXCLUDED.year,
        output_vat = EXCLUDED.output_vat,
        input_vat = EXCLUDED.input_vat,
        vat_payable = EXCLUDED.vat_payable,
        state = EXCLUDED.state,
        tin = EXCLUDED.tin,
        rdo_code = EXCLUDED.rdo_code,
        updated_at = NOW()
    RETURNING id INTO v_form_id;

    RETURN v_form_id;
END;
$$;

-- =====================================================
-- Function: upsert_bir_1702rt
-- Purpose: Upsert BIR Form 1702-RT from Odoo
-- =====================================================
CREATE OR REPLACE FUNCTION upsert_bir_1702rt(
    p_odoo_id INTEGER,
    p_agency_code TEXT,
    p_agency_name TEXT,
    p_form_number TEXT,
    p_fiscal_year TEXT,
    p_period_start DATE,
    p_period_end DATE,
    p_gross_income NUMERIC DEFAULT NULL,
    p_deductions NUMERIC DEFAULT NULL,
    p_taxable_income NUMERIC DEFAULT NULL,
    p_income_tax_due NUMERIC DEFAULT NULL,
    p_tax_credits NUMERIC DEFAULT NULL,
    p_net_tax_payable NUMERIC DEFAULT NULL,
    p_state TEXT DEFAULT 'draft',
    p_tin TEXT DEFAULT NULL,
    p_rdo_code TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_form_id UUID;
BEGIN
    -- Upsert with odoo_id as conflict key
    INSERT INTO bir.form_1702rt (
        odoo_id, agency_code, agency_name, form_number,
        fiscal_year, period_start, period_end,
        gross_income, deductions, taxable_income,
        income_tax_due, tax_credits, net_tax_payable,
        state, tin, rdo_code
    ) VALUES (
        p_odoo_id, p_agency_code, p_agency_name, p_form_number,
        p_fiscal_year, p_period_start, p_period_end,
        p_gross_income, p_deductions, p_taxable_income,
        p_income_tax_due, p_tax_credits, p_net_tax_payable,
        p_state, p_tin, p_rdo_code
    )
    ON CONFLICT (odoo_id)
    DO UPDATE SET
        agency_code = EXCLUDED.agency_code,
        agency_name = EXCLUDED.agency_name,
        form_number = EXCLUDED.form_number,
        fiscal_year = EXCLUDED.fiscal_year,
        period_start = EXCLUDED.period_start,
        period_end = EXCLUDED.period_end,
        gross_income = EXCLUDED.gross_income,
        deductions = EXCLUDED.deductions,
        taxable_income = EXCLUDED.taxable_income,
        income_tax_due = EXCLUDED.income_tax_due,
        tax_credits = EXCLUDED.tax_credits,
        net_tax_payable = EXCLUDED.net_tax_payable,
        state = EXCLUDED.state,
        tin = EXCLUDED.tin,
        rdo_code = EXCLUDED.rdo_code,
        updated_at = NOW()
    RETURNING id INTO v_form_id;

    RETURN v_form_id;
END;
$$;

-- =====================================================
-- Function: get_bir_dashboard_stats
-- Purpose: Get aggregated statistics for Superset dashboards
-- =====================================================
CREATE OR REPLACE FUNCTION get_bir_dashboard_stats(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    form_type TEXT,
    agency_code TEXT,
    count_forms BIGINT,
    total_tax NUMERIC,
    avg_tax NUMERIC,
    period_start DATE,
    period_end DATE
)
LANGUAGE sql
STABLE
AS $$
    -- BIR 1601-C stats
    SELECT
        '1601-C' as form_type,
        agency_code,
        COUNT(*) as count_forms,
        SUM(total_tax_withheld) as total_tax,
        AVG(total_tax_withheld) as avg_tax,
        MIN(period_start) as period_start,
        MAX(period_end) as period_end
    FROM bir.form_1601c
    WHERE state = 'posted'
        AND (p_start_date IS NULL OR period_start >= p_start_date)
        AND (p_end_date IS NULL OR period_end <= p_end_date)
    GROUP BY agency_code

    UNION ALL

    -- BIR 2550Q stats
    SELECT
        '2550Q' as form_type,
        agency_code,
        COUNT(*) as count_forms,
        SUM(vat_payable) as total_tax,
        AVG(vat_payable) as avg_tax,
        MIN(quarter_start) as period_start,
        MAX(quarter_end) as period_end
    FROM bir.form_2550q
    WHERE state = 'posted'
        AND (p_start_date IS NULL OR quarter_start >= p_start_date)
        AND (p_end_date IS NULL OR quarter_end <= p_end_date)
    GROUP BY agency_code

    UNION ALL

    -- BIR 1702-RT stats
    SELECT
        '1702-RT' as form_type,
        agency_code,
        COUNT(*) as count_forms,
        SUM(net_tax_payable) as total_tax,
        AVG(net_tax_payable) as avg_tax,
        MIN(period_start) as period_start,
        MAX(period_end) as period_end
    FROM bir.form_1702rt
    WHERE state = 'posted'
        AND (p_start_date IS NULL OR period_start >= p_start_date)
        AND (p_end_date IS NULL OR period_end <= p_end_date)
    GROUP BY agency_code;
$$;
