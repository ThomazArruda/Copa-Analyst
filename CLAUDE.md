# CLAUDE.md — ProvaPool

Guia de contexto para o agente Claude trabalhar neste projeto.

---

## O que é o ProvaPool

App mobile colaborativo onde estudantes universitários brasileiros fazem upload, organizam e acessam provas anteriores, listas de exercícios, resumos e gabaritos. Plataforma-alvo: iOS + Android via Expo Go.

PRD completo em: `PRD_ProvaPool.md`

---

## Stack

| Camada | Tecnologia |
|---|---|
| Mobile | Expo (React Native) + TypeScript |
| Roteamento | Expo Router (file-based) |
| UI | NativeWind (Tailwind para RN) |
| Estado global | Zustand |
| Dados assíncronos | TanStack React Query |
| Backend / Auth / DB | Supabase (PostgreSQL + Auth + Storage + Edge Functions) |
| Armazenamento seguro | Expo SecureStore |
| Testes | Jest + jest-expo + Testing Library + MSW (mocks) + Maestro (E2E) |

---

## Estrutura do Projeto

```
provapool/
├── app/                        # Expo Router — file-based routing
│   ├── (auth)/                 # Rotas não autenticadas
│   │   ├── login.tsx
│   │   ├── register.tsx
│   │   └── onboarding.tsx
│   ├── (tabs)/                 # Rotas autenticadas (bottom tabs)
│   │   ├── _layout.tsx
│   │   ├── index.tsx           # Home / Feed
│   │   ├── search.tsx
│   │   ├── upload.tsx
│   │   └── profile.tsx
│   ├── document/
│   │   └── [id].tsx            # Visualização de documento
│   └── _layout.tsx
│
├── src/
│   ├── components/
│   │   ├── ui/                 # Átomos: Button, Input, Card, etc.
│   │   ├── DocumentCard.tsx
│   │   ├── DocumentViewer.tsx
│   │   ├── FilterBar.tsx
│   │   ├── ReputationBadge.tsx
│   │   └── UploadForm.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useDocuments.ts
│   │   ├── useUpload.ts
│   │   └── useReputation.ts
│   ├── services/
│   │   ├── supabase.ts         # Instância do cliente Supabase
│   │   ├── auth.service.ts
│   │   ├── documents.service.ts
│   │   └── storage.service.ts
│   ├── stores/
│   │   ├── authStore.ts        # Zustand: sessão do usuário
│   │   └── filterStore.ts      # Zustand: filtros ativos de busca
│   ├── types/
│   │   ├── database.types.ts   # Tipos gerados pelo Supabase CLI
│   │   └── app.types.ts        # Tipos da aplicação
│   └── utils/
│       ├── formatters.ts
│       └── validators.ts
│
└── __tests__/
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## Comandos Principais

```bash
# Desenvolvimento
npx expo start               # Inicia o servidor Expo
npx expo start --clear       # Limpa cache e reinicia

# Testes
npx jest                     # Roda todos os testes
npx jest --coverage          # Com relatório de cobertura
npx jest --watch             # Modo watch

# Supabase (via CLI)
supabase gen types typescript --project-id <ID> > src/types/database.types.ts
supabase db push             # Aplica migrations no banco remoto
supabase functions deploy    # Deploy das Edge Functions

# TypeScript
npx tsc --noEmit             # Verifica tipos sem compilar
```

---

## Convenções de Código

### Nomenclatura
- **Componentes React**: PascalCase (`DocumentCard.tsx`)
- **Hooks**: camelCase com prefixo `use` (`useDocuments.ts`)
- **Serviços**: camelCase com sufixo `.service` (`auth.service.ts`)
- **Stores Zustand**: camelCase com sufixo `Store` (`authStore.ts`)
- **Testes**: mesmo nome do arquivo testado com sufixo `.test.ts`

### Estilo
- NativeWind para todos os estilos (classes Tailwind)
- Evitar `StyleSheet.create` salvo exceções com animações
- Componentes de UI base ficam em `src/components/ui/`

### Estado
- **Zustand** para estado global persistente (auth, filtros)
- **React Query** para dados do servidor (documentos, perfis)
- **useState** local apenas para estado de UI (modal aberto, loading local)

### Supabase
- Sempre usar RLS — nunca bypassar com `service_role` no cliente
- Downloads de arquivos sempre via Signed URL (validade 1h)
- Tokens e sessões armazenados exclusivamente no `Expo SecureStore`

---

## Modelo de Dados (Resumo)

Tabelas principais no Supabase:
- `profiles` — dados do usuário (reputação, plano, instituição)
- `institutions` — universidades cadastradas
- `courses` — cursos por instituição
- `subjects` — matérias por curso
- `documents` — arquivos enviados (PDF/imagem)
- `votes` — upvotes/downvotes em documentos
- `downloads` — histórico de downloads por usuário
- `reputation_events` — log de variações de reputação

---

## Regras de Negócio Críticas

| Regra | Detalhe |
|---|---|
| Limite de upload | 5 uploads/dia no plano free |
| Tamanho máximo | 20 MB por arquivo |
| Tipos aceitos | PDF, JPG, PNG |
| Downloads free (rep. positiva) | 20/mês |
| Downloads free (rep. negativa) | 3/mês |
| Downloads Pro | Ilimitado |
| Reputação por upload aprovado | +10 pts |
| Reputação por upvote recebido | +2 pts |
| Auto-ocultar documento | Score < -5 (ratio negativo > 50%) |

---

## Estratégia de Testes

- **Unit (Jest)**: services, hooks, utils — cobertura ≥ 80%
- **Integration (Jest + MSW)**: fluxos completos (upload, busca)
- **E2E (Maestro)**: fluxos críticos (auth, download)

Threshold de cobertura configurado no `jest.config.js`:
- branches: 70% | functions: 80% | lines: 80% | statements: 80%

---

## Segurança

- Bucket `documents/` é **privado** — nunca expor URL direta
- Credenciais nunca no `AsyncStorage`, sempre no `SecureStore`
- Validar MIME type no cliente **e** na Edge Function
- RLS ativa em todas as tabelas (ver SQL no PRD seção 5.4)

---

## Edge Functions

| Função | Trigger | O que faz |
|---|---|---|
| `on-document-upload` | INSERT em `documents` | Valida MIME, conta páginas, +10 pts reputação |
| `on-vote` | INSERT/UPDATE em `votes` | Recalcula score, atualiza reputação, oculta se score < -5 |
