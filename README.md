# Copa Analyst

Sistema de análise preditiva pré-jogo para a Copa do Mundo FIFA 2026.

Combina um modelo estatístico (Dixon-Coles ancorado num rating prior) com pesquisa qualitativa via IA para gerar um **relatório por partida**, com previsões para múltiplos mercados, cada uma com probabilidade estimada, nível de incerteza, origem rastreável e justificativa.

> **Aviso:** este é um projeto interno de um grupo de amigos. Não é uma plataforma de apostas e não recomenda apostar dinheiro em nada.

---

## Stack

- **Backend:** Python 3.12+ · FastAPI + Uvicorn
- **Frontend:** React + Vite + Tailwind (`web/`)
- **Banco:** SQLite
- **IA:** API da Anthropic (Claude com web search)

> Nota: a interface migrou de Streamlit para **React + FastAPI**. O app Streamlit
> em `src/interface/app.py` permanece apenas como fallback legado.

## Pré-requisitos

- Python 3.12+
- Node.js 18+ (para o frontend)
- Chave da API da Anthropic (`ANTHROPIC_API_KEY`)
- Chave da API-Football free tier (`API_FOOTBALL_KEY`) — 100 req/dia

## Instalação

```bash
# 1. Clone o repositório
git clone <repo>
cd copa-analyst

# 2. Crie o ambiente virtual
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows

# 3. Instale as dependências Python
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# edite .env com suas chaves

# 5. Instale as dependências do frontend
cd web
npm install
cd ..
```

## Como rodar

```bash
# Terminal 1 — Backend FastAPI (porta 8000)
.venv\Scripts\activate      # Windows  (source .venv/bin/activate no Linux/Mac)
python -m uvicorn src.api.main:app --reload --port 8000

# Terminal 2 — Frontend React (porta 5173)
cd web
npm run dev
```

Acesse **http://localhost:5173**. Selecione o jogo na página "Relatório IA",
clique em "Gerar análise" e aguarde ~30–60s.

> Para desenvolver a UI sem gastar chamadas pagas da API Anthropic, defina
> `MOCK_AI=true` no `.env`. Remova-o para gerar análises reais.

## Comandos de linha de comando (dados)

```bash
python -m src.dados.ingestao listar        # lista os jogos da Copa 2026
python -m src.dados.ingestao jogo <ID>     # mostra os dados duros de um jogo
python -m src.dados.ingestao inicial       # ingere stats (idempotente, respeita 100 req/dia)
python -m src.dados.ingestao atualizar     # puxa resultados via TheSportsDB
```

---

## Arquitetura em uma linha

```
Rating prior → Dados duros → Pesquisa web (IA) → Modelo D-C → Síntese IA → Relatório HTML
```

Ver `CLAUDE.md` para a arquitetura completa e `docs/ROADMAP.md` para o plano de fases.

## Documentação

| Arquivo | Conteúdo |
|---|---|
| `PRD_Copa_Analyst_v1.1.md` | Requisitos completos do produto — fonte única de verdade |
| `CLAUDE.md` | Instruções de desenvolvimento para Claude Code |
| `docs/ROADMAP.md` | Fases de implementação e status |
| `docs/DECISIONS.md` | Decisões arquiteturais e pendências |
| `prompts/sintese_v1.md` | Prompt de síntese da IA (artefato versionado) |

## Validação e anti-data leakage

Toda previsão é travada com timestamp antes do apito inicial. A métrica de qualidade é Brier score / log-loss — nunca "% de acertos". Ver PRD Seção 9.
