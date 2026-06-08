# Plano — Copa Analyst até o Jogo 1 (11/jun/2026)

**Criado em:** 2026-06-06 · **Copa começa:** 2026-06-11 · **Faltam:** 5 dias

**Estado na criação:** pipeline completo (Fases 0–6) implementado, stack já migrado de
Streamlit → React + FastAPI. Banco com 1176 jogos, 104 da Copa 2026, 273 times com Elo,
494 estatísticas de partida, 8 relatórios. Dois problemas conhecidos: (1) bug que derruba a
página principal e (2) validação real do pipeline ainda não confirmada.

---

## P0 — Crítico: destravar o produto

| # | Tarefa | Arquivo | Status |
|---|--------|---------|--------|
| 1 | Adicionar `import json` (faltando) | `src/api/main.py` | ✅ |
| 2 | Verificar `buscar_relatorio` retornando relatório completo (jogo 41) | — | ✅ |

**Por quê:** `buscar_relatorio` chama `json.loads` mas `json` nunca é importado →
o endpoint `GET /api/jogos/{id}/relatorio` retorna 500 sempre que existe um relatório salvo.
Confirmado contra o banco (relatório id=8 → `NameError: name 'json' is not defined`).
A página **Relatório IA** — conector do pipeline de IA ao frontend — está quebrada hoje.

---

## P1 — Alto: confirmar que funciona de verdade

| # | Tarefa | Status |
|---|--------|--------|
| 3 | Rodar 1 análise real (`MOCK_AI=false`) de um jogo da abertura e ler o relatório | ✅ |
| 4 | Auditar a saída real contra o PRD: origens corretas, `fatores_ausentes` preenchido no cold start, nenhuma prob >60% sem base (PRD 2.1/2.6) | ✅ |
| 5 | Confirmar que repair de 1 tentativa e o caminho de erro não gravam lixo no banco (PRD 6.8) | ✅ |

**Resultado (México × África do Sul, jogo 29):** pipeline rodou ponta a ponta
(relatorio_id=9). Web search real trouxe lesões atuais; validador da banda
auto-corrigiu inconsistência calculado/original e manteve ajustes híbridos ≤10pp;
`fatores_ausentes` rico; cold start e HA=0.25 (anfitrião) declarados.

**⚠️ Achado importante (rate limit):** a conta opera no tier de **30k tokens de
input/minuto**. A pesquisa (web search) + síntese no mesmo minuto estouram o limite
(429). Mitigado com retry/backoff (`src/ia/_retry.py`) — o pipeline aguarda ~60s e
completa. Custo: cada relatório agora leva ~2–3 min. Para acelerar no dia de jogo,
**comprar créditos para subir de tier** (decisão do usuário).

---

## P2 — Médio: qualidade e operação durante a Copa

| # | Tarefa | Status |
|---|--------|--------|
| 6 | Plugar Brier/log-loss real em `/api/calibracao` (lógica já existe em `src/validacao/calibracao.py`; hoje a API só conta) | ✅ |
| 7 | Atualizar `README.md` para o stack real (FastAPI + React; remover instruções Streamlit) | ✅ |
| 8 | Rodar ingestão diária de stats (`python -m src.dados.ingestao inicial`) para reduzir mercados "ausentes" | 🔄 em andamento |
| 9 | Definir fluxo operacional do dia de jogo: gerar → marcar oficial antes do apito → puxar `resultado_real` depois (anti-leakage, PRD 9) | ✅ |

---

## P3 — Opcional / pós-abertura

- ✅ ~~Automação (cron/loop) para puxar resultados durante o torneio.~~ — feito via
  Agendador do Windows (`CopaAnalyst-IngestaoDiaria`, comando `stats` leve).
- ✅ ~~Opus em jogos importantes.~~ — síntese com modelo selecionável por jogo
  (`opus`/`sonnet`) via API (`?modelo=`) e seletor na UI. Default segue `sonnet` (custo).
- ⏸️ Email diário (Resend) — **código pronto** (`src/relatorio/email_diario.py`);
  falta só o usuário pôr `RESEND_API_KEY` + `EMAIL_DESTINATARIOS` no `.env`.

