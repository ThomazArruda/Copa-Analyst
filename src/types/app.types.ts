export type DocumentType = 'prova' | 'lista' | 'resumo' | 'gabarito';
export type DocumentStatus = 'active' | 'pending' | 'hidden' | 'removed';
export type UserPlan = 'free' | 'pro';

export interface Institution {
  id: string;
  name: string;
  acronym: string | null;
  city: string | null;
  state: string | null;
  verified: boolean;
  created_at: string;
}

export interface Course {
  id: string;
  institution_id: string;
  name: string;
  area: string | null;
  created_at: string;
}

export interface Subject {
  id: string;
  course_id: string;
  name: string;
  code: string | null;
  created_at: string;
}

export interface Profile {
  id: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  institution_id: string | null;
  course_id: string | null;
  semester: number | null;
  reputation: number;
  plan: UserPlan;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  uploader_id: string;
  subject_id: string;
  title: string;
  type: DocumentType;
  professor: string | null;
  semester: string | null;
  file_path: string;
  file_size: number | null;
  mime_type: string | null;
  page_count: number | null;
  view_count: number;
  download_count: number;
  score: number;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
  // Joined fields
  subject?: Subject;
  uploader?: Pick<Profile, 'id' | 'username' | 'avatar_url' | 'reputation'>;
}

export interface Vote {
  id: string;
  user_id: string;
  document_id: string;
  value: 1 | -1;
  reason: string | null;
  created_at: string;
}

export interface Download {
  id: string;
  user_id: string;
  document_id: string;
  created_at: string;
}

export interface ReputationEvent {
  id: string;
  user_id: string;
  type: 'upload_approved' | 'upvote_received' | 'downvote_received';
  delta: number;
  document_id: string | null;
  created_at: string;
}

export interface DocumentFilter {
  institutionId?: string;
  courseId?: string;
  subjectId?: string;
  type?: DocumentType;
  semester?: string;
  query?: string;
}

export interface UploadFormData {
  file: {
    uri: string;
    name: string;
    size: number;
    mimeType: string;
  };
  title: string;
  subjectId: string;
  type: DocumentType;
  professor?: string;
  semester: string;
}
