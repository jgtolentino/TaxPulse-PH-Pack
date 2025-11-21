-- Copyright 2025 InsightPulse AI Finance SSC
-- Supabase schema for Philippine BIR tax compliance
-- Multi-agency Finance SSC with Row-Level Security (RLS)

-- Create schema for BIR tax data
CREATE SCHEMA IF NOT EXISTS bir;

-- =====================================================
-- Table: bir.agencies
-- Purpose: Multi-agency management (8 agencies)
-- =====================================================
CREATE TABLE IF NOT EXISTS bir.agencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    tin TEXT,
    rdo_code TEXT,
    line_of_business TEXT,
    address TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on agencies
ALTER TABLE bir.agencies ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Allow authenticated users to view all agencies
CREATE POLICY "Authenticated users can view agencies"
ON bir.agencies FOR SELECT
USING (auth.role() = 'authenticated');

-- RLS Policy: Service role full access
CREATE POLICY "Service role full access on agencies"
ON bir.agencies FOR ALL
USING (auth.jwt()->>'role' = 'service_role');

-- =====================================================
-- Table: bir.form_1601c
-- Purpose: Monthly Withholding Tax (Compensation & Final)
-- =====================================================
CREATE TABLE IF NOT EXISTS bir.form_1601c (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    odoo_id INTEGER UNIQUE,
    agency_code TEXT NOT NULL REFERENCES bir.agencies(code),
    agency_name TEXT NOT NULL,
    form_number TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    month TEXT NOT NULL,
    year TEXT NOT NULL,
    compensation_tax NUMERIC(12,2) DEFAULT 0,
    final_tax NUMERIC(12,2) DEFAULT 0,
    total_tax_withheld NUMERIC(12,2) DEFAULT 0,
    state TEXT DEFAULT 'draft',
    tin TEXT,
    rdo_code TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on form_1601c
ALTER TABLE bir.form_1601c ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Agency-scoped access
CREATE POLICY "Agency members can view agency 1601c forms"
ON bir.form_1601c FOR SELECT
USING (
    agency_code IN (
        SELECT agency_code
        FROM bir.user_agency_access
        WHERE user_id = auth.uid()
    )
);

-- RLS Policy: Service role full access
CREATE POLICY "Service role full access on form_1601c"
ON bir.form_1601c FOR ALL
USING (auth.jwt()->>'role' = 'service_role');

-- Indexes for performance
CREATE INDEX idx_form_1601c_agency ON bir.form_1601c(agency_code, period_end DESC);
CREATE INDEX idx_form_1601c_period ON bir.form_1601c(period_start, period_end);
CREATE INDEX idx_form_1601c_state ON bir.form_1601c(state, period_end DESC);

-- =====================================================
-- Table: bir.form_2550q
-- Purpose: Quarterly VAT Return
-- =====================================================
CREATE TABLE IF NOT EXISTS bir.form_2550q (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    odoo_id INTEGER UNIQUE,
    agency_code TEXT NOT NULL REFERENCES bir.agencies(code),
    agency_name TEXT NOT NULL,
    form_number TEXT NOT NULL,
    quarter_start DATE NOT NULL,
    quarter_end DATE NOT NULL,
    quarter TEXT NOT NULL,
    year TEXT NOT NULL,
    output_vat NUMERIC(12,2) DEFAULT 0,
    input_vat NUMERIC(12,2) DEFAULT 0,
    vat_payable NUMERIC(12,2) DEFAULT 0,
    state TEXT DEFAULT 'draft',
    tin TEXT,
    rdo_code TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on form_2550q
ALTER TABLE bir.form_2550q ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Agency-scoped access
CREATE POLICY "Agency members can view agency 2550q forms"
ON bir.form_2550q FOR SELECT
USING (
    agency_code IN (
        SELECT agency_code
        FROM bir.user_agency_access
        WHERE user_id = auth.uid()
    )
);

-- RLS Policy: Service role full access
CREATE POLICY "Service role full access on form_2550q"
ON bir.form_2550q FOR ALL
USING (auth.jwt()->>'role' = 'service_role');

-- Indexes for performance
CREATE INDEX idx_form_2550q_agency ON bir.form_2550q(agency_code, quarter_end DESC);
CREATE INDEX idx_form_2550q_quarter ON bir.form_2550q(quarter_start, quarter_end);
CREATE INDEX idx_form_2550q_state ON bir.form_2550q(state, quarter_end DESC);

-- =====================================================
-- Table: bir.form_1702rt
-- Purpose: Annual Income Tax Return
-- =====================================================
CREATE TABLE IF NOT EXISTS bir.form_1702rt (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    odoo_id INTEGER UNIQUE,
    agency_code TEXT NOT NULL REFERENCES bir.agencies(code),
    agency_name TEXT NOT NULL,
    form_number TEXT NOT NULL,
    fiscal_year TEXT NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    gross_income NUMERIC(14,2) DEFAULT 0,
    deductions NUMERIC(14,2) DEFAULT 0,
    taxable_income NUMERIC(14,2) DEFAULT 0,
    income_tax_due NUMERIC(14,2) DEFAULT 0,
    tax_credits NUMERIC(14,2) DEFAULT 0,
    net_tax_payable NUMERIC(14,2) DEFAULT 0,
    state TEXT DEFAULT 'draft',
    tin TEXT,
    rdo_code TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on form_1702rt
ALTER TABLE bir.form_1702rt ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Agency-scoped access
CREATE POLICY "Agency members can view agency 1702rt forms"
ON bir.form_1702rt FOR SELECT
USING (
    agency_code IN (
        SELECT agency_code
        FROM bir.user_agency_access
        WHERE user_id = auth.uid()
    )
);

-- RLS Policy: Service role full access
CREATE POLICY "Service role full access on form_1702rt"
ON bir.form_1702rt FOR ALL
USING (auth.jwt()->>'role' = 'service_role');

-- Indexes for performance
CREATE INDEX idx_form_1702rt_agency ON bir.form_1702rt(agency_code, fiscal_year DESC);
CREATE INDEX idx_form_1702rt_fiscal_year ON bir.form_1702rt(fiscal_year);
CREATE INDEX idx_form_1702rt_state ON bir.form_1702rt(state, fiscal_year DESC);

-- =====================================================
-- Table: bir.user_agency_access
-- Purpose: User-agency access control for RLS
-- =====================================================
CREATE TABLE IF NOT EXISTS bir.user_agency_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agency_code TEXT NOT NULL REFERENCES bir.agencies(code),
    role TEXT DEFAULT 'viewer', -- viewer, editor, admin
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on user_agency_access
ALTER TABLE bir.user_agency_access ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can view their own access
CREATE POLICY "Users can view own agency access"
ON bir.user_agency_access FOR SELECT
USING (user_id = auth.uid());

-- RLS Policy: Service role full access
CREATE POLICY "Service role full access on user_agency_access"
ON bir.user_agency_access FOR ALL
USING (auth.jwt()->>'role' = 'service_role');

-- Indexes for performance
CREATE INDEX idx_user_agency_access_user ON bir.user_agency_access(user_id, agency_code);
CREATE UNIQUE INDEX idx_user_agency_access_unique ON bir.user_agency_access(user_id, agency_code);

-- =====================================================
-- Updated_at trigger function
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables
CREATE TRIGGER update_agencies_updated_at
    BEFORE UPDATE ON bir.agencies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_form_1601c_updated_at
    BEFORE UPDATE ON bir.form_1601c
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_form_2550q_updated_at
    BEFORE UPDATE ON bir.form_2550q
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_form_1702rt_updated_at
    BEFORE UPDATE ON bir.form_1702rt
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Insert default agencies (8 agencies)
-- =====================================================
INSERT INTO bir.agencies (code, name) VALUES
    ('RIM', 'RIM Agency'),
    ('CKVC', 'CKVC Agency'),
    ('BOM', 'BOM Agency'),
    ('JPAL', 'JPAL Agency'),
    ('JLI', 'JLI Agency'),
    ('JAP', 'JAP Agency'),
    ('LAS', 'LAS Agency'),
    ('RMQB', 'RMQB Agency')
ON CONFLICT (code) DO NOTHING;
