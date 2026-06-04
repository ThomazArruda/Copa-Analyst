# TODO — ProvaPool MVP

Rastreamento de tarefas para a v1.0.
Status: `[ ]` pendente · `[x]` concluído · `[~]` em progresso · `[!]` bloqueado/tem problema

> **Última atualização:** 2026-02-27

---

## Fase 0 — Setup do Projeto ✅ CONCLUÍDA

- [x] Inicializar projeto Expo com TypeScript
- [x] Configurar Expo Router (file-based routing)
- [x] Configurar NativeWind + Tailwind
- [x] Configurar alias `@/` no `tsconfig.json` e `babel.config.js`
- [x] Instalar todas as dependências (Supabase, React Query, Zustand, etc.)
- [x] Configurar Jest + jest-expo + Testing Library
- [x] Configurar variáveis de ambiente (`.env.example`)
- [x] Setup inicial do repositório Git + `.gitignore`
- [ ] Configurar ESLint + Prettier ← ainda pendente
- [ ] Criar projeto no Supabase (dev) ← **AÇÃO MANUAL NECESSÁRIA**

---

## Fase 1 — Banco de Dados (Supabase) 🔶 PARCIAL

- [x] Migration: `001_institutions.sql`
- [x] Migration: `002_courses.sql`
- [x] Migration: `003_subjects.sql`
- [x] Migration: `004_profiles.sql`
- [x] Migration: `005_documents.sql`
- [x] Migration: `006_votes.sql`
- [x] Migration: `007_downloads.sql`
- [x] Migration: `008_reputation_events.sql`
- [x] Migration: `009_rls_policies.sql` (políticas RLS)
- [x] Migration: `010_seed_institutions.sql` (~20 universidades brasileiras)
- [ ] **Aplicar migrations no Supabase** ← **AÇÃO MANUAL NECESSÁRIA** (precisa do projeto criado)
- [ ] Configurar buckets no Storage (`documents/` privado, `avatars/` público)
- [!] Gerar `database.types.ts` via Supabase CLI ← **BLOQUEADO** (placeholder atual causa erros TS)

---

## Fase 2 — Infraestrutura do App ✅ CONCLUÍDA

- [x] Cliente Supabase (`src/services/supabase.ts`) com SecureStore adapter
- [x] Tipos da aplicação (`src/types/app.types.ts`)
- [x] `validators.ts` — `isValidFileSize`, `isValidMimeType`, `isValidSemester`
- [x] `formatters.ts` — `formatFileSize`, `formatSemester`, `formatReputation`
- [x] Store Zustand: `authStore.ts`
- [x] Store Zustand: `filterStore.ts`
- [x] `app/_layout.tsx` com QueryClient + auth guard

---

## Fase 3 — Autenticação ✅ ESTRUTURA CRIADA (requer Supabase)

- [x] `auth.service.ts` (signUp, signIn, signOut, resetPassword, OAuth Google)
- [x] Hook `useAuth.ts`
- [x] Tela `(auth)/login.tsx`
- [x] Tela `(auth)/register.tsx`
- [!] Tela `(auth)/onboarding.tsx` ← tem erros TypeScript (FlatList + insert de profile)
- [x] Tela `(auth)/forgot-password.tsx`
- [x] Proteção de rotas (redirect não autenticado → login)
- [ ] Testes unitários: `auth.service.test.ts`
- [ ] Validar fluxo OAuth Google no Expo Go

---

## Fase 4 — Upload de Documentos ✅ ESTRUTURA CRIADA (requer Supabase)

- [x] `storage.service.ts` (upload, getSignedUrl, deleteFile)
- [!] `documents.service.ts` ← erros TypeScript em `insert` (causados por `database.types.ts` placeholder)
- [x] Hook `useUpload.ts`
- [x] Tela `(tabs)/upload.tsx`
- [ ] Componente `UploadForm.tsx` standalone
- [ ] Pré-visualização de arquivo antes do upload
- [ ] Edge Function: `on-document-upload`
- [x] Testes unitários: `documents.service.test.ts`
- [ ] Testes de integração: `upload.flow.test.ts`

---

## Fase 5 — Busca e Navegação ✅ ESTRUTURA CRIADA (requer Supabase)

- [x] `searchDocuments`, `getRecentDocuments`, `getPopularDocuments` no service
- [x] Hook `useDocuments.ts` (search, recent, popular com React Query)
- [x] Tela `(tabs)/search.tsx`
- [x] Tela `(tabs)/index.tsx` (Home com feed)
- [ ] Componente `FilterBar.tsx` standalone
- [ ] Componente `DocumentCard.tsx` standalone
- [ ] Testes: `useDocuments.test.ts`, `search.flow.test.ts`

---

## Fase 6 — Visualização de Documentos ✅ ESTRUTURA CRIADA

- [x] Tela `document/[id].tsx`
- [ ] Componente `DocumentViewer.tsx` (PDF + imagem com zoom)
- [ ] Botão Download com verificação de limite mensal
- [ ] Tratamento de erros (404, oculto, Signed URL falhou)

---

## Fase 7 — Sistema de Reputação ✅ CONCLUÍDA

- [x] Hook `useReputation.ts`
- [x] Testes unitários: `useReputation.test.ts` (31 testes passando ✅)
- [ ] Componente `ReputationBadge.tsx`
- [ ] Edge Function: `on-vote`

---

## Fase 8 — Avaliação de Documentos (Votes) 🔶 PARCIAL

- [x] `voteDocument`, `removeVote`, `getUserVote` no `documents.service.ts`
- [ ] UI de upvote/downvote na tela `document/[id].tsx`
- [ ] Modal de motivo para downvote
- [ ] Testes

---

## Fase 9 — Perfil do Usuário 🔶 PARCIAL

- [x] Tela `(tabs)/profile.tsx` (estrutura base)
- [ ] Edição de perfil (nome, avatar)
- [ ] Histórico de uploads paginado
- [ ] Histórico de downloads paginado
- [ ] Upload de avatar para `avatars/`

---

## Fase 10 — Testes e Qualidade 🔶 PARCIAL

- [x] 31 testes unitários passando (`validators`, `documents.service`, `useReputation`)
- [ ] Cobertura ≥ 80% (ainda não medida formalmente)
- [ ] `npx tsc --noEmit` sem erros ← **tem erros** (ver seção de problemas)
- [ ] Testes E2E com Maestro
- [ ] Revisar segurança

---

## Problemas Conhecidos 🔴

| # | Arquivo | Problema | Causa |
|---|---------|----------|-------|
| 1 | `src/types/database.types.ts` | Placeholder — tabelas tipadas como `never` | Projeto Supabase ainda não criado |
| 2 | `src/services/documents.service.ts` | Erros de TS em `insert()` | Causado pelo problema #1 |
| 3 | `app/(auth)/onboarding.tsx` | Erros TS em FlatList + insert de profile | Causado pelo problema #1 + tipagem local |
| 4 | `src/components/EditScreenInfo.tsx` | Módulos `ExternalLink` e `Themed` não encontrados | Arquivos de template Expo não migrados — não afeta o app |

---

## Backlog (v2.0+)

- [ ] OCR para busca por conteúdo interno
- [ ] IA para geração de resumos e questões similares
- [ ] Modo Estudo (quiz)
- [ ] Notificações push
- [ ] Favoritos e coleções
- [ ] Moderação comunitária
- [ ] Plano institucional
