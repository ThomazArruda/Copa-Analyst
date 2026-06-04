import type { Document, Profile } from '@/types/app.types';

export const DEMO_MODE = process.env.EXPO_PUBLIC_DEMO_MODE === 'true';

// ---------------------------------------------------------------------------
// Mock user (shape mínima necessária pelo authStore)
// ---------------------------------------------------------------------------
export const mockUser = {
  id: 'demo-user-id',
  email: 'demo@provapool.app',
  created_at: new Date().toISOString(),
  app_metadata: {},
  user_metadata: {},
  aud: 'authenticated',
  role: 'authenticated',
};

// ---------------------------------------------------------------------------
// Mock profile
// ---------------------------------------------------------------------------
export const mockProfile: Profile = {
  id: 'demo-user-id',
  username: 'estudante_demo',
  full_name: 'Rafael Fernandez',
  avatar_url: null,
  institution_id: 'inst-usp',
  course_id: 'course-cc',
  semester: 5,
  reputation: 120,
  plan: 'free',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

// ---------------------------------------------------------------------------
// Mock documents
// ---------------------------------------------------------------------------
export const mockDocuments: Document[] = [
  {
    id: 'doc-1',
    uploader_id: 'other-user',
    subject_id: 'subj-calc',
    title: 'Prova 1 – Cálculo I (2024.1)',
    type: 'prova',
    professor: 'Prof. João Silva',
    semester: '2024.1',
    file_path: 'demo/1.pdf',
    file_size: 1024000,
    mime_type: 'application/pdf',
    page_count: 4,
    view_count: 142,
    download_count: 38,
    score: 15,
    status: 'active',
    created_at: '2024-03-15T10:00:00Z',
    updated_at: '2024-03-15T10:00:00Z',
    subject: { id: 'subj-calc', name: 'Cálculo I', course_id: 'course-cc', code: null, created_at: '' },
    uploader: { id: 'other-user', username: 'joao_usp', avatar_url: null, reputation: 80 },
  },
  {
    id: 'doc-2',
    uploader_id: 'other-user',
    subject_id: 'subj-algo',
    title: 'Lista 3 – Algoritmos e Estruturas de Dados',
    type: 'lista',
    professor: 'Profa. Ana Costa',
    semester: '2024.1',
    file_path: 'demo/2.pdf',
    file_size: 512000,
    mime_type: 'application/pdf',
    page_count: 2,
    view_count: 89,
    download_count: 21,
    score: 8,
    status: 'active',
    created_at: '2024-03-10T14:00:00Z',
    updated_at: '2024-03-10T14:00:00Z',
    subject: { id: 'subj-algo', name: 'Algoritmos e ED', course_id: 'course-cc', code: null, created_at: '' },
    uploader: { id: 'other-user', username: 'ana_unicamp', avatar_url: null, reputation: 55 },
  },
  {
    id: 'doc-3',
    uploader_id: 'other-user',
    subject_id: 'subj-fis',
    title: 'Resumo completo – Física II',
    type: 'resumo',
    professor: 'Prof. Carlos Lima',
    semester: '2023.2',
    file_path: 'demo/3.pdf',
    file_size: 2048000,
    mime_type: 'application/pdf',
    page_count: 12,
    view_count: 310,
    download_count: 95,
    score: 23,
    status: 'active',
    created_at: '2024-01-20T09:00:00Z',
    updated_at: '2024-01-20T09:00:00Z',
    subject: { id: 'subj-fis', name: 'Física II', course_id: 'course-eng', code: null, created_at: '' },
    uploader: { id: 'other-user', username: 'carlos_ufrj', avatar_url: null, reputation: 210 },
  },
  {
    id: 'doc-4',
    uploader_id: 'other-user',
    subject_id: 'subj-bd',
    title: 'Gabarito P2 – Banco de Dados',
    type: 'gabarito',
    professor: 'Profa. Mariana Souza',
    semester: '2024.1',
    file_path: 'demo/4.pdf',
    file_size: 256000,
    mime_type: 'application/pdf',
    page_count: 3,
    view_count: 178,
    download_count: 67,
    score: 12,
    status: 'active',
    created_at: '2024-02-28T16:00:00Z',
    updated_at: '2024-02-28T16:00:00Z',
    subject: { id: 'subj-bd', name: 'Banco de Dados', course_id: 'course-cc', code: null, created_at: '' },
    uploader: { id: 'other-user', username: 'mari_puc', avatar_url: null, reputation: 95 },
  },
  {
    id: 'doc-5',
    uploader_id: 'demo-user-id',
    subject_id: 'subj-calc',
    title: 'Prova Final – Cálculo I (2023.2)',
    type: 'prova',
    professor: 'Prof. João Silva',
    semester: '2023.2',
    file_path: 'demo/5.pdf',
    file_size: 1536000,
    mime_type: 'application/pdf',
    page_count: 5,
    view_count: 520,
    download_count: 183,
    score: 31,
    status: 'active',
    created_at: '2024-01-05T11:00:00Z',
    updated_at: '2024-01-05T11:00:00Z',
    subject: { id: 'subj-calc', name: 'Cálculo I', course_id: 'course-cc', code: null, created_at: '' },
    uploader: { id: 'demo-user-id', username: 'estudante_demo', avatar_url: null, reputation: 120 },
  },
];

// Documentos do usuário demo (apenas os que ele "enviou")
export const mockMyUploads = mockDocuments.filter(
  (d) => d.uploader_id === 'demo-user-id'
);
