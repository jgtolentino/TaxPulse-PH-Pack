// finance-tax-pulse Edge Function
// Copyright 2025 InsightPulse AI Finance SSC
//
// AI-assisted tax compliance review for Philippine BIR forms
// Integrates with TaxPulse PH Pack Odoo module and Supabase warehouse

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

// Types
interface TaxPulseRequest {
  entity_id: string;
  period_start: string;
  period_end: string;
  tax_types: string[];
  protocol_version?: string;
}

interface DimensionScores {
  compliance: number;
  numeric: number;
  coverage: number;
  timeliness: number;
  clarity: number;
}

interface TaxPulseResult {
  run_id: string;
  entity_id: string;
  period_start: string;
  period_end: string;
  tax_types: string[];
  protocol_version: string;
  scores: DimensionScores;
  composite_score: number;
  weakest_dimension: string;
  weakest_reason: string;
  improvement_ideas: string;
  memo_summary: string;
  status: "pass" | "conditional" | "fail";
}

// Environment variables
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const LLM_API_URL = Deno.env.get("LLM_API_URL") || "https://api.anthropic.com/v1/messages";
const LLM_API_KEY = Deno.env.get("LLM_API_KEY")!;
const LLM_MODEL = Deno.env.get("LLM_MODEL") || "claude-sonnet-4-20250514";

// Initialize Supabase client
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

// CORS headers
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

/**
 * Fetch protocol text from database
 */
async function fetchProtocol(version: string): Promise<string> {
  const { data, error } = await supabase
    .from("tax_pulse_protocols")
    .select("protocol_text")
    .eq("version", version)
    .eq("is_active", true)
    .single();

  if (error || !data) {
    throw new Error(`Protocol ${version} not found or inactive: ${error?.message}`);
  }

  return data.protocol_text;
}

/**
 * Fetch finance data for the entity and period
 */
async function fetchFinanceData(
  entityId: string,
  periodStart: string,
  periodEnd: string,
  taxTypes: string[]
): Promise<Record<string, unknown>> {
  const { data, error } = await supabase.rpc("fn_fetch_finance_data", {
    p_entity_id: entityId,
    p_period_start: periodStart,
    p_period_end: periodEnd,
    p_tax_types: taxTypes,
  });

  if (error) {
    throw new Error(`Failed to fetch finance data: ${error.message}`);
  }

  return data;
}

/**
 * Fetch authority sources for context
 */
async function fetchAuthoritySources(): Promise<Record<string, unknown>[]> {
  const { data, error } = await supabase
    .from("v_tax_pulse_source_domains")
    .select("*")
    .eq("active", true)
    .order("tier", { ascending: true });

  if (error) {
    console.warn("Failed to fetch authority sources:", error.message);
    return [];
  }

  return data || [];
}

/**
 * Build system prompt for the orchestrator
 */
function buildSystemPrompt(protocolText: string, authoritySources: Record<string, unknown>[]): string {
  const sourcesContext = authoritySources
    .map((s) => `- Tier ${s.tier} [${s.kind}]: ${s.label} (${s.domain})`)
    .join("\n");

  return `You are the Finance Tax Pulse Orchestrator, an AI assistant specialized in Philippine BIR tax compliance review.

YOUR MISSION:
Review tax compliance data for Philippine entities and produce structured assessments across five dimensions:
- D1: Compliance Accuracy (30% weight)
- D2: Numerical Accuracy (25% weight)
- D3: Coverage & Risk Exposure (20% weight)
- D4: Timeliness & Operational Fit (15% weight)
- D5: Clarity & Auditability (10% weight)

AUTHORITY SOURCES (cite in order of precedence):
${sourcesContext}

REVIEW PROTOCOL:
${protocolText}

OUTPUT FORMAT:
You must return a valid JSON object with this exact structure:
{
  "scores": {
    "compliance": <0-100>,
    "numeric": <0-100>,
    "coverage": <0-100>,
    "timeliness": <0-100>,
    "clarity": <0-100>
  },
  "weakest_dimension": "<D1|D2|D3|D4|D5>",
  "weakest_reason": "<explanation of weakest area>",
  "improvement_ideas": "<prioritized improvement suggestions>",
  "memo_summary": "<executive summary for SSC memo>",
  "findings": [
    {
      "dimension": "<D1-D5>",
      "severity": "<high|medium|low>",
      "finding": "<specific observation>",
      "citation": "<authority reference if applicable>",
      "remediation": "<suggested fix>"
    }
  ],
  "reconciliations": [
    {
      "check": "<reconciliation type>",
      "gl_amount": <number>,
      "return_amount": <number>,
      "variance": <number>,
      "status": "<pass|fail>"
    }
  ],
  "risk_flags": [
    {
      "item": "<risk description>",
      "severity": "<high|medium|low>"
    }
  ]
}

RULES:
1. Be objective and cite specific data points
2. Use BIR terminology and form references
3. Flag any variance exceeding thresholds
4. Recommend escalation if composite score < 70
5. Return ONLY valid JSON, no markdown or explanations`;
}

