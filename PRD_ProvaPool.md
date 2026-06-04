# PRD — ProvaPool
## Repositório Colaborativo de Provas e Materiais de Estudo

**Versão:** 1.0  
**Data:** Fevereiro de 2026  
**Status:** Draft  
**Plataforma-alvo:** Mobile (iOS + Android) via Expo Go  

---

## 1. Visão Geral

### 1.1 Resumo do Produto

O **ProvaPool** é uma plataforma mobile colaborativa onde estudantes universitários brasileiros fazem upload, organizam e acessam provas anteriores, listas de exercícios, resumos e gabaritos. O objetivo é democratizar o acesso a material de estudo de qualidade, incentivando a colaboração entre alunos de qualquer instituição do país.

### 1.2 Problema

Estudantes universitários frequentemente buscam provas antigas para se preparar para avaliações, mas esses materiais estão espalhados em grupos de WhatsApp, drives pessoais ou dependem de contatos específicos. Não existe uma plataforma centralizada, organizada e acessível para qualquer estudante brasileiro.

### 1.3 Solução

Um app mobile que funciona como repositório colaborativo, onde qualquer estudante pode contribuir com materiais e acessar o acervo da comunidade, organizado por instituição, curso, matéria e professor.

### 1.4 Público-Alvo

- Estudantes de graduação de universidades públicas e privadas brasileiras
- Faixa etária predominante: 18–28 anos
- Alta familiaridade com smartphones e plataformas de conteúdo colaborativo

---

## 2. Objetivos e Métricas

### 2.1 Objetivos de Negócio

- Atingir 10.000 usuários cadastrados nos primeiros 6 meses
- Construir um acervo de 50.000 documentos no primeiro ano
- Converter 10% dos usuários ativos para o plano Pro

### 2.2 KPIs

| Métrica | Meta 3 meses | Meta 6 meses |
|---|---|---|
| Usuários cadastrados | 2.000 | 10.000 |
| Documentos no acervo | 5.000 | 50.000 |
| DAU / MAU ratio | 20% | 30% |
| Taxa de conversão Pro | — | 10% |
| NPS | > 40 | > 55 |

---

## 3. Funcionalidades

### 3.1 MVP (v1.0)

#### 3.1.1 Autenticação
- Cadastro com e-mail e senha
- Login com e-mail/senha e Google (OAuth)
- Seleção de instituição, curso e período no onboarding
- Recuperação de senha por e-mail

#### 3.1.2 Upload de Documentos
- Upload de arquivos PDF e imagens (JPG, PNG)
- Formulário de categorização obrigatória:
  - Instituição
  - Curso
  - Matéria
  - Professor (opcional)
  - Tipo: Prova / Lista / Resumo / Gabarito
  - Semestre/Ano
- Pré-visualização do arquivo antes de confirmar upload
- Limite de 20 MB por arquivo
- Limite de 5 uploads por dia no plano gratuito

#### 3.1.3 Busca e Navegação
- Busca textual por matéria, professor ou instituição
- Filtros combinados: instituição + curso + matéria + tipo + período
- Feed de documentos recentes e populares na home
- Aba "Minha Faculdade" com feed personalizado pela instituição do usuário

#### 3.1.4 Visualização de Documentos
- Leitor de PDF nativo no app
- Visualizador de imagens com zoom
- Informações do documento: uploader (anônimo ou com username), data, tipo, avaliações
- Contador de visualizações e downloads

#### 3.1.5 Sistema de Reputação
- Pontos ganhos por upload aprovado: +10 pts
- Pontos ganhos por avaliação recebida (upvote): +2 pts
- Usuários com saldo abaixo de 0 pontos têm limite de 3 downloads/mês
- Usuários com saldo positivo têm 20 downloads/mês
- Usuários Pro têm downloads ilimitados

#### 3.1.6 Avaliação de Documentos
- Upvote / Downvote por documento
- Motivos de downvote: "Arquivo ilegível", "Conteúdo errado", "Duplicado", "Outro"
- Documentos com ratio negativo >50% são ocultados para revisão moderação

#### 3.1.7 Perfil do Usuário
- Avatar, nome, instituição e curso
- Pontuação de reputação
- Histórico de uploads
- Histórico de downloads

