# Copa Analyst — Status do Projeto

**Atualizado em:** 2026-06-05  
**Copa do Mundo começa:** 2026-06-11 (6 dias)

---

## 1. Git — Estado atual

| Branch | Conteúdo | Estado |
|---|---|---|
| `master` | Copa Analyst completo (Fases 0–6) | ✅ Correto |
| `main` | ProvaPool (projeto diferente do Rafael, enviado por engano) | ⚠️ Precisa ser movido |

**Ação necessária:** o Rafael deve criar um repo separado para o ProvaPool e remover o branch `main` daqui. Enquanto isso, não interfere no projeto — apenas evitar fazer merge acidental.

---

## 2. Fases de implementação — O que está pronto

| Fase | Status | O que entregou |
|---|---|---|
| 0 — Validação de dados | ✅ Completo | API-Football confirmado, decisões de fontes documentadas |
| 1 — Fundação de dados | ✅ Completo | 957 jogos, Elo, openfootball, Wikipedia, TheSportsDB |
| 2 — Motor estatístico | ✅ Completo | Dixon-Coles + mercados secundários (Poisson) |
| 3 — Pipeline IA | ✅ Completo | Claude + web search + contrato pydantic + digest email |
| 4 — Relatório HTML | ✅ Completo | HTML standalone com badges de origem/incerteza |
| 5 — Interface | ✅ Completo | **React + FastAPI** (Rafael) substituindo Streamlit |
| 6 — Validação | ✅ Completo | Brier/log-loss, resultado_real automático, painel calibração |

---

## 3. O que falta — Banco de dados (CRÍTICO)

### 3.1 Stats de partida (API-Football — limitado a 100 req/dia)

Estatísticas de escanteios, chutes, faltas e cartões alimentam os **mercados secundários** do modelo. Sem elas, essas previsões ficam marcadas como "ausentes" no relatório.

**Estado atual:**

| Dado | Jogos no banco | Stats coletadas |
|---|---|---|
| Copa 2022 | 92 jogos | **28 jogos** (64 faltando) |
| Eliminatórias CONMEBOL 2022 | 90 jogos | 0 |
| Eliminatórias UEFA 2024 | 172 jogos | 0 |
| Eliminatórias CONCACAF 2022 | 62 jogos | 0 |
| Eliminatórias AFC 2022 | 180 jogos | 0 (baixa prioridade) |
| Eliminatórias CAF 2022 | 257 jogos | 0 (baixa prioridade) |

**Requests necessários:**

| Prioridade | Tarefa | Requests | Dias (100/dia) |
|---|---|---|---|
| 🔴 Alta | Completar Copa 2022 stats | 64 | 1 dia |
| 🟠 Média | Stats CONMEBOL 2022 | ~91 | 1 dia |
| 🟠 Média | Stats UEFA 2024 | ~205 | 3 dias |
| 🟡 Baixa | Stats CONCACAF/AFC/CAF | ~500+ | 6+ dias |
| **Total** | **Completo** | **~860** | **~10 dias** |

**Impacto:** sem as stats, o modelo calcula resultado/gols normalmente (usa Elo + Dixon-Coles), mas os mercados de escanteios, cartões, faltas e chutes ficam "ausentes" no relatório.

**Como coletar:** rodar todo dia de manhã:
```bash
python -m src.dados.ingestao inicial
```
O script é idempotente — usa cache, não repete requests já feitos, para sozinho quando chega no limite diário.

### 3.2 Times sem Elo calculado de Copa (cold start)

**24 times** participaram da Copa 2022 e têm Elo calculado com dados reais.  
**88 "times"** no banco incluem:
- **Placeholders de fase eliminatória** (1A, W73, L101 etc.) — normal, serão resolvidos conforme a Copa avança
- **16+ times novos na Copa 2026** (Albânia, Colômbia, Noruega, etc.) — Elo default 1500, modelo os trata como cold start