/**
 * Call LLM API for tax review
 */
async function callLLM(
  systemPrompt: string,
  financeData: Record<string, unknown>
): Promise<Record<string, unknown>> {
  const userPrompt = `Review the following Philippine tax compliance data and provide your assessment:

ENTITY DATA:
${JSON.stringify(financeData, null, 2)}

Analyze this data according to the Review Protocol and return your structured assessment as JSON.`;

  const response = await fetch(LLM_API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": LLM_API_KEY,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: LLM_MODEL,
      max_tokens: 4096,
      temperature: 0.1,
      system: systemPrompt,
      messages: [
        {
          role: "user",
          content: userPrompt,
        },
      ],
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`LLM API error: ${response.status} - ${errorText}`);
  }

  const result = await response.json();

  // Extract JSON from response
  const content = result.content?.[0]?.text || "";

  // Parse JSON from response (handle potential markdown wrapping)
  let jsonStr = content;
  const jsonMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (jsonMatch) {
    jsonStr = jsonMatch[1];
  }

  try {
    return JSON.parse(jsonStr.trim());
  } catch (e) {
    throw new Error(`Failed to parse LLM response as JSON: ${e}`);
  }
}

/**
 * Calculate composite score from dimension scores
 */
function calculateCompositeScore(scores: DimensionScores): number {
  const weights = {
    compliance: 0.30,
    numeric: 0.25,
    coverage: 0.20,
    timeliness: 0.15,
    clarity: 0.10,
  };

  return (
    scores.compliance * weights.compliance +
    scores.numeric * weights.numeric +
    scores.coverage * weights.coverage +
    scores.timeliness * weights.timeliness +
    scores.clarity * weights.clarity
  );
}

/**
 * Determine status based on composite score
 */
function determineStatus(compositeScore: number, scores: DimensionScores): "pass" | "conditional" | "fail" {
  // Fail if any dimension below 50 or composite below 60
  const minScore = Math.min(
    scores.compliance,
    scores.numeric,
    scores.coverage,
    scores.timeliness,
    scores.clarity
  );

  if (compositeScore < 60 || minScore < 50) {
    return "fail";
  }

  // Conditional if composite below 80 or any dimension below 70
  if (compositeScore < 80 || minScore < 70) {
    return "conditional";
  }

  return "pass";
}

/**
 * Save run results to database
 */
async function saveRunLog(
  request: TaxPulseRequest,
  protocolVersion: string,
  scores: DimensionScores,
  weakestDimension: string,
  weakestReason: string,
  improvementIdeas: string,
  memoSummary: string,
  rawOutputRef: string | null
): Promise<string> {
  const { data, error } = await supabase.rpc("fn_insert_tax_pulse_run", {
    p_entity_id: request.entity_id,
    p_period_start: request.period_start,
    p_period_end: request.period_end,
    p_tax_types: request.tax_types,
    p_protocol_version: protocolVersion,
    p_score_compliance: scores.compliance,
    p_score_numeric: scores.numeric,
    p_score_coverage: scores.coverage,
    p_score_timeliness: scores.timeliness,
    p_score_clarity: scores.clarity,
    p_weakest_dimension: weakestDimension,
    p_weakest_reason: weakestReason,
    p_improvement_ideas: improvementIdeas,
    p_memo_summary: memoSummary,
    p_raw_output_ref: rawOutputRef,
  });

  if (error) {
    throw new Error(`Failed to save run log: ${error.message}`);
  }

  return data;
}

