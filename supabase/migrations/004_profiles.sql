CREATE TABLE profiles (
  id             UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username       TEXT UNIQUE NOT NULL,
  full_name      TEXT,
  avatar_url     TEXT,
  institution_id UUID REFERENCES institutions(id),
  course_id      UUID REFERENCES courses(id),
  semester       INTEGER CHECK (semester BETWEEN 1 AND 12),
  reputation     INTEGER DEFAULT 0,
  plan           TEXT DEFAULT 'free' CHECK (plan IN ('free', 'pro')),
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-update updated_at on change
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
