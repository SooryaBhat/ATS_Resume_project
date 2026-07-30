-- ============================================================================
-- Migration 007: Notifications
-- Description: Stores per-user notification alerts (analysis complete, skill
--              gap detected, report ready, etc.)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.notifications (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title       TEXT        NOT NULL,
    description TEXT,
    icon        TEXT        DEFAULT 'fa-bell',
    type        TEXT        DEFAULT 'info',    -- info | success | warning | error
    is_read     BOOLEAN     DEFAULT false,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast unread-count queries
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON public.notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read  ON public.notifications(user_id, is_read);

-- Enable Row Level Security
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own notifications"
    ON public.notifications FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update (mark read) their own notifications"
    ON public.notifications FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own notifications"
    ON public.notifications FOR DELETE
    USING (auth.uid() = user_id);

-- Service-role INSERT allowed (backend inserts on behalf of user)
CREATE POLICY "Service role can insert notifications"
    ON public.notifications FOR INSERT
    WITH CHECK (true);
