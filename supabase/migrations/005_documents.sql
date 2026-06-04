CREATE TABLE documents (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  uploader_id    UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  subject_id     UUID NOT NULL REFERENCES subjects(id),
  title          TEXT NOT NULL,
  type           TEXT NOT NULL CHECK (type IN ('prova', 'lista', 'resumo', 'gabarito')),
  professor      TEXT,
  semester       TEXT,
  file_path      TEXT NOT NULL,
  file_size      INTEGER,
  mime_type      TEXT,
  page_count     INTEGER,
  view_count     INTEGER DEFAULT 0,
  download_count INTEGER DEFAULT 0,
  score          INTEGER DEFAULT 0,
  status         TEXT DEFAULT 'active' CHECK (status IN ('active', 'pending', 'hidden', 'removed')),
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_subject ON documents(subject_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_type ON documents(type);
CREATE INDEX idx_documents_uploader ON documents(uploader_id);
CREATE INDEX idx_documents_created ON documents(created_at DESC);
CREATE INDEX idx_documents_score ON documents(score DESC);

CREATE TRIGGER documents_updated_at
  BEFORE UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- RPC to increment view count atomically
CREATE OR REPLACE FUNCTION increment_view_count(doc_id UUID)
RETURNS VOID AS $$
BEGIN
  UPDATE documents SET view_count = view_count + 1 WHERE id = doc_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RPC to increment download count atomically
CREATE OR REPLACE FUNCTION increment_download_count(doc_id UUID)
RETURNS VOID AS $$
BEGIN
  UPDATE documents SET download_count = download_count + 1 WHERE id = doc_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
