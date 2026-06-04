# Copa Analyst

Sistema de análise preditiva pré-jogo para a Copa do Mundo FIFA 2026.

Combina um modelo estatístico (Dixon-Coles ancorado num rating prior) com pesquisa qualitativa via IA para gerar um **relatório por partida**, com previsões para múltiplos mercados, cada uma com probabilidade estimada, nível de incerteza, origem rastreável e justificativa.

> **Aviso:** este é um projeto interno de um grupo de amigos. Não é uma plataforma de apostas e não recomenda apostar dinheiro em nada.

---

## Pré-requisitos

- Python 3.12+
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

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# edite .env com suas chaves

# 5. Inicialize o banco
python -m src.db.schema
```

## Como usar

```bash
# Sobe a interface Streamlit
streamlit run src/interface/app.py
```

Selecione o jogo, clique em "Analisar" e aguarde o relatório.

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
