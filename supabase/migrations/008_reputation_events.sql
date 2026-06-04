CREATE TABLE reputation_events (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  type        TEXT NOT NULL CHECK (type IN ('upload_approved', 'upvote_received', 'downvote_received')),
  delta       INTEGER NOT NULL,
  document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reputation_user ON reputation_events(user_id, created_at DESC);