/**
 * Main handler
 */
serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // Parse request
    const requestBody: TaxPulseRequest = await req.json();

    // Validate required fields
    if (!requestBody.entity_id || !requestBody.period_start || !requestBody.period_end) {
      throw new Error("Missing required fields: entity_id, period_start, period_end");
    }

    // Set defaults
    const taxTypes = requestBody.tax_types || ["1601-C", "2550Q", "1702-RT"];
    const protocolVersion = requestBody.protocol_version || "v1";

    console.log(`Starting Tax Pulse review for ${requestBody.entity_id}, period ${requestBody.period_start} to ${requestBody.period_end}`);

    // 1. Load protocol text
    const protocolText = await fetchProtocol(protocolVersion);
    console.log(`Loaded protocol ${protocolVersion}`);

    // 2. Fetch finance data
    const financeData = await fetchFinanceData(
      requestBody.entity_id,
      requestBody.period_start,
      requestBody.period_end,
      taxTypes
    );
    console.log(`Fetched finance data: ${JSON.stringify(financeData).length} bytes`);

    // 3. Fetch authority sources for context
    const authoritySources = await fetchAuthoritySources();
    console.log(`Loaded ${authoritySources.length} authority sources`);

    // 4. Build system prompt
    const systemPrompt = buildSystemPrompt(protocolText, authoritySources);

    // 5. Call LLM for review
    const llmResult = await callLLM(systemPrompt, financeData);
    console.log("LLM review completed");

    // 6. Extract and validate scores
    const scores: DimensionScores = {
      compliance: Number(llmResult.scores?.compliance) || 0,
      numeric: Number(llmResult.scores?.numeric) || 0,
      coverage: Number(llmResult.scores?.coverage) || 0,
      timeliness: Number(llmResult.scores?.timeliness) || 0,
      clarity: Number(llmResult.scores?.clarity) || 0,
    };

    // 7. Calculate composite and status
    const compositeScore = calculateCompositeScore(scores);
    const status = determineStatus(compositeScore, scores);

    // 8. Save to run log
    const runId = await saveRunLog(
      requestBody,
      protocolVersion,
      scores,
      String(llmResult.weakest_dimension || "D1"),
      String(llmResult.weakest_reason || ""),
      String(llmResult.improvement_ideas || ""),
      String(llmResult.memo_summary || ""),
      null // raw_output_ref - could store in blob storage
    );
    console.log(`Saved run log: ${runId}`);

    // 9. Build response
    const result: TaxPulseResult = {
      run_id: runId,
      entity_id: requestBody.entity_id,
      period_start: requestBody.period_start,
      period_end: requestBody.period_end,
      tax_types: taxTypes,
      protocol_version: protocolVersion,
      scores,
      composite_score: Math.round(compositeScore * 100) / 100,
      weakest_dimension: String(llmResult.weakest_dimension || ""),
      weakest_reason: String(llmResult.weakest_reason || ""),
      improvement_ideas: String(llmResult.improvement_ideas || ""),
      memo_summary: String(llmResult.memo_summary || ""),
      status,
    };

    // Include detailed findings if present
    const fullResult = {
      ...result,
      findings: llmResult.findings || [],
      reconciliations: llmResult.reconciliations || [],
      risk_flags: llmResult.risk_flags || [],
    };

    return new Response(JSON.stringify(fullResult), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
      status: 200,
    });

  } catch (error) {
    console.error("Tax Pulse error:", error);

    return new Response(
      JSON.stringify({
        error: error instanceof Error ? error.message : "Unknown error",
        timestamp: new Date().toISOString(),
      }),
      {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 500,
      }
    );
  }
});
