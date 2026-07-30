-- ============================================================================
-- Migration 005: Skill Gap Roadmaps
-- Description: Stores personalized skill learning roadmaps and priority checklists.
-- ============================================================================

-- Create Skill Gap Roadmaps Table
CREATE TABLE IF NOT EXISTS public.skill_gap_roadmaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    analysis_id UUID REFERENCES public.analyses(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    category TEXT DEFAULT 'General',
    priority TEXT DEFAULT 'Medium',
    estimated_hours TEXT DEFAULT '10 Hours',
    status TEXT DEFAULT 'Not Started',
    roadmap_steps JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for User Skill Roadmaps
CREATE INDEX IF NOT EXISTS idx_skill_roadmaps_user_id ON public.skill_gap_roadmaps(user_id);

-- Enable Row Level Security (RLS)
ALTER TABLE public.skill_gap_roadmaps ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view their own skill roadmaps"
    ON public.skill_gap_roadmaps FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own skill roadmaps"
    ON public.skill_gap_roadmaps FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own skill roadmaps"
    ON public.skill_gap_roadmaps FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own skill roadmaps"
    ON public.skill_gap_roadmaps FOR DELETE
    USING (auth.uid() = user_id);
