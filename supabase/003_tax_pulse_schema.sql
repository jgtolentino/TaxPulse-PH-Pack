-- 003_tax_pulse_schema.sql
-- Finance Tax Pulse: Authority Registry + Run Log Schema
-- Copyright 2025 InsightPulse AI Finance SSC

-- =====================================================
-- 1) Authority registry - trusted tax source domains
-- =====================================================
CREATE TABLE IF NOT EXISTS tax_pulse_sources (
  id           text PRIMARY KEY,
  tier         integer NOT NULL CHECK (tier BETWEEN 0 AND 3),
  kind         text NOT NULL CHECK (kind IN ('law','admin','research','jurisprudence','practitioner')),
  domain       text NOT NULL,
  path_pattern text,
  label        text NOT NULL,
  description  text NOT NULL,
  active       boolean NOT NULL DEFAULT true,
  created_at   timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE tax_pulse_sources IS 'Registry of authoritative Philippine tax sources by tier';
COMMENT ON COLUMN tax_pulse_sources.tier IS '0=Primary Law, 1=Admin/BIR, 2=Research/Judicial, 3=Practitioner';
COMMENT ON COLUMN tax_pulse_sources.kind IS 'Source type: law, admin, research, jurisprudence, practitioner';

-- =====================================================
-- 2) Source domain aliases (for multi-domain sources)
-- =====================================================
CREATE TABLE IF NOT EXISTS tax_pulse_source_aliases (
  id         bigserial PRIMARY KEY,
  source_id  text NOT NULL REFERENCES tax_pulse_sources(id) ON DELETE CASCADE,
  domain     text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE tax_pulse_source_aliases IS 'Alternate domains for tax sources (e.g., elibrary.judiciary.gov.ph)';

-- =====================================================
-- 3) Protocol registry - Review Protocol versions
-- =====================================================
CREATE TABLE IF NOT EXISTS tax_pulse_protocols (
  version        text PRIMARY KEY,     -- 'v1','v2','v1.1', etc.
  label          text NOT NULL,
  description    text NOT NULL,
  protocol_text  text NOT NULL,
  is_active      boolean NOT NULL DEFAULT true,
  created_at     timestamptz NOT NULL DEFAULT now(),
  created_by     text
);

COMMENT ON TABLE tax_pulse_protocols IS 'Versioned review protocols for Finance Tax Pulse orchestrator';
COMMENT ON COLUMN tax_pulse_protocols.protocol_text IS 'Full protocol document text used as system prompt input';

-- =====================================================
-- 4) Run log - stores each Tax Pulse review run
-- =====================================================
CREATE TABLE IF NOT EXISTS tax_pulse_run_log (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_ts           timestamptz NOT NULL DEFAULT now(),
  entity_id        text NOT NULL,
  period_start     date NOT NULL,
  period_end       date NOT NULL,
  tax_types        text[] NOT NULL,
  protocol_version text NOT NULL REFERENCES tax_pulse_protocols(version),

  -- Dimension scores (0-100)
  score_compliance numeric NOT NULL CHECK (score_compliance BETWEEN 0 AND 100),
  score_numeric    numeric NOT NULL CHECK (score_numeric BETWEEN 0 AND 100),
  score_coverage   numeric NOT NULL CHECK (score_coverage BETWEEN 0 AND 100),
  score_timeliness numeric NOT NULL CHECK (score_timeliness BETWEEN 0 AND 100),
  score_clarity    numeric NOT NULL CHECK (score_clarity BETWEEN 0 AND 100),

  -- Analysis results
  weakest_dimension text NOT NULL,
  weakest_reason    text,
  improvement_ideas text,

  -- Memo and raw output
  memo_summary      text,
  raw_output_ref    text,

  -- Metadata
  created_at       timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE tax_pulse_run_log IS 'Audit log of Finance Tax Pulse AI review runs';
COMMENT ON COLUMN tax_pulse_run_log.entity_id IS 'Agency code or entity identifier being reviewed';
COMMENT ON COLUMN tax_pulse_run_log.tax_types IS 'Array of BIR form types reviewed (1601-C, 2550Q, 1702-RT)';

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tax_pulse_run_log_entity ON tax_pulse_run_log(entity_id);
CREATE INDEX IF NOT EXISTS idx_tax_pulse_run_log_period ON tax_pulse_run_log(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_tax_pulse_run_log_ts ON tax_pulse_run_log(run_ts DESC);

-- =====================================================
-- 5) Domain helper view - unified source domain lookup
-- =====================================================
CREATE OR REPLACE VIEW v_tax_pulse_source_domains AS
SELECT
  s.id         AS source_id,
  s.tier,
  s.kind,
  s.label,
  s.description,
  s.active,
  s.domain     AS domain
FROM tax_pulse_sources s
UNION ALL
SELECT
  a.source_id  AS source_id,
  s.tier,
  s.kind,
  s.label,
  s.description,
  s.active,
  a.domain     AS domain
FROM tax_pulse_source_aliases a
JOIN tax_pulse_sources s
  ON s.id = a.source_id;

COMMENT ON VIEW v_tax_pulse_source_domains IS 'Unified view of all tax source domains including aliases';

-- =====================================================
-- 6) Protocol performance helper view
-- =====================================================
CREATE OR REPLACE VIEW v_tax_pulse_protocol_stats AS
SELECT
  protocol_version,
  count(*) AS run_count,
  avg(score_compliance) AS avg_compliance,
  avg(score_numeric)    AS avg_numeric,
  avg(score_coverage)   AS avg_coverage,
  avg(score_timeliness) AS avg_timeliness,
  avg(score_clarity)    AS avg_clarity,
  min(run_ts) AS first_run,
  max(run_ts) AS last_run