---

## Log de execução

| Data | Item | O que foi feito |
|---|---|---|
| 2026-06-06 | — | Plano criado |
| 2026-06-06 | P0 #1 | `import json` adicionado em `src/api/main.py`. Bug confirmado e corrigido (endpoint `buscar_relatorio` voltou a funcionar). |
| 2026-06-06 | P0 #2 | `buscar_relatorio(41)` retorna relatório completo (resumo + 2 previsões). Smoke dos endpoints sem custo OK via venv. |
| 2026-06-06 | P2 #6 | `/api/calibracao` reescrito para usar `calcular_calibracao`/`pontos_calibracao` (Brier+log-loss por mercado, pontos do gráfico). Chaves antigas mantidas. Tipos TS adicionados em `web/src/lib/api.ts` (tsc OK). |
| 2026-06-06 | P2 #7 | `README.md` atualizado para FastAPI + React; instruções Streamlit removidas (mantida nota de fallback legado). |
| 2026-06-06 | P1 #3–#5 | Análise real de México × África do Sul (jogo 29) rodada com sucesso (relatorio_id=9). Saída auditada contra o PRD: OK. Descoberto rate limit de 30k tokens/min. |
| 2026-06-06 | P1 (extra) | Adicionado retry/backoff em 429 (`src/ia/_retry.py`) ligado a `pesquisa.py` e `sintese.py` (chamada principal + repair). Faz o pipeline sobreviver ao rate limit. |
| 2026-06-07 | P2 #9 | Salvaguarda anti-leakage criada: `src/relatorio/oficial.py` (kickoff, `marcar_oficial_seguro`, `marcar_oficiais_automatico` + CLI). Endpoint `marcar-oficial` agora recusa relatório gerado após o apito; novo `POST /api/marcar-oficiais-automatico`. Frontend mostra o motivo da recusa. Doc `docs/FLUXO_DIA_DE_JOGO.md`. Validado read-only (jogo 29 kickoff 11/jun 13:00 UTC). |
| 2026-06-07 | P2 #8 | Ingestão `inicial` rodada: etapas 1–4 OK; etapa 5 consumiu ~100 requests e bateu o limite diário. Stats subiram de 494→696 linhas (UEFA 2024: 99→200 jogos com stats). Cota reabre amanhã. |
| 2026-06-07 | P2 #8 (fix) | Cliente API-Football agora sinaliza `limite_diario_atingido` e a ingestão **aborta cedo** ao esgotar a cota (antes girava 7s/fixture à toa). `src/dados/api_football.py` + `src/dados/ingestao.py`. |
| 2026-06-08 | P3 (automação) | Ingestão diária automatizada: subcomando leve `stats` (só etapa API-Football, sem re-scrape), `scripts/ingestao_diaria.ps1` + `scripts/registrar_tarefa_diaria.ps1`, tarefa `CopaAnalyst-IngestaoDiaria` registrada (09:00, State Ready). Testada ponta a ponta (~24s, aborta no limite, log em `dados/logs/`). Doc de fluxo atualizada. |
| 2026-06-08 | P3 (Opus) | Modelo de síntese selecionável por jogo: `resolver_modelo` + apelidos opus/sonnet em `sintese.py`, `analisar_jogo(modelo=)`, endpoint `gerar-relatorio?modelo=`, seletor na UI (`Relatorio.tsx`). `modelo_versao` registra o modelo usado. IDs conferidos na ref da Claude API (opus=claude-opus-4-8). Email Resend confirmado code-complete (só config). |
| 2026-06-08 | Deploy simples | FastAPI passa a servir `web/dist` (StaticFiles + fallback SPA) → um único `uvicorn` serve API + UI. Frontend buildado, servidor subido e **UI verificada ponta a ponta com Playwright** (Jogos do Dia com Elo real; Relatório IA renderizando o relatório real do jogo 29 + seletor de modelo). README documenta o deploy de processo único. |
</content>
</invoke>
