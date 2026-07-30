-- ============================================================================
-- Migration 010: Resume Comparisons
-- Description: Stores multi-resume comparison sessions and their result data.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.comparisons (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name              TEXT        DEFAULT 'Resume Comparison',
    analysis_ids      UUID[]      DEFAULT '{}',     -- FKs to analyses table
    comparison_result JSONB       DEFAULT '{}'::jsonb,
    winner_filename   TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Index for listing user comparisons
CREATE INDEX IF NOT EXISTS idx_comparisons_user_id    ON public.comparisons(user_id);
CREATE INDEX IF NOT EXISTS idx_comparisons_created_at ON public.comparisons(user_id, created_at DESC);

-- Enable Row Level Security
ALTER TABLE public.comparisons ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own comparisons"
    ON public.comparisons FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can insert comparisons"
    ON public.comparisons FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Users can delete their own comparisons"
    ON public.comparisons FOR DELETE
    USING (auth.uid() = user_id);