FROM tax_pulse_run_log
GROUP BY protocol_version;

COMMENT ON VIEW v_tax_pulse_protocol_stats IS 'Aggregate statistics per protocol version for performance tracking';

-- =====================================================
-- 7) Seed authority sources - Tier 0: Primary Law
-- =====================================================
INSERT INTO tax_pulse_sources (id, tier, kind, domain, label, description) VALUES
  ('nirc_official_gazette', 0, 'law', 'officialgazette.gov.ph',
   'National Internal Revenue Code (as amended)',
   'Consolidated text of the NIRC of 1997 as amended by TRAIN, CREATE and other tax laws.'),
  ('tax_laws_dof', 0, 'law', 'dof.gov.ph',
   'Tax-related Republic Acts and DOF tax law pages',
   'Official DOF pages and Republic Acts that amend or supplement the NIRC.')
ON CONFLICT (id) DO NOTHING;

-- =====================================================
-- 8) Seed authority sources - Tier 1: Administrative/BIR
-- =====================================================
INSERT INTO tax_pulse_sources (id, tier, kind, domain, path_pattern, label, description) VALUES
  ('bir_main', 1, 'admin', 'bir.gov.ph', NULL,
   'BIR main site',
   'Official BIR site including tax code copy, forms, FAQs and guides.'),
  ('bir_revenue_issuances', 1, 'admin', 'bir.gov.ph', '/index.php/revenue-issuances',
   'BIR Revenue Issuances',
   'Revenue Regulations, Revenue Memorandum Circulars, RMOs and related issuances implementing the NIRC.'),
  ('bir_tax_guides', 1, 'admin', 'bir.gov.ph', '/index.php/tax-information',
   'BIR Tax Guides',
   'BIR-prepared guides, primers and FAQs by tax type (VAT, withholding, etc.).')
ON CONFLICT (id) DO NOTHING;

-- =====================================================
-- 9) Seed authority sources - Tier 2: Research/Judicial
-- =====================================================
INSERT INTO tax_pulse_sources (id, tier, kind, domain, label, description) VALUES
  ('ntrc_main', 2, 'research', 'ntrc.gov.ph',
   'National Tax Research Center',
   'DOF-attached research body that compiles tax laws, BIR issuances and analytical papers.'),
  ('ph_supreme_court_elibrary', 2, 'jurisprudence', 'judiciary.gov.ph',
   'Philippine Supreme Court / CTA E-Library',
   'Official e-library for Supreme Court and Court of Tax Appeals decisions on tax controversies.')
ON CONFLICT (id) DO NOTHING;

-- Add alias for judiciary e-library subdomain
INSERT INTO tax_pulse_source_aliases (source_id, domain)
VALUES ('ph_supreme_court_elibrary', 'elibrary.judiciary.gov.ph')
ON CONFLICT DO NOTHING;

-- =====================================================
-- 10) Seed authority sources - Tier 3: Practitioner
-- =====================================================
INSERT INTO tax_pulse_sources (id, tier, kind, domain, label, description) VALUES
  ('picpa', 3, 'practitioner', 'picpa.com.ph',
   'Philippine Institute of Certified Public Accountants',
   'AIPO for CPAs; use for practice notes and implementation guidance, not binding law.'),
  ('tmap', 3, 'practitioner', 'tmap.org.ph',
   'Tax Management Association of the Philippines',
   'Private-sector tax association. Use for best practices and commentary only.'),
  ('philippine_tax_academy', 3, 'practitioner', 'doftaxacademy.gov.ph',
   'Philippine Tax Academy',
   'State tax-training institution. Use for training materials and high-level guidance.')
