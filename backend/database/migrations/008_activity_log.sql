-- ============================================================================
-- Migration 008: Activity Log
-- Description: Chronological activity feed per user — analysis runs,
--              JD matches, PDF exports, etc. Powers the dashboard feed.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.activity_log (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    action      TEXT        NOT NULL,        -- e.g. "analyzed_resume", "matched_jd"
    description TEXT,
    icon        TEXT        DEFAULT 'fa-circle-check',
    metadata    JSONB       DEFAULT '{}'::jsonb,   -- extra data (filename, score, etc.)
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Index for latest-first queries per user
CREATE INDEX IF NOT EXISTS idx_activity_log_user_id   ON public.activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON public.activity_log(user_id, created_at DESC);

-- Enable Row Level Security
ALTER TABLE public.activity_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own activity"
    ON public.activity_log FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can insert activity"
    ON public.activity_log FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Users can delete their own activity"
    ON public.activity_log FOR DELETE
    USING (auth.uid() = user_id);
