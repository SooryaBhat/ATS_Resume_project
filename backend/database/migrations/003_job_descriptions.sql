-- ============================================================================
-- Migration 003: Job Descriptions
-- Description: Stores target job descriptions and extracted requirements for
--              multi-JD matching and resume tailoring features.
-- ============================================================================

-- Create Job Descriptions Table
CREATE TABLE IF NOT EXISTS public.job_descriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    jd_text TEXT NOT NULL,
    parsed_jd JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for User Job Descriptions
CREATE INDEX IF NOT EXISTS idx_jd_user_id ON public.job_descriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_jd_company ON public.job_descriptions(company_name);

-- Enable Row Level Security (RLS)
ALTER TABLE public.job_descriptions ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view their own saved JDs"
    ON public.job_descriptions FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own JDs"
    ON public.job_descriptions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own JDs"
    ON public.job_descriptions FOR DELETE
    USING (auth.uid() = user_id);