ON CONFLICT (id) DO NOTHING;

-- =====================================================
-- 11) RPC Function: Fetch finance data for Tax Pulse
-- =====================================================
CREATE OR REPLACE FUNCTION fn_fetch_finance_data(
    p_entity_id TEXT,
    p_period_start DATE,
    p_period_end DATE,
    p_tax_types TEXT[] DEFAULT ARRAY['1601-C', '2550Q', '1702-RT']
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result JSONB;
    v_1601c JSONB;
    v_2550q JSONB;
    v_1702rt JSONB;
BEGIN
    -- Fetch 1601-C forms if requested
    IF '1601-C' = ANY(p_tax_types) THEN
        SELECT COALESCE(jsonb_agg(row_to_json(f)::jsonb), '[]'::jsonb)
        INTO v_1601c
        FROM bir.form_1601c f
        WHERE f.agency_code = p_entity_id
          AND f.period_start >= p_period_start
          AND f.period_end <= p_period_end;
    ELSE
        v_1601c := '[]'::jsonb;
    END IF;

    -- Fetch 2550Q forms if requested
    IF '2550Q' = ANY(p_tax_types) THEN
        SELECT COALESCE(jsonb_agg(row_to_json(f)::jsonb), '[]'::jsonb)
        INTO v_2550q
        FROM bir.form_2550q f
        WHERE f.agency_code = p_entity_id
          AND f.quarter_start >= p_period_start
          AND f.quarter_end <= p_period_end;
    ELSE
        v_2550q := '[]'::jsonb;
    END IF;

    -- Fetch 1702-RT forms if requested
    IF '1702-RT' = ANY(p_tax_types) THEN
        SELECT COALESCE(jsonb_agg(row_to_json(f)::jsonb), '[]'::jsonb)
        INTO v_1702rt
        FROM bir.form_1702rt f
        WHERE f.agency_code = p_entity_id
          AND f.period_start >= p_period_start
          AND f.period_end <= p_period_end;
    ELSE
        v_1702rt := '[]'::jsonb;
    END IF;

    -- Build result object
    v_result := jsonb_build_object(
        'entity_id', p_entity_id,
        'period_start', p_period_start,
        'period_end', p_period_end,
        'tax_types', p_tax_types,
        'forms', jsonb_build_object(
            '1601-C', v_1601c,
            '2550Q', v_2550q,
            '1702-RT', v_1702rt
        ),
        'fetched_at', now()
    );

    RETURN v_result;
END;
$$;

COMMENT ON FUNCTION fn_fetch_finance_data IS 'Aggregates BIR form data for Finance Tax Pulse review';

-- =====================================================
-- 12) RPC Function: Insert Tax Pulse run log entry
-- =====================================================
CREATE OR REPLACE FUNCTION fn_insert_tax_pulse_run(
    p_entity_id TEXT,
    p_period_start DATE,
    p_period_end DATE,
    p_tax_types TEXT[],
    p_protocol_version TEXT,
    p_score_compliance NUMERIC,
    p_score_numeric NUMERIC,
    p_score_coverage NUMERIC,
    p_score_timeliness NUMERIC,
    p_score_clarity NUMERIC,
    p_weakest_dimension TEXT,
    p_weakest_reason TEXT DEFAULT NULL,
    p_improvement_ideas TEXT DEFAULT NULL,
    p_memo_summary TEXT DEFAULT NULL,
    p_raw_output_ref TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_run_id UUID;
BEGIN
    INSERT INTO tax_pulse_run_log (
        entity_id,
        period_start,
        period_end,
        tax_types,
        protocol_version,
        score_compliance,
        score_numeric,
        score_coverage,
        score_timeliness,
        score_clarity,
        weakest_dimension,
        weakest_reason,
        improvement_ideas,
        memo_summary,
        raw_output_ref
    ) VALUES (
        p_entity_id,
        p_period_start,
        p_period_end,
        p_tax_types,
        p_protocol_version,
        p_score_compliance,
        p_score_numeric,
        p_score_coverage,
        p_score_timeliness,
        p_score_clarity,
        p_weakest_dimension,
        p_weakest_reason,
        p_improvement_ideas,
        p_memo_summary,
        p_raw_output_ref
    )
    RETURNING id INTO v_run_id;

    RETURN v_run_id;
END;
$$;

COMMENT ON FUNCTION fn_insert_tax_pulse_run IS 'Records a Finance Tax Pulse review run with scores and analysis';
