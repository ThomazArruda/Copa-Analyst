# Plano de Implementação — ProvaPool MVP

> **Última atualização:** 2026-02-27
> **Status geral:** Fases 0–2 concluídas. Estrutura das Fases 3–9 criada. Bloqueio principal: projeto Supabase não configurado.

---

## Status por Fase

| Fase | Nome | Status | Nota |
|------|------|--------|------|
| 0 | Setup do Projeto | ✅ Concluída | ESLint/Prettier ainda pendente |
| 1 | Banco de Dados | 🔶 Parcial | Migrations criadas, não aplicadas |
| 2 | Infraestrutura do App | ✅ Concluída | Serviços, stores, utils, types |
| 3 | Autenticação | 🔶 Estrutura criada | Requer Supabase conectado |
| 4 | Upload de Documentos | 🔶 Estrutura criada | Requer Supabase conectado |
| 5 | Busca e Navegação | 🔶 Estrutura criada | Requer Supabase conectado |
| 6 | Visualização | 🔶 Estrutura criada | DocumentViewer ainda não implementado |
| 7 | Reputação | ✅ Concluída | 31 testes passando |
| 8 | Votes | 🔶 Parcial | Service criado, UI pendente |
| 9 | Perfil | 🔶 Parcial | Tela criada, features pendentes |
| 10 | Testes e Qualidade | 🔶 Parcial | 31 testes OK, TS tem erros |
| 11 | Validação Final | ⏳ Pendente | — |

---

## Visão Geral das Fases

```
Fase 0 → Setup
Fase 1 → Banco de Dados
Fase 2 → Infraestrutura do App
Fase 3 → Autenticação
Fase 4 → Upload de Documentos
Fase 5 → Busca e Navegação
Fase 6 → Visualização de Documentos
Fase 7 → Sistema de Reputação
Fase 8 → Avaliação (Votes)
Fase 9 → Perfil do Usuário
Fase 10 → Testes e Qualidade
Fase 11 → Validação dos Critérios de Aceite
```

Cada fase depende da anterior. Não avançar para a próxima fase sem os critérios de saída da atual serem cumpridos.

---

## 🚧 PRÓXIMOS PASSOS IMEDIATOS

### Passo 1 — Conectar ao Supabase (AÇÃO MANUAL DO USUÁRIO)

