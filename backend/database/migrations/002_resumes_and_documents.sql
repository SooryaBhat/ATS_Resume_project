-- ============================================================================
-- Migration 002: Resumes and Documents
-- Description: Stores raw resume uploads, parsed structured metadata, and
--              configures Supabase Storage bucket policies.
-- ============================================================================

-- Create Resumes Table
CREATE TABLE IF NOT EXISTS public.resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    storage_path TEXT,
    file_type TEXT DEFAULT 'pdf',
    file_size_bytes INT,
    raw_text TEXT,
    parsed_data JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for User Resumes Lookups
CREATE INDEX IF NOT EXISTS idx_resumes_user_id ON public.resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_created_at ON public.resumes(created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.resumes ENABLE ROW LEVEL SECURITY;

-- RLS Policies for Resumes
CREATE POLICY "Users can view their own resumes"
    ON public.resumes FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own resumes"
    ON public.resumes FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own resumes"
    ON public.resumes FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own resumes"
    ON public.resumes FOR DELETE
    USING (auth.uid() = user_id);

-- ── Supabase Storage Setup ──────────────────────────────────────────────────
-- Ensure storage bucket 'resumes' exists
INSERT INTO storage.buckets (id, name, public)
VALUES ('resumes', 'resumes', false)
ON CONFLICT (id) DO NOTHING;

-- Storage Policies for 'resumes' bucket
CREATE POLICY "Authenticated users can upload resume files"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'resumes' AND
        auth.role() = 'authenticated' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Users can read their own resume files"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'resumes' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Users can delete their own resume files"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'resumes' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );
