# Copa Analyst — Decisões Arquiteturais

Registro das decisões tomadas e das pendências que precisam ser resolvidas antes de avançar nas fases correspondentes. Toda decisão pendente bloqueia a fase listada.

---

## Decisão 1 — Fonte do Rating Prior ⚠️ PENDENTE (bloqueia Fase 1)

**Questão:** qual a fonte de força base das seleções para ancorar o Dixon-Coles?

**Opções avaliadas:**

### Opção A: Elo próprio a partir do openfootball histórico
- **Como:** calcular Elo K-factor a partir de todos os resultados de Copa do Mundo disponíveis no openfootball (1930–2022 + eliminatórias, se disponíveis)
- **Prós:** controle total, rastreável, sem dependência externa além do openfootball (que já é uma dependência)
- **Contras:** mais trabalho de implementação; eliminatórias têm strength-of-schedule muito diferente entre confederações, o que complica a escala comum; Copas antigas têm pouca informação (poucos times, formato diferente)
- **Implementação estimada:** `src/modelos/rating_prior.py` ~100–150 linhas

### Opção B: Ingestão de ranking público
Três sub-opções:

| Fonte | URL | Disponibilidade | Observações |
|---|---|---|---|
| **Club Elo (seleções)** | clubelo.com/api | Grátis, API simples | Cobre seleções nacionais com Elo histórico |
| **FiveThirtyEight SPI** | github.com/fivethirtyeight/data | Grátis, CSV histórico | SPI (Soccer Power Index); FTT encerrou cobertura de futebol em 2023, dados até lá |
| **Ranking oficial FIFA** | fifa.com/rankings | HTML scraping ou CSV | Ranking oficial; metodologia diferente de Elo; mais fácil de explicar para o grupo |

- **Prós:** mais rápido de implementar; rankin FIFA tem credibilidade fácil de explicar
- **Contras:** dependência externa; FIFA ranking é pontual (não dá série histórica para recalcular); FTT SPI está desatualizado desde 2023

### Opção C: Híbrido
- Usar ranking FIFA como prior inicial de força relativa entre confederações
- Ajustar com Elo calculado sobre jogos disponíveis nos últimos X anos
- Maior esforço, mais robusto

**Decisão:** `[ ] PENDENTE — decidir na Fase 0`

**Recomendação tentativa:** Opção B (Club Elo ou ranking FIFA) para chegar rápido ao Jogo 1; avaliar Opção A para v2 se o projeto continuar pós-Copa.

---

## Decisão 2 — Disponibilidade Real da API-Football Free Tier ⚠️ PENDENTE (bloqueia Fases 1 e 2)

**Questão:** quais dados o free tier realmente entrega para seleções?

**O que o PRD (Seção 4.4) documenta como incerto:**
- Plano grátis limita as **temporadas disponíveis** (não apenas o volume de requests)
- Amistosos têm cobertura de estatísticas **inconsistente**
- xG: assumido majoritariamente ausente — o modelo não depende dele

**O que precisa ser confirmado empiricamente (Fase 0):**

| Dado | Endpoint | Status |
|---|---|---|
| Calendário Copa 2026 | `/fixtures?league=1&season=2026` | ⬜ Validar |
| Resultados Copa 2022 | `/fixtures?league=1&season=2022` | ⬜ Validar |
| Stats de partida Copa 2022 (escanteios/chutes/cartões) | `/fixtures/statistics?fixture=<id>` | ⬜ Validar |
| Forma recente — Eliminatórias CONMEBOL 2026 | `/fixtures?league=29&season=2025` | ⬜ Validar |
| Forma recente — Eliminatórias UEFA 2026 | `/fixtures?league=34&season=2025` | ⬜ Validar |
| Amistosos internacionais | `/fixtures?league=10` | ⬜ Validar (cobertura suspeita) |
| Stats de amistosos | `/fixtures/statistics?fixture=<id_amistoso>` | ⬜ Validar |

**Impacto da resposta:**
- Se estatísticas de partida estiverem disponíveis para Copa 2022 + eliminatórias → mercados 7.2 parcialmente calculáveis
- Se estatísticas ausentes para seleções → todos os mercados secundários viram puramente qualitativos
- O modelo Dixon-Coles **não depende** das stats — roda em gols crus. A questão é só para escanteios/cartões/chutes

**Decisão:** `[ ] PENDENTE — resultado da Fase 0 preenche esta seção`

---

## Decisão 3 — Interface: Streamlit ou outra coisa? ✅ DECIDIDO

**Decisão:** começar com **Streamlit**.

**Justificativa:** o valor do projeto está no pipeline de análise e na honestidade do relatório, não na interface. Streamlit entrega o produto funcional em horas; qualquer outro caminho consome tempo que não existe com a Copa começando em uma semana.

