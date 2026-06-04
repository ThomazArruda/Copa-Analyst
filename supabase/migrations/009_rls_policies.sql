-- =========================================================
-- PROFILES
-- =========================================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Profiles are viewable by everyone"
  ON profiles FOR SELECT USING (true);

CREATE POLICY "Users can insert their own profile"
  ON profiles FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
  ON profiles FOR UPDATE USING (auth.uid() = id);

-- =========================================================
-- INSTITUTIONS (read-only for all authenticated users)
-- =========================================================
ALTER TABLE institutions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Institutions are viewable by authenticated users"
  ON institutions FOR SELECT USING (auth.role() = 'authenticated');

-- =========================================================
-- COURSES
-- =========================================================
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Courses are viewable by authenticated users"
  ON courses FOR SELECT USING (auth.role() = 'authenticated');

-- =========================================================
-- SUBJECTS
-- =========================================================
ALTER TABLE subjects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Subjects are viewable by authenticated users"
  ON subjects FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can create subjects"
  ON subjects FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- =========================================================
-- DOCUMENTS
-- =========================================================
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Active documents are viewable by authenticated users"
  ON documents FOR SELECT
  USING (auth.role() = 'authenticated' AND status = 'active');

CREATE POLICY "Users can insert their own documents"
  ON documents FOR INSERT
  WITH CHECK (auth.uid() = uploader_id);

CREATE POLICY "Users can update their own documents"
  ON documents FOR UPDATE
  USING (auth.uid() = uploader_id);

-- =========================================================
-- VOTES
-- =========================================================
ALTER TABLE votes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can see their own votes"
  ON votes FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create votes"
  ON votes FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own votes"
  ON votes FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own votes"
  ON votes FOR DELETE USING (auth.uid() = user_id);

-- =========================================================
-- DOWNLOADS
-- =========================================================
ALTER TABLE downloads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can see their own downloads"
  ON downloads FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create download records"
  ON downloads FOR INSERT WITH CHECK (auth.uid() = user_id);

-- =========================================================
-- REPUTATION EVENTS
-- =========================================================
ALTER TABLE reputation_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can see their own reputation events"
  ON reputation_events FOR SELECT USING (auth.uid() = user_id);