Times reais sem stats de Copa (cold start total):
`Algeria, Austria, Bosnia & Herzegovina, Cape Verde, Colombia, Curacao, Czech Republic, DR Congo, Egypt, Haiti, Iraq, Ivory Coast, Jordan, New Zealand, Norway, Panama, Paraguay, Scotland, South Africa, Sweden, Turkey, Uzbekistan`

Para eles: o modelo usa só o rating Elo (1500) + forma das eliminatórias (W/D/L). O relatório declara explicitamente como cold start.

---

## 4. O que falta — Configuração

### 4.1 Email diário (Resend) — não configurado

```env
# Adicionar no .env:
RESEND_API_KEY=re_...           ← criar em resend.com (grátis)
EMAIL_REMETENTE=...@dominio.com ← ou onboarding@resend.dev para testes
EMAIL_DESTINATARIOS=email1,email2,email3
```

Sem isso: o digest é gerado mas não enviado por email (salva HTML localmente).

### 4.2 requirements.txt — atualizar com FastAPI/uvicorn

O Rafael adicionou `src/api/main.py` (FastAPI) mas não atualizou o `requirements.txt`. Os colaboradores que clonarem o repo e rodarem `pip install -r requirements.txt` não terão FastAPI instalado.

```bash
# Adicionar ao requirements.txt:
fastapi>=0.115.0
uvicorn>=0.32.0
```

### 4.3 MOCK_AI no .env

Atualmente `MOCK_AI=true` está no `.env` local (modo de desenvolvimento).  
Para análise real antes dos jogos: remover ou comentar essa linha.

---

## 5. O que fazer nos próximos 6 dias (antes do Jogo 1)

| Quando | O que fazer |
|---|---|
| **Hoje** | Coletar stats Copa 2022 (rodar `python -m src.dados.ingestao inicial`) |
| **Hoje** | Configurar Resend no `.env` se quiser emails |
| **Hoje** | Atualizar `requirements.txt` com fastapi/uvicorn |
| **Amanhã** | Rodar ingestão de novo (mais 100 requests — CONMEBOL 2022) |
| **06-08 jun** | Rodar ingestão diária (UEFA 2024 stats) |
| **10 jun** | Testar análise completa com `MOCK_AI=false` para Brasil × Marrocos |
| **10 jun** | Remover `MOCK_AI=true` do `.env` |
| **11 jun** | 🏆 Copa começa — rodar análise de cada jogo do dia antes do apito |

---

## 6. Como rodar o projeto

### Backend + Frontend

```bash
# Terminal 1 — Backend FastAPI
cd "Copa Analyst"
.venv\Scripts\activate
python -m uvicorn src.api.main:app --reload --port 8000

# Terminal 2 — Frontend React
cd "Copa Analyst/web"
npm run dev
```

Acesso: **http://localhost:5173**

### Análise de um jogo (linha de comando)

```bash
python -m src.dados.ingestao jogo <ID>     # ver dados disponíveis
python -m src.dados.ingestao listar        # listar jogos Copa 2026
```

### Digest email do dia

```bash
python -m src.relatorio.email_diario 2026-06-11
```

### Atualizar resultados durante a Copa

```bash
python -m src.dados.ingestao atualizar    # puxa resultados via TheSportsDB
```

---

## 7. Estrutura do projeto

```
Copa Analyst/
├── src/
│   ├── api/         ← FastAPI (backend Rafael)
│   ├── dados/       ← ingestão, API-Football, Wikipedia, TheSportsDB
│   ├── modelos/     ← Dixon-Coles, Elo, mercados secundários
│   ├── ia/          ← síntese Claude, pesquisa, validação pydantic
│   ├── relatorio/   ← gerador HTML, email diário
│   ├── validacao/   ← Brier/log-loss, calibração
│   └── interface/   ← Streamlit (legado, mantido como fallback)
├── web/             ← Frontend React + Vite + Tailwind (Rafael)
├── prompts/         ← sintese_v1.md (prompt versionado)
├── scripts/         ← smoke tests, setup mock, validação Fase 0
└── docs/            ← ROADMAP.md, DECISIONS.md, este arquivo
```