1. Criar um projeto em [supabase.com](https://supabase.com)
2. Copiar `EXPO_PUBLIC_SUPABASE_URL` e `EXPO_PUBLIC_SUPABASE_ANON_KEY`
3. Criar arquivo `.env` na raiz:
   ```
   EXPO_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
   EXPO_PUBLIC_SUPABASE_ANON_KEY=eyJxxx...
   ```
4. Aplicar migrations:
   ```bash
   supabase link --project-ref <seu-project-id>
   supabase db push
   ```
5. Gerar tipos TypeScript:
   ```bash
   supabase gen types typescript --project-id <seu-project-id> > src/types/database.types.ts
   ```

### Passo 2 — Corrigir erros TypeScript

Após gerar `database.types.ts` real, os erros em `documents.service.ts` e `onboarding.tsx` serão resolvidos ou expostos claramente.

Restará corrigir o `onboarding.tsx` (tipagem do FlatList com `Institution | Course`).

### Passo 3 — Implementar componentes visuais faltantes

- `src/components/ui/` — Button, Input, Card atômicos
- `src/components/DocumentCard.tsx`
- `src/components/FilterBar.tsx`
- `src/components/DocumentViewer.tsx` (PDF + zoom)
- `src/components/ReputationBadge.tsx`
- `src/components/UploadForm.tsx`

### Passo 4 — Edge Functions

- `on-document-upload` — valida MIME, conta páginas, +10 pts
- `on-vote` — recalcula score, oculta se score < -5

### Passo 5 — Testes e cobertura

- Completar testes unitários para `auth.service`, `useDocuments`, `useUpload`
- Rodar `npx jest --coverage` e atingir thresholds
- Testes E2E com Maestro (auth + download)

---

## Fase 0 — Setup do Projeto ✅

**Objetivo:** ter o projeto rodando no Expo Go com a estrutura de pastas correta.

**Critério de saída:** ✅ `npx expo start` abre o app. `npx jest` roda sem falhar (31 testes passando).

---

## Fase 1 — Banco de Dados (Supabase) 🔶

**Objetivo:** schema completo no Supabase com RLS e Storage configurados.

### Migrations criadas (em `supabase/migrations/`)

```
001_institutions.sql
002_courses.sql
003_subjects.sql
004_profiles.sql
005_documents.sql
006_votes.sql
007_downloads.sql
008_reputation_events.sql
009_rls_policies.sql
010_seed_institutions.sql  ← ~20 universidades brasileiras
```

**Pendente:**
- Aplicar as migrations no Supabase (`supabase db push`)
- Configurar buckets: `documents/` (privado, 20 MB) e `avatars/` (público, 2 MB)
- Gerar `database.types.ts` real via CLI

**Critério de saída:** todas as tabelas criadas, RLS ativa, `database.types.ts` gerado sem erros.

---

## Fase 2 — Infraestrutura do App ✅

**Objetivo:** serviços base, stores e utilitários disponíveis.

**O que foi criado:**
- `src/services/supabase.ts` — cliente com ExpoSecureStoreAdapter
- `src/types/app.types.ts` — interfaces Document, Profile, Institution, etc.
- `src/utils/validators.ts` — isValidFileSize, isValidMimeType, isValidSemester (100% testado)
- `src/utils/formatters.ts` — formatFileSize, formatSemester, formatReputation
- `src/stores/authStore.ts` — Zustand (user, session, isLoading)
- `src/stores/filterStore.ts` — Zustand (institution, course, subject, type, semester)
- `app/_layout.tsx` — QueryClient + auth guard + onAuthStateChange

**Critério de saída:** ✅ testes de validators passando com 100% de cobertura.

---

## Fase 3 — Autenticação 🔶

**Objetivo:** fluxo completo de cadastro, login e onboarding.

**O que foi criado:**
- `src/services/auth.service.ts` — signUp, signIn, signInWithGoogle, signOut, resetPassword
- `src/hooks/useAuth.ts`
- `app/(auth)/login.tsx`, `register.tsx`, `onboarding.tsx`, `forgot-password.tsx`
- Proteção de rotas nos layouts

**Problemas:**
- `onboarding.tsx` tem erros TS (FlatList tipagem + insert profile) → corrigir após gerar types reais
- OAuth Google precisa ser validado no Expo Go (requer `app.json` scheme + redirect URL no Supabase)

**Critério de saída:** usuário consegue se cadastrar, onboarding, login e logout. Sessão persiste.

---

## Fase 4 — Upload de Documentos 🔶

**Objetivo:** usuário seleciona, pré-visualiza, categoriza e publica documento.

**O que foi criado:**
- `src/services/storage.service.ts` — uploadFile, getSignedUrl, deleteFile
- `src/services/documents.service.ts` — createDocument, getDocumentById, incrementViewCount, etc.
- `src/hooks/useUpload.ts`
- `app/(tabs)/upload.tsx`

**Problemas:**
- Erros TS em `documents.service.ts` (insert `never`) → resolvido após gerar types reais
- Componente `UploadForm.tsx` ainda não extraído como componente standalone
- Edge Function `on-document-upload` não criada

**Critério de saída:** upload funciona no Expo Go. +10 pts creditado. Limite 5/dia respeitado.

---

## Fase 5 — Busca e Navegação 🔶

**Objetivo:** usuário encontra documentos por texto e filtros.

**O que foi criado:**
- `searchDocuments`, `getRecentDocuments`, `getPopularDocuments` no service
- `src/hooks/useDocuments.ts` com React Query
- `app/(tabs)/search.tsx` e `app/(tabs)/index.tsx`

**Pendente:**
- Componentes `FilterBar.tsx` e `DocumentCard.tsx` standalone
- Testes

---

## Fase 6 — Visualização de Documentos 🔶

**Objetivo:** usuário visualiza documento dentro do app.

**O que foi criado:**
- `app/document/[id].tsx` — estrutura base

**Pendente:**
- `src/components/DocumentViewer.tsx` (react-native-pdf + zoom)
- Botão Download com verificação de limite
- Tratamento de erros

---

## Fase 7 — Sistema de Reputação ✅

**Objetivo:** regras de reputação funcionando.

**O que foi criado:**
- `src/hooks/useReputation.ts`
- `__tests__/unit/hooks/useReputation.test.ts` — 13 testes, todos passando ✅

**Pendente:**
- `ReputationBadge.tsx` visual
- Edge Function `on-vote`

---

## Fase 8 — Avaliação de Documentos (Votes) 🔶

**Pendente:**
- UI de upvote/downvote na tela do documento
- Modal de motivo para downvote
- Testes

---

## Fase 9 — Perfil do Usuário 🔶

**Pendente:**
- Edição de perfil (nome, avatar)
- Histórico paginado de uploads e downloads
- Upload de avatar para bucket `avatars/`

---

## Fase 10 — Testes e Qualidade 🔶

**Estado atual:**
- 31 testes passando ✅
- `npx tsc --noEmit` → tem erros (causados pelo `database.types.ts` placeholder)

**Checklist:**
- [ ] branches ≥ 70%
- [ ] functions ≥ 80%
- [ ] lines ≥ 80%
- [ ] statements ≥ 80%
- [ ] Zero erros TypeScript
- [ ] Testes E2E Maestro: `auth.yaml`, `document.yaml`

---

## Fase 11 — Critérios de Aceite (Validação Final)

| Critério | iOS | Android |
|---|---|---|
| Cadastro e login | ☐ | ☐ |
| Upload PDF com categorização | ☐ | ☐ |
| Busca por matéria + filtro por tipo | ☐ | ☐ |
| Visualização de PDF no app | ☐ | ☐ |
| Reputação contabilizada corretamente | ☐ | ☐ |
| Documento oculto por downvotes | ☐ | ☐ |
| Limite de downloads respeitado | ☐ | ☐ |
| Cobertura ≥ 80% | ☐ | — |
| App roda no Expo Go | ☐ | ☐ |
| Nenhuma credencial exposta | ☐ | — |

---

## Dependências entre Fases

```
0 (Setup) ✅
└── 1 (Banco) 🔶
    └── 2 (Infraestrutura) ✅
        └── 3 (Auth) 🔶
            ├── 4 (Upload) 🔶
            │   └── 5 (Busca) 🔶
            │       └── 6 (Visualização) 🔶
            │           └── 8 (Votes) 🔶
            │               └── 9 (Perfil) 🔶
            └── 7 (Reputação) ✅
                └── integração com 6 e 8

10 (Testes) ← cobre todas as fases
11 (Validação Final) ← após todas as fases
```

---

## Decisões de Arquitetura

| Decisão | Justificativa |
|---|---|
| Expo Router (file-based) | Convenção moderna do ecossistema Expo, deep linking nativo |
| Supabase | BaaS completo: auth, DB, storage, edge functions — ideal para MVP rápido |
| Zustand para estado global | API simples, sem boilerplate |
| React Query para dados do servidor | Cache, invalidation, loading states, optimistic updates |
| NativeWind | Mesma DX do Tailwind Web, sem overhead de StyleSheet |
| Buckets privados + Signed URLs | Segurança no acesso a documentos |
| Edge Functions para reputação | Lógica de negócio no servidor, não manipulável pelo cliente |
| MSW para mocks de testes | Intercepta na camada de rede, testes mais realistas |

---

## Riscos e Mitigações

| Risco | Mitigação |
|---|---|
| `react-native-pdf` pode ter bugs em alguns devices | Testar em iOS e Android físicos cedo (Fase 6) |
| OAuth Google no Expo Go pode exigir configuração extra | Validar fluxo OAuth no início da Fase 3 |
| `database.types.ts` placeholder causa erros TS em cascata | Conectar Supabase e gerar types reais o quanto antes |
| Limites de rate do Supabase no plano free | Monitorar queries, usar plano Pro antes do beta |
| Upload de arquivos grandes pode ter timeout | Implementar chunked upload se necessário |
| Performance do PDF viewer em documentos longos | Carregar páginas sob demanda |
