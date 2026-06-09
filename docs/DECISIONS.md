# Copa Analyst — Decisões Arquiteturais

Registro das decisões tomadas e das pendências que precisam ser resolvidas antes de avançar nas fases correspondentes. Toda decisão pendente bloqueia a fase listada.

---

## Decisão 1 — Fonte do Rating Prior ✅ DECIDIDO

**Questão:** qual a fonte de força base das seleções para ancorar o Dixon-Coles?

**Validado na Fase 0:** Club Elo (`api.clubelo.com/<codigo>`) **não retorna dados para seleções nacionais** — a API retornou apenas o header CSV sem linhas de dados. Descartado.

**Decisão: World Football Elo Ratings (eloratings.net) + Elo calculado de openfootball.**

Estratégia em dois passos:

1. **Prior inicial:** baixar os ratings atuais de `eloratings.net` (cobre todas as seleções, metodologia pública, inclui todos os jogos internacionais A desde 1872). Grátis, sem chave, atualizados continuamente. Endpoint: `eloratings.net/World` ou download do histórico completo.

2. **Ajuste com dados disponíveis:** calcular ajuste Elo sobre os jogos que o API-Football free tier entrega (eliminatórias 2022, Copa 2022) para capturar forma recente dentro das janelas acessíveis.

**Por que não FIFA Ranking:** a metodologia do ranking FIFA (pontos por resultado × importância do jogo × força do adversário) não é Elo — não é diretamente comparável em escala nem interpretável como probabilidade de vitória. Eloratings.net usa escala Elo real, que alimenta diretamente o Dixon-Coles.

**Implementação:** `src/modelos/rating_prior.py` — baixar CSV do eloratings.net na inicialização, cachear no SQLite.

---

## Decisão 2 — Disponibilidade Real da API-Football Free Tier ✅ DECIDIDO (validado na Fase 0)

**Restrição crítica descoberta:** o free tier bloqueia seasons 2025 e 2026 com mensagem explícita: *"Free plans do not have access to this season, try from 2022 to 2024."*

### O que está disponível

| Dado | League | Season | Status | Qtd |
|---|---|---|---|---|
| Copa do Mundo 2022 — fixtures | 1 | 2022 | **OK** | 64 jogos |
| Copa do Mundo 2022 — estatísticas de partida | 1 | 2022 | **OK** | escanteios, chutes, faltas, posse, cartões amarelos |
| Copa do Mundo 2026 — fixtures | 1 | 2026 | **BLOQUEADO** | — |
| Eliminatórias CONMEBOL 2022 | 34 | 2022 | **OK** | 90 jogos + stats |
| Eliminatórias UEFA 2024 | 32 | 2024 | **OK** | 204 jogos + stats |
| Eliminatórias CONCACAF 2022 | 31 | 2022 | **OK** | 122 jogos |
| Eliminatórias Ásia 2022 | 30 | 2022 | **OK** | 233 jogos |
| Eliminatórias África 2022 | 29 | 2022 | **OK** | 158 jogos |
| Eliminatórias 2026 (todas) | — | 2026 | **BLOQUEADO** | — |
| Amistosos 2024 | 10 | 2024 | **OK (parcial)** | 394 jogos, stats inconsistentes |
| Amistosos 2025+ | 10 | 2025+ | **BLOQUEADO** | — |

### Estatísticas disponíveis (Copa 2022 + Eliminatórias)

| Stat | Status |
|---|---|
| Escanteios | **Sim** |
| Chutes totais | **Sim** |
| Chutes no alvo | **Sim** |
| Faltas | **Sim** |
| Posse de bola | **Sim** |
| Cartões amarelos | **Sim** |
| Cartões vermelhos | campo presente, geralmente `null` (evento raro — esperado) |
| xG | **Não** (confirmado, como previsto no PRD 5.3) |

### IDs de league confirmados

| Confederação | League ID | Season mais recente disponível |
|---|---|---|
| Copa do Mundo | 1 | 2022 |
| CONMEBOL Eliminatórias | 34 | 2022 |
| UEFA Eliminatórias | 32 | 2024 |
| CONCACAF Eliminatórias | 31 | 2022 |
| Ásia Eliminatórias | 30 | 2022 |
| África Eliminatórias | 29 | 2022 |
| Amistosos internacionais | 10 | 2024 (stats inconsistentes — usar só resultado) |

### Implicação crítica para o modelo

**Todos os jogos da Copa 2026 são efetivamente cold start.** O free tier não entrega o calendário da Copa 2026 nem as eliminatórias do ciclo 2026. A forma recente máxima disponível é até 2024 — lapso de ~1 ano até o torneio.

