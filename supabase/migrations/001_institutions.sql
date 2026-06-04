CREATE TABLE institutions (
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name      TEXT NOT NULL,
  acronym   TEXT,
  city      TEXT,
  state     CHAR(2),
  verified  BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_institutions_name ON institutions(name);
