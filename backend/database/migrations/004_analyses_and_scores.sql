-- ============================================================================
-- Migration 004: Analyses and Scores
-- Description: Stores full ATS analysis reports, component score breakdowns,
--              matched/missing keywords, recommendations, and PDF report buckets.
-- ============================================================================

-- Create Analyses Table
CREATE TABLE IF NOT EXISTS public.analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    resume_id UUID REFERENCES public.resumes(id) ON DELETE SET NULL,
    filename TEXT NOT NULL,
    job_title TEXT DEFAULT '',
    ats_score NUMERIC(5,2) NOT NULL DEFAULT 0.0,
    keyword_match NUMERIC(5,2) DEFAULT 0.0,
    component_scores JSONB DEFAULT '{}'::jsonb,
    matched_keywords TEXT[] DEFAULT '{}',
    missing_keywords TEXT[] DEFAULT '{}',
    issues_summary TEXT[] DEFAULT '{}',
    detailed_feedback JSONB DEFAULT '[]'::jsonb,
    jd_match_analysis JSONB DEFAULT '{}'::jsonb,
    skill_validation_details JSONB DEFAULT '{}'::jsonb,
    recommendations JSONB DEFAULT '[]'::jsonb,
    strengths TEXT[] DEFAULT '{}',
    interpretation TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexing for High Performance Queries
CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON public.analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON public.analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_ats_score ON public.analyses(ats_score DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;

-- RLS Policies for Analyses Table
CREATE POLICY "Users can view their own analyses"
    ON public.analyses FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own analyses"
    ON public.analyses FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own analyses"
    ON public.analyses FOR DELETE
    USING (auth.uid() = user_id);

-- ── Supabase Storage Setup for PDF Reports ───────────────────────────────────
INSERT INTO storage.buckets (id, name, public)
VALUES ('pdf_reports', 'pdf_reports', false)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Authenticated users can upload PDF reports"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'pdf_reports' AND
        auth.role() = 'authenticated' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Users can read their own PDF reports"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'pdf_reports' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );
