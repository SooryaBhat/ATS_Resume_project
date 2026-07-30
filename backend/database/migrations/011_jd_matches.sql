-- ============================================================================
-- Migration 011: JD Matches
-- Description: Stores results of matching a specific analysis (resume) against
--              a specific saved job description. Also adds tracking columns
--              to job_descriptions for the most recent match score/date.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.jd_matches (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    jd_id        UUID        NOT NULL REFERENCES public.job_descriptions(id) ON DELETE CASCADE,
    analysis_id  UUID        REFERENCES public.analyses(id) ON DELETE SET NULL,
    match_result JSONB       DEFAULT '{}'::jsonb,  -- full JDComparison output
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_jd_matches_user_id ON public.jd_matches(user_id);
CREATE INDEX IF NOT EXISTS idx_jd_matches_jd_id   ON public.jd_matches(jd_id);

-- Enable Row Level Security
ALTER TABLE public.jd_matches ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own JD matches"
    ON public.jd_matches FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can insert JD matches"
    ON public.jd_matches FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Users can delete their own JD matches"
    ON public.jd_matches FOR DELETE
    USING (auth.uid() = user_id);

-- ── Add tracking columns to job_descriptions ─────────────────────────────────
ALTER TABLE public.job_descriptions
    ADD COLUMN IF NOT EXISTS last_match_score  NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS last_matched_at   TIMESTAMPTZ;

-- ── Add label column to analyses for user renames ────────────────────────────
ALTER TABLE public.analyses
    ADD COLUMN IF NOT EXISTS label TEXT;

-- ── Add context FK to chat_sessions ──────────────────────────────────────────
ALTER TABLE public.chat_sessions
    ADD COLUMN IF NOT EXISTS analysis_id UUID REFERENCES public.analyses(id) ON DELETE SET NULL;

-- ── Add skill_gap_roadmaps progress columns ───────────────────────────────────
ALTER TABLE public.skill_gap_roadmaps
    ADD COLUMN IF NOT EXISTS progress_percent INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
