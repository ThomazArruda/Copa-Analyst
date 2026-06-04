import { supabase } from '@/services/supabase';
import type { Document, DocumentFilter, DocumentType } from '@/types/app.types';

const DOCUMENTS_SELECT = `
  *,
  subject:subjects(*, course:courses(*, institution:institutions(*))),
  uploader:profiles(id, username, avatar_url, reputation)
`;

export const getDocumentsByFilter = async (
  filter: DocumentFilter,
  limit = 20,
  offset = 0
): Promise<Document[]> => {
  let query = supabase
    .from('documents')
    .select(DOCUMENTS_SELECT)
    .eq('status', 'active')
    .order('created_at', { ascending: false })
    .range(offset, offset + limit - 1);

  if (filter.subjectId) query = query.eq('subject_id', filter.subjectId);
  if (filter.type) query = query.eq('type', filter.type);
  if (filter.semester) query = query.eq('semester', filter.semester);
  if (filter.query) {
    query = query.or(`title.ilike.%${filter.query}%,professor.ilike.%${filter.query}%`);
  }

  const { data, error } = await query;
  if (error) throw error;
  return (data as Document[]) ?? [];
};

export const getDocumentById = async (id: string): Promise<Document | null> => {
  const { data, error } = await supabase
    .from('documents')
    .select(DOCUMENTS_SELECT)
    .eq('id', id)
    .single();
  if (error) throw error;
  return data as Document | null;
};

export const createDocument = async (doc: {
  uploader_id: string;
  subject_id: string;
  title: string;
  type: DocumentType;
  professor?: string;
  semester: string;
  file_path: string;
  file_size: number;
  mime_type: string;
}): Promise<Document> => {
  const { data, error } = await supabase
    .from('documents')
    .insert(doc)
    .select(DOCUMENTS_SELECT)
    .single();
  if (error) throw error;
  return data as Document;
};

export const getRecentDocuments = async (
  institutionId?: string,
  limit = 10
): Promise<Document[]> => {
  let query = supabase
    .from('documents')
    .select(DOCUMENTS_SELECT)
    .eq('status', 'active')
    .order('created_at', { ascending: false })
    .limit(limit);

  if (institutionId) {
    query = query.eq('subject.course.institution_id', institutionId);
  }

  const { data, error } = await query;
  if (error) throw error;
  return (data as Document[]) ?? [];
};

export const getPopularDocuments = async (limit = 10): Promise<Document[]> => {
  const { data, error } = await supabase
    .from('documents')
    .select(DOCUMENTS_SELECT)
    .eq('status', 'active')
    .order('score', { ascending: false })
    .order('download_count', { ascending: false })
    .limit(limit);
  if (error) throw error;
  return (data as Document[]) ?? [];
};

export const incrementViewCount = async (id: string): Promise<void> => {
  const { error } = await supabase.rpc('increment_view_count' as any, { doc_id: id } as any);
  if (error) throw error;
};

export const incrementDownloadCount = async (id: string): Promise<void> => {
  const { error } = await supabase.rpc('increment_download_count' as any, { doc_id: id } as any);
  if (error) throw error;
};

export const getUploadCountToday = async (userId: string): Promise<number> => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const { count, error } = await supabase
    .from('documents')
    .select('id', { count: 'exact', head: true })
    .eq('uploader_id', userId)
    .gte('created_at', today.toISOString());
  if (error) throw error;
  return count ?? 0;
};

export const getDownloadCountThisMonth = async (userId: string): Promise<number> => {
  const firstOfMonth = new Date();
  firstOfMonth.setDate(1);
  firstOfMonth.setHours(0, 0, 0, 0);

  const { count, error } = await supabase
    .from('downloads')
    .select('id', { count: 'exact', head: true })
    .eq('user_id', userId)
    .gte('created_at', firstOfMonth.toISOString());
  if (error) throw error;
  return count ?? 0;
};

export const voteDocument = async (
  documentId: string,
  value: 1 | -1,
  reason?: string
): Promise<void> => {
  const { error } = await supabase.from('votes').upsert(
    { document_id: documentId, value, reason: reason ?? null },
    { onConflict: 'user_id,document_id' }
  );
  if (error) throw error;
};

export const getUserVote = async (
  documentId: string,
  userId: string
): Promise<1 | -1 | null> => {
  const { data, error } = await supabase
    .from('votes')
    .select('value')
    .eq('document_id', documentId)
    .eq('user_id', userId)
    .maybeSingle();
  if (error) throw error;
  return (data?.value as 1 | -1) ?? null;
};