**Decisão de mitigação:**
- Calendário Copa 2026: **openfootball** (grátis, domínio público)
- Forma recente: Copa 2022 + eliminatórias 2022–2024 disponíveis
- Relatório deve declarar o lapso de dados explicitamente para todos os jogos (PRD 2.4)
- Amistosos 2024: usar apenas resultado (W/D/L) para forma, não stats detalhadas

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

## Decisão 11 — Arquitetura de Fontes de Dados (100% gratuita) ✅ DECIDIDO

**Decisão:** usar combinação de fontes gratuitas em camadas. Nenhum pagamento.

| Dado | Fonte | Método |
|---|---|---|
| Calendário Copa 2026 (104 fixtures) | openfootball/worldcup.json (GitHub) | HTTP GET raw JSON |
| **Resultados Copa 2026 automáticos** | **TheSportsDB free API** | `eventsseason?id=4429&s=2026` — atualiza conforme jogos terminam |
| Forma qualificatórias 2025/2026 (W/D/L + gols) | Wikipedia (scraping) | `requests` + `BeautifulSoup` nas 6 páginas de confederação |
| Stats históricas (escanteios, chutes, faltas, cartões) | API-Football free tier | Copa 2022 + eliminatórias 2022-2024 (temporadas desbloqueadas) |
| Rating prior | eloratings.net | HTTP GET CSV |
| Escalação, lesões, árbitro, notícias | Claude API + web search | Fase 3 |

**Por que TheSportsDB para Copa 2026:** confirmado que retorna fixtures com `intHomeScore`/`intAwayScore` — campos ficam `null` antes do jogo e preenchem automaticamente após o apito final. Brasil 6×2 Panamá (31/mai/2026) já aparece no endpoint `eventslast`. Zero entrada manual.

**Por que Wikipedia para forma 2025/2026:** confirmado que as páginas de qualificatórias (CONMEBOL, UEFA, CONCACAF, AFC, CAF) têm tabelas HTML com todos os 90+ jogos por confederação, com data, times e placar — estrutura consistente e scrapeável. Cobre até set/2025 (última rodada das qualificatórias).

**Gap declarado:** estatísticas granulares (escanteios, chutes, faltas) dos jogos de 2025 não disponíveis gratuitamente. Averages para mercados secundários calculadas com dados 2022-2024. O relatório declara esse lapso (PRD 2.4).

---

## Decisão 12 — Uso pleno dos dados (zero desperdício) ✅ DECIDIDO

**Princípio do usuário:** todo dado coletado deve contribuir nos cálculos; nada fica sem uso.

**Motor de gols (Dixon-Coles):** antes estimava ataque/defesa **só com jogos de Copa**,
deixando ~38 seleções em cold-start (só Elo) apesar de terem dezenas de jogos de
qualificatória no banco. Agora usa **todos** os jogos disponíveis (Copa + qualificatórias
+ amistosos), cada um com peso = `decaimento por recência × peso da competição`:

| Parâmetro | Valor | Descrição |
|---|---|---|
| `SHRINKAGE_FLOOR` | 0.60 | Elo retém ≥60% mesmo com muitos jogos (impede inflação intra-confederação) |
| `PESO copa` | 1.0 | jogo de Copa (sinal cross-confederação) |
| `PESO_QUALIFICATORIA` | 0.5 | qualificatória (força do adversário já no Elo) |
| `PESO_AMISTOSO` | 0.4 | amistoso |
| `JANELA_FORMA` | 40 | usa todos os jogos recentes (decaimento pondera os antigos) |

Fiel ao PRD 7.1 ("usar os jogos disponíveis com regularização ao prior"). Validado em
jogos reais: cold-start eliminado, favoritos favorecidos proporcionalmente ao Elo,
nenhum λ explode. **A recalibrar com dados históricos pós-Fase 2.**

**Mercados secundários:** antes marcava "ausente" se **qualquer** lado faltasse dado.
Agora usa o dado real de cada time onde existe e cai num **prior global** (média do
torneio sobre todas as stats coletadas) onde falta — produzindo previsão **parcial**
(rotulada, com incerteza maior) em vez de vazia. Ex.: México×África do Sul usa as stats
do México + prior para a SA.

---

## Log de Mudanças

| Data | Decisão | O quê mudou |
|---|---|---|
| 2026-06-04 | Todas | Criação inicial do documento |
| 2026-06-09 | 12 | Dixon-Coles usa todos os jogos (não só Copa) com piso de shrinkage; mercados usam prior global para lados sem dado. Zero desperdício de dados. |
| 2026-06-04 | 1 | Decidido: eloratings.net + Elo de openfootball. Club Elo descartado (não cobre seleções nacionais) |
| 2026-06-04 | 2 | Decidido: free tier bloqueia 2025/2026. Copa 2026 via openfootball. Stats disponíveis para 2022-2024 |
| 2026-06-04 | 11 | Decidido: arquitetura de fontes 100% gratuita (ver Decisão 11) |