**Migração futura:** FastAPI + React apenas se o projeto evoluir pós-Copa e a empolgação justificar. Não é objetivo desta versão.

---

## Decisão 4 — Banco de Dados ✅ DECIDIDO

**Decisão:** **SQLite**.

**Justificativa:** 104 jogos, um grupo de usuários, sem concorrência de escritas, sem necessidade de acesso remoto. O volume não justifica nada maior. `sqlite3` nativo do Python, sem dependência extra.

---

## Decisão 5 — Modelo Estatístico para Resultado/Gols ✅ DECIDIDO

**Decisão:** **Dixon-Coles ancorado no rating prior**, com shrinkage/regularização.

**Justificativa:** D-C puro não funciona para seleções porque não existe um grafo de partidas conexo entre confederações — não há como estimar forças em escala comum só com os jogos disponíveis. O prior fornece a escala; o D-C ajusta a forma recente em torno dela. Ver PRD Seção 7.1.

**Parâmetros a versionar** (não mudar silenciosamente — sempre registrar no relatório):

| Parâmetro | Valor default | Descrição |
|---|---|---|
| `DECAIMENTO_TEMPORAL` | 0.005 | Peso exponencial de jogos antigos |
| `SHRINKAGE_PRIOR` | 0.7 | Força da regularização em direção ao prior |
| `JANELA_FORMA_RECENTE` | 10 | Últimos N jogos para cálculo de forma |
| `HA_REAL` | 0.3 | Vantagem de casa para anfitriões (log-odds) |
| `BANDA_AJUSTE_PP` | 0.10 | Banda máxima de ajuste qualitativo (PRD 2.2) |

**Revisão pós-Fase 2:** calibrar `HA_REAL` e `SHRINKAGE_PRIOR` em jogos históricos antes do Jogo 1.

---

## Decisão 6 — xG ✅ DECIDIDO

**Decisão:** o modelo de gols **não usa xG**.

**Justificativa:** xG de seleção no free tier da API-Football é majoritariamente ausente. Usar gols crus + rating prior é mais honesto do que depender de uma variável que estará missing na maior parte dos jogos. Ver PRD Seção 5.3 e 7.1.

**Campo `xg` na tabela `estatisticas_jogo`:** presente no schema como nullable; sempre tratado como ausente a menos que o dado apareça; nunca imputado.

---

## Decisão 7 — Mercados de Jogador ✅ DECIDIDO (fora do escopo)

**Decisão:** **não implementar no v1**.

**Justificativa:** dados individuais de seleção no free tier são fracos ou ausentes. Qualquer número de jogador seria palpite com verniz de exatidão — contradiz o Princípio 2.1 do PRD. Se solicitado, o sistema responde que está fora de escopo. O campo `entidade` no schema fica reservado para v2.

---

## Decisão 8 — Estratégia de Cache ✅ DECIDIDO

**Decisão:** **cache agressivo no SQLite, cache-first em toda requisição**.

**Regras:**
- Dados históricos de Copas anteriores: imutáveis, puxar uma vez
- Qualquer resposta da API-Football: gravar no banco antes de processar
- Nunca repetir requisição cuja resposta não mudou
- Rate limit de 100 req/dia é uma constraint dura — esgotar é um bug, não um edge case

---

## Decisão 9 — Prompt de Síntese como Artefato Versionado ✅ DECIDIDO

**Decisão:** o prompt de síntese vive em `prompts/sintese_vN.md`, nunca inline no código.

**Regras:**
- Mudança de prompt = novo arquivo (`sintese_v2.md`) + bump de versão
- Toda chamada à IA registra a versão do prompt no relatório (`prompt_versao`)
- Rodar a eval mínima (PRD Seção 10, Fase 3) a cada mudança de prompt
- É o artefato mais sensível do sistema — precisa de histórico auditável

---

## Decisão 10 — Relatório Oficial e Anti-Leakage ✅ DECIDIDO

**Decisão:** relatórios são append-only; apenas o último gerado antes do apito é marcado `eh_relatorio_oficial = true`.

**Regras:**
- Re-run antes do jogo → novo relatório, novo timestamp
- Quando o jogo começa, o último relatório gerado vira o oficial (automático via `hora_utc` ou manual)
- Apenas relatórios oficiais entram na validação Brier/log-loss
- O par (timestamp `gerado_em` + `eh_relatorio_oficial`) é a prova de que a previsão precedeu o resultado

---

## Log de Mudanças

| Data | Decisão | O quê mudou |
|---|---|---|
| 2026-06-04 | Todas | Criação inicial do documento |
