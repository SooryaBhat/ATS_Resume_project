-- ============================================================================
-- Migration 009: PDF Reports
-- Description: Tracks persisted PDF reports stored in the pdf_reports
--              Supabase Storage bucket. Allows listing and re-downloading
--              previously generated reports without re-generation.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.reports (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    analysis_id  UUID        REFERENCES public.analyses(id) ON DELETE SET NULL,
    filename     TEXT        NOT NULL,
    storage_path TEXT        NOT NULL,   -- e.g. "{user_id}/{report_id}.pdf"
    file_size_bytes INT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Index for listing a user's reports newest-first
CREATE INDEX IF NOT EXISTS idx_reports_user_id    ON public.reports(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON public.reports(user_id, created_at DESC);

-- Enable Row Level Security
ALTER TABLE public.reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own reports"
    ON public.reports FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can insert reports"
    ON public.reports FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Users can delete their own reports"
    ON public.reports FOR DELETE
    USING (auth.uid() = user_id);