### 3.2 Roadmap Futuro (v2.0+)

- OCR para busca por conteúdo dentro dos documentos
- Integração com IA para geração de resumos e questões similares
- Modo Estudo (quiz com as questões da prova)
- Notificações push quando novo material da matéria seguida for publicado
- Sistema de favoritos e coleções pessoais
- Moderação comunitária (denúncias e revisões)
- Plano institucional para universidades

---

## 4. User Stories

### Estudante (Usuário Principal)

```
Como estudante, quero pesquisar provas da minha matéria filtradas pelo meu professor
para encontrar exatamente o que preciso para estudar.

Como estudante, quero fazer upload de uma prova que tenho salva no meu celular
para contribuir com a comunidade e ganhar pontos.

Como estudante, quero visualizar um PDF diretamente no app
para não precisar abrir outro aplicativo.

Como estudante, quero ver minha pontuação de reputação
para saber o quanto estou contribuindo com a plataforma.

Como estudante, quero avaliar documentos que baixei
para ajudar a comunidade a identificar materiais de qualidade.
```

---

## 5. Arquitetura Técnica

### 5.1 Visão Geral da Stack

```
┌─────────────────────────────────────────────────────┐
│                   CLIENTE MOBILE                    │
│           Expo (React Native) + TypeScript          │
│                                                     │
│  ┌──────────────┐  ┌───────────────────────────┐   │
│  │   UI Layer   │  │      State Management     │   │
│  │  NativeWind  │  │   Zustand + React Query   │   │
│  │   (Tailwind) │  │                           │   │
│  └──────────────┘  └───────────────────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │            Navigation (Expo Router)           │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────┘
                          │ HTTPS / REST
┌─────────────────────────▼───────────────────────────┐
│                      SUPABASE                       │
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │    Auth     │  │  PostgreSQL  │  │  Storage  │  │
│  │  (JWT/OAuth)│  │  (Database)  │  │  (Files)  │  │
│  └─────────────┘  └──────────────┘  └───────────┘  │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │         Edge Functions (Deno)               │   │
│  │  - Processamento de upload                  │   │
│  │  - Moderação automática                     │   │
│  │  - Cálculo de reputação                     │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 5.2 Estrutura do Projeto (Expo)

```
provapool/
├── app/                          # Expo Router (file-based routing)
│   ├── (auth)/
│   │   ├── login.tsx
│   │   ├── register.tsx
│   │   └── onboarding.tsx
│   ├── (tabs)/
│   │   ├── _layout.tsx
│   │   ├── index.tsx             # Home / Feed
│   │   ├── search.tsx            # Busca
│   │   ├── upload.tsx            # Upload
│   │   └── profile.tsx           # Perfil
│   ├── document/
│   │   └── [id].tsx              # Visualização de documento
│   └── _layout.tsx
│
├── src/
│   ├── components/
│   │   ├── ui/                   # Componentes base (Button, Input, Card...)
│   │   ├── DocumentCard.tsx
│   │   ├── DocumentViewer.tsx
│   │   ├── FilterBar.tsx
│   │   ├── ReputationBadge.tsx
│   │   └── UploadForm.tsx
│   │
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useDocuments.ts
│   │   ├── useUpload.ts
│   │   └── useReputation.ts
│   │
│   ├── services/
│   │   ├── supabase.ts           # Cliente Supabase
│   │   ├── auth.service.ts
│   │   ├── documents.service.ts
│   │   └── storage.service.ts
│   │
│   ├── stores/
│   │   ├── authStore.ts          # Zustand: estado de auth
│   │   └── filterStore.ts        # Zustand: filtros ativos
│   │
│   ├── types/
│   │   ├── database.types.ts     # Tipos gerados pelo Supabase
│   │   └── app.types.ts          # Tipos customizados da aplicação
│   │
│   └── utils/
│       ├── formatters.ts
│       └── validators.ts
│
├── __tests__/
│   ├── unit/
│   │   ├── services/
│   │   │   ├── auth.service.test.ts
│   │   │   └── documents.service.test.ts
│   │   ├── hooks/
│   │   │   ├── useDocuments.test.ts
│   │   │   └── useReputation.test.ts
│   │   └── utils/
│   │       └── validators.test.ts
│   ├── integration/
│   │   ├── upload.flow.test.ts
│   │   └── search.flow.test.ts
│   └── e2e/
│       ├── auth.e2e.ts
│       └── document.e2e.ts
│
├── app.json
├── babel.config.js
├── tsconfig.json
├── jest.config.js
└── package.json
```

### 5.3 Modelo de Dados (PostgreSQL / Supabase)

#### Tabela: `profiles`
```sql
CREATE TABLE profiles (
  id          UUID PRIMARY KEY REFERENCES auth.users(id),
  username    TEXT UNIQUE NOT NULL,
  full_name   TEXT,
  avatar_url  TEXT,
  institution_id UUID REFERENCES institutions(id),
  course_id   UUID REFERENCES courses(id),
  semester    INTEGER CHECK (semester BETWEEN 1 AND 12),
  reputation  INTEGER DEFAULT 0,
  plan        TEXT DEFAULT 'free' CHECK (plan IN ('free', 'pro')),
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

#### Tabela: `institutions`
```sql
CREATE TABLE institutions (
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name      TEXT NOT NULL,
  acronym   TEXT,
  city      TEXT,
  state     CHAR(2),
  verified  BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Tabela: `courses`
```sql
CREATE TABLE courses (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id UUID REFERENCES institutions(id),
  name           TEXT NOT NULL,
  area           TEXT, -- 'Exatas', 'Humanas', 'Saúde', etc.
  created_at     TIMESTAMPTZ DEFAULT NOW()
);
```

#### Tabela: `subjects`
```sql
CREATE TABLE subjects (
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  course_id UUID REFERENCES courses(id),
  name      TEXT NOT NULL,
  code      TEXT, -- código da disciplina (ex: MAT001)
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Tabela: `documents`
```sql
CREATE TABLE documents (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  uploader_id  UUID REFERENCES profiles(id),
  subject_id   UUID REFERENCES subjects(id),
  title        TEXT NOT NULL,
  type         TEXT NOT NULL CHECK (type IN ('prova', 'lista', 'resumo', 'gabarito')),
  professor    TEXT,
  semester     TEXT, -- ex: '2024.1'
  file_path    TEXT NOT NULL, -- path no Supabase Storage
  file_size    INTEGER,
  mime_type    TEXT,
  page_count   INTEGER,
  view_count   INTEGER DEFAULT 0,
  download_count INTEGER DEFAULT 0,
  score        INTEGER DEFAULT 0, -- upvotes - downvotes
  status       TEXT DEFAULT 'active' CHECK (status IN ('active', 'pending', 'hidden', 'removed')),
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_subject ON documents(subject_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_type ON documents(type);
```

#### Tabela: `votes`
```sql
CREATE TABLE votes (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES profiles(id),
  document_id UUID REFERENCES documents(id),
  value       SMALLINT CHECK (value IN (1, -1)),
  reason      TEXT, -- apenas para downvotes
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id, document_id)
);
```

#### Tabela: `downloads`
```sql
CREATE TABLE downloads (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES profiles(id),
  document_id UUID REFERENCES documents(id),
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_downloads_user ON downloads(user_id, created_at);
```

#### Tabela: `reputation_events`
```sql
CREATE TABLE reputation_events (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES profiles(id),
  type        TEXT NOT NULL, -- 'upload_approved', 'upvote_received', etc.
  delta       INTEGER NOT NULL,
  document_id UUID REFERENCES documents(id),
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.4 Row Level Security (RLS)

```sql
-- Usuários só leem/editam o próprio perfil
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Perfil visível para todos"
  ON profiles FOR SELECT USING (true);

CREATE POLICY "Usuário edita próprio perfil"
  ON profiles FOR UPDATE USING (auth.uid() = id);

-- Documentos ativos visíveis para todos autenticados
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Documentos ativos visíveis para autenticados"
  ON documents FOR SELECT
  USING (auth.role() = 'authenticated' AND status = 'active');

CREATE POLICY "Usuário cria próprio documento"
  ON documents FOR INSERT
  WITH CHECK (auth.uid() = uploader_id);

-- Votes: um por usuário por documento
ALTER TABLE votes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Usuário vê próprios votes"
  ON votes FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Usuário cria vote"
  ON votes FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Usuário atualiza próprio vote"
  ON votes FOR UPDATE USING (auth.uid() = user_id);
```

### 5.5 Storage (Supabase Storage)

```
Buckets:
├── documents/          (privado — acesso via signed URL)
│   └── {user_id}/
│       └── {document_id}.pdf
│
└── avatars/            (público)
    └── {user_id}/
        └── avatar.{ext}
```

**Políticas de Storage:**
- Upload restrito ao próprio usuário autenticado
- Download de documentos via Signed URL com validade de 1 hora
- Limite de 20 MB por arquivo (enforced no cliente e no storage)

### 5.6 Edge Functions

#### `on-document-upload`
Trigger após insert em `documents`:
1. Valida tipo MIME do arquivo no storage
2. Conta páginas do PDF
3. Registra evento de reputação (+10 pts) para o uploader
4. Envia notificação para usuários que seguem a matéria

#### `on-vote`
Trigger após insert/update em `votes`:
1. Recalcula `score` do documento
2. Registra evento de reputação para o uploader do documento
3. Se score cair abaixo de -5, muda status para `pending`

---

## 6. Estratégia de Testes

### 6.1 Filosofia

O projeto adota uma pirâmide de testes clássica, com foco em testes unitários e de integração automatizados, viabilizando CI confiável.

```
         ┌──────────┐
         │   E2E    │  (Maestro — poucos, críticos)
        ┌┴──────────┴┐
        │ Integration │  (Jest + MSW — fluxos principais)
       ┌┴────────────┴┐
       │     Unit     │  (Jest — amplo, rápido)
       └──────────────┘
```

### 6.2 Configuração de Testes

**`jest.config.js`**
```js
module.exports = {
  preset: 'jest-expo',
  setupFilesAfterFramework: ['@testing-library/jest-native/extend-expect'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  transformIgnorePatterns: [
    'node_modules/(?!((jest-)?react-native|@react-native|expo|@expo|@unimodules|native-base)/)',
  ],
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/types/**',
  ],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
};
```

### 6.3 Testes Unitários

#### Exemplo: `validators.test.ts`
```typescript
// src/utils/validators.ts
export const isValidFileSize = (bytes: number, maxMB = 20): boolean =>
  bytes <= maxMB * 1024 * 1024;

export const isValidMimeType = (mime: string): boolean =>
  ['application/pdf', 'image/jpeg', 'image/png'].includes(mime);

export const isValidSemester = (semester: string): boolean =>
  /^\d{4}\.(1|2)$/.test(semester);

// __tests__/unit/utils/validators.test.ts
import { isValidFileSize, isValidMimeType, isValidSemester } from '@/utils/validators';

describe('validators', () => {
  describe('isValidFileSize', () => {
    it('aceita arquivo dentro do limite', () => {
      expect(isValidFileSize(10 * 1024 * 1024)).toBe(true); // 10 MB
    });
    it('rejeita arquivo acima do limite', () => {
      expect(isValidFileSize(21 * 1024 * 1024)).toBe(false); // 21 MB
    });
    it('aceita exatamente no limite', () => {
      expect(isValidFileSize(20 * 1024 * 1024)).toBe(true); // 20 MB
    });
  });

  describe('isValidMimeType', () => {
    it('aceita PDF', () => expect(isValidMimeType('application/pdf')).toBe(true));
    it('aceita JPEG', () => expect(isValidMimeType('image/jpeg')).toBe(true));
    it('rejeita Word', () => expect(isValidMimeType('application/msword')).toBe(false));
  });

  describe('isValidSemester', () => {
    it('aceita formato correto', () => expect(isValidSemester('2024.1')).toBe(true));
    it('rejeita semestre 3', () => expect(isValidSemester('2024.3')).toBe(false));
    it('rejeita formato inválido', () => expect(isValidSemester('24.1')).toBe(false));
  });
});
```

#### Exemplo: `documents.service.test.ts`
```typescript
// __tests__/unit/services/documents.service.test.ts
import { getDocumentsBySubject, incrementViewCount } from '@/services/documents.service';

// Mock do cliente Supabase
jest.mock('@/services/supabase', () => ({
  supabase: {
    from: jest.fn(() => ({
      select: jest.fn().mockReturnThis(),
      eq: jest.fn().mockReturnThis(),
      order: jest.fn().mockReturnThis(),
      limit: jest.fn().mockResolvedValue({
        data: [
          { id: 'doc-1', title: 'P1 2024.1', type: 'prova', score: 15 },
        ],
        error: null,
      }),
      rpc: jest.fn().mockResolvedValue({ error: null }),
    })),
  },
}));

describe('documents.service', () => {
  describe('getDocumentsBySubject', () => {
    it('retorna documentos da matéria', async () => {
      const docs = await getDocumentsBySubject('subject-uuid');
      expect(docs).toHaveLength(1);
      expect(docs[0].title).toBe('P1 2024.1');
    });

    it('retorna array vazio quando não há documentos', async () => {
      // Override do mock para este teste
      const { supabase } = require('@/services/supabase');
      supabase.from.mockReturnValueOnce({
        select: jest.fn().mockReturnThis(),
        eq: jest.fn().mockReturnThis(),
        order: jest.fn().mockReturnThis(),
        limit: jest.fn().mockResolvedValue({ data: [], error: null }),
      });

      const docs = await getDocumentsBySubject('subject-vazia');
      expect(docs).toHaveLength(0);
    });
  });
});
```

#### Exemplo: `useReputation.test.ts`
```typescript
// __tests__/unit/hooks/useReputation.test.ts
import { renderHook, act } from '@testing-library/react-hooks';
import { useReputation } from '@/hooks/useReputation';

const mockProfile = { reputation: 45, plan: 'free' };

describe('useReputation', () => {
  it('calcula corretamente o limite de downloads para plano free com reputação positiva', () => {
    const { result } = renderHook(() => useReputation(mockProfile));
    expect(result.current.monthlyDownloadLimit).toBe(20);
  });

  it('reduz limite para 3 quando reputação é negativa', () => {
    const { result } = renderHook(() => useReputation({ ...mockProfile, reputation: -5 }));
    expect(result.current.monthlyDownloadLimit).toBe(3);
  });

  it('retorna ilimitado para plano pro', () => {
    const { result } = renderHook(() => useReputation({ ...mockProfile, plan: 'pro' }));
    expect(result.current.monthlyDownloadLimit).toBe(Infinity);
  });
});
```

### 6.4 Testes de Integração

#### Exemplo: `upload.flow.test.ts`
```typescript
// __tests__/integration/upload.flow.test.ts
import { render, screen, fireEvent, waitFor } from '@testing-library/react-native';
import { setupServer } from 'msw/node';
import { rest } from 'msw';
import UploadScreen from '@/app/(tabs)/upload';
import { AllProviders } from '../test-utils';

const server = setupServer(
  rest.post('*/rest/v1/documents', (req, res, ctx) =>
    res(ctx.json([{ id: 'new-doc-id', status: 'active' }]))
  ),
  rest.post('*/storage/v1/object/*', (req, res, ctx) =>
    res(ctx.json({ Key: 'documents/user-1/new-doc-id.pdf' }))
  )
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('Upload Flow', () => {
  it('permite upload quando todos os campos obrigatórios estão preenchidos', async () => {
    render(<UploadScreen />, { wrapper: AllProviders });

    fireEvent.press(screen.getByText('Selecionar arquivo'));
    // Simula seleção de arquivo via mock do expo-document-picker
    
    fireEvent.changeText(screen.getByPlaceholderText('Nome da matéria'), 'Cálculo I');
    fireEvent(screen.getByTestId('type-select'), 'valueChange', 'prova');
    fireEvent.changeText(screen.getByPlaceholderText('Semestre (ex: 2024.1)'), '2024.1');

    fireEvent.press(screen.getByText('Publicar'));

    await waitFor(() => {
      expect(screen.getByText('Documento publicado com sucesso!')).toBeTruthy();
    });
  });

  it('bloqueia upload quando campos obrigatórios faltam', async () => {
    render(<UploadScreen />, { wrapper: AllProviders });
    fireEvent.press(screen.getByText('Publicar'));

    await waitFor(() => {
      expect(screen.getByText('Preencha todos os campos obrigatórios')).toBeTruthy();
    });
  });
});
```

### 6.5 Testes E2E (Maestro)

```yaml
# e2e/auth.yaml
appId: com.provapool.app
---
- launchApp
- assertVisible: "Entrar no ProvaPool"
- tapOn: "Criar conta"
- inputText:
    id: "input-email"
    text: "teste@universidade.edu.br"
- inputText:
    id: "input-password"
    text: "Senha@123"
- tapOn: "Criar Conta"
- assertVisible: "Selecione sua instituição"
- tapOn: "USP"
- tapOn: "Engenharia de Computação"
- tapOn: "Continuar"
- assertVisible: "Feed"
```

### 6.6 Cobertura de Testes por Módulo

| Módulo | Tipo | Cobertura Alvo |
|---|---|---|
| `utils/validators` | Unit | 100% |
| `services/auth` | Unit | 85% |
| `services/documents` | Unit | 85% |
| `hooks/useReputation` | Unit | 90% |
| `hooks/useDocuments` | Unit | 80% |
| Fluxo de Upload | Integration | — |
| Fluxo de Busca | Integration | — |
| Auth completo | E2E | — |
| Download documento | E2E | — |

---

## 7. Dependências Principais

```json
{
  "dependencies": {
    "expo": "~51.0.0",
    "expo-router": "~3.5.0",
    "react-native": "0.74.x",
    "typescript": "^5.3.0",

    "@supabase/supabase-js": "^2.43.0",
    "expo-secure-store": "~13.0.0",

    "zustand": "^4.5.0",
    "@tanstack/react-query": "^5.40.0",

    "nativewind": "^4.0.0",
    "tailwindcss": "^3.4.0",

    "expo-document-picker": "~12.0.0",
    "expo-file-system": "~17.0.0",
    "expo-image-picker": "~15.0.0",
    "react-native-pdf": "^6.7.0",

    "react-native-reanimated": "~3.10.0",
    "react-native-gesture-handler": "~2.16.0"
  },
  "devDependencies": {
    "jest": "^29.0.0",
    "jest-expo": "~51.0.0",
    "@testing-library/react-native": "^12.0.0",
    "@testing-library/jest-native": "^5.4.0",
    "@testing-library/react-hooks": "^8.0.0",
    "msw": "^2.3.0"
  }
}
```

---

## 8. Fluxos de Usuário

### 8.1 Onboarding
```
Splash → Login/Cadastro → Seleção de Instituição → Seleção de Curso
→ Período atual → Home (Feed personalizado)
```

### 8.2 Upload
```
Tab Upload → Selecionar arquivo (picker) → Pré-visualização
→ Preenchimento do formulário → Validação → Publicar
→ Processamento (Edge Function) → Confirmação + +10 pts
```

### 8.3 Busca e Download
```
Tab Busca → Digitação → Filtros (opcional) → Lista de resultados
→ Tap no documento → Tela de detalhes → Visualizar PDF
→ Botão Download → Verificação de limite → Download via Signed URL
→ Avaliação pós-download (opcional)
```

---

## 9. Considerações de Segurança

- Todos os arquivos são armazenados em bucket **privado** no Supabase Storage
- Downloads são servidos via **Signed URLs** com validade de 1 hora, impossibilitando hotlinking
- RLS enforça no banco que usuários não autenticados não acessam nada
- Rate limiting de uploads previne abuso (5/dia no plano free)
- Arquivos passam por validação de MIME type no cliente e na Edge Function
- Dados sensíveis (tokens) armazenados no Expo SecureStore, nunca no AsyncStorage

---

## 10. Critérios de Aceite para MVP

- [ ] Usuário consegue se cadastrar e fazer login
- [ ] Usuário consegue fazer upload de um PDF com categorização completa
- [ ] Usuário consegue buscar documentos por matéria e filtrar por tipo
- [ ] Usuário consegue visualizar PDF dentro do app
- [ ] Sistema de reputação contabiliza pontos corretamente
- [ ] Downvotes suficientes ocultam documento automaticamente
- [ ] Limite de downloads por mês é respeitado conforme o plano
- [ ] Cobertura de testes unitários ≥ 80%
- [ ] App roda corretamente no Expo Go (iOS e Android)
- [ ] Nenhuma credencial exposta no cliente

---

*Documento gerado em Fevereiro de 2026. Revisões devem ser versionadas neste arquivo com data e responsável.*
