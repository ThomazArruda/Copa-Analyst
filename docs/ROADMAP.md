# Copa Analyst — Roadmap de Implementação

**Contexto de urgência:** a Copa começa em **11 de junho de 2026**. As Fases 0–5 precisam estar operacionais para o Jogo 1. A Fase 6 pode rodar durante o torneio.

---

## Status Geral

| Fase | Título | Status | Prazo alvo |
|---|---|---|---|
| 0 | Validação de dados | ⬜ Não iniciada | **HOJE** |
| 1 | Fundação de dados | ⬜ Não iniciada | 5–6 jun |
| 2 | Motor estatístico | ⬜ Não iniciada | 7–8 jun |
| 3 | Cérebro de IA + contrato de saída | ⬜ Não iniciada | 8–9 jun |
| 4 | Relatório HTML | ⬜ Não iniciada | 9–10 jun |
| 5 | Interface Streamlit | ⬜ Não iniciada | 10 jun |
| 6 | Ciclo de validação | ⬜ Não iniciada | Durante a Copa |

---

## Fase 0 — Validação de Viabilidade de Dados ⚠️ CRÍTICA, FAZER AGORA

**Por que é obrigatória:** as Fases 1 e 2 dependem de saber o que o free tier da API-Football realmente entrega para seleções. Construir o motor estatístico sobre dados que não existem é o erro mais caro possível.

### Tarefas

- [ ] Registrar conta em api-sports.io e obter `API_FOOTBALL_KEY`
- [ ] Mapear empiricamente: quais temporadas de competições de seleção o free tier expõe
  - Eliminatórias (CONMEBOL, UEFA, CONCACAF, CAF, AFC, OFC)
  - Amistosos internacionais
  - Copa do Mundo (histórico: 2018, 2022, 2026)
  - Copa das Confederações / Copas continentais (Copa América, Euro, etc.)
- [ ] Confirmar se as rotas de **estatísticas de partida** retornam dados para jogos de seleção no free tier:
  - `/fixtures/statistics` → escanteios, chutes, cartões, posse, faltas
  - Para cada liga/temporada confirmada, fazer 1–2 chamadas de teste e anotar o resultado
- [ ] Confirmar cobertura de amistosos (a documentação diz que é inconsistente)
- [ ] Testar `/fixtures?league=1&season=2022` (Copa 2022) e verificar se vêm estatísticas
- [ ] Decidir a fonte do rating prior (ver `docs/DECISIONS.md` Decisão 1)

### Entregável

Atualizar `docs/DECISIONS.md` com:
- Lista exata de quais endpoints/temporadas estão disponíveis no free tier
- Decisão sobre o rating prior
- Quais mercados secundários (7.2 do PRD) são calculáveis vs. puramente qualitativos

**Não pular esta fase.** O custo de fazer agora é 2–3 horas. O custo de não fazer é descobrir na véspera do Jogo 1 que os dados não existem.

---

## Fase 1 — Fundação de Dados

**Dependência:** Fase 0 concluída (saber o que o free tier entrega).

**Objetivo:** dado um jogo, o sistema consegue reunir todos os dados duros disponíveis + o rating prior.

### Tarefas

- [ ] `src/db/schema.sql` — criar o schema SQLite conforme PRD Seção 5
  - `times`, `jogos`, `estatisticas_jogo`, `relatorios`, `previsoes`
  - Atenção: `campo_neutro` boolean, `placar_*` nullable, `xg` nullable
- [ ] `src/db/repositorio.py` — camada de acesso ao banco (toda I/O passa por aqui)
- [ ] `src/dados/openfootball.py` — ingerir do repositório openfootball:
  - Calendário 2026: todos os 104 jogos com data, hora UTC, estádio, cidade
  - Grupos e seleções classificadas
  - Histórico de Copas anteriores (jogos + placares — imutáveis, puxar uma vez)
- [ ] `src/modelos/rating_prior.py` — implementar a fonte de prior escolhida na Fase 0
- [ ] `src/dados/api_football.py` — cliente API-Football:
  - Rate limiting: não passar de 100 req/dia
  - Cache-first: toda resposta vai ao SQLite antes de processar
  - Só buscar os endpoints/temporadas confirmados na Fase 0
- [ ] `src/dados/ingestao.py` — orquestrador: dado um `jogo_id`, retorna o pacote de dados duros
- [ ] Smoke test: listar todos os 104 jogos da Copa; dado Brasil × Argentina, retornar o pacote de dados

### Entregável

`python -m src.dados.ingestao --jogo <id>` imprime os dados disponíveis para o jogo sem erros.

---

## Fase 2 — Motor Estatístico

**Dependência:** Fase 1 (dados no banco).

**Objetivo:** dado um jogo, gerar previsões puramente calculadas com comportamento sensato no cold start.

### Tarefas

- [ ] `src/modelos/dixon_coles.py` — Dixon-Coles ancorado no prior:
  - Força de ataque/defesa inicializada a partir do `rating_prior`
  - Regularização (shrinkage) em direção ao prior — estabiliza estimativas com poucos jogos
  - Vantagem de casa: **zero quando `campo_neutro = true`**; HA real apenas para Canadá, EUA, México em casa
  - Decaimento temporal: parâmetro versionado (não hardcoded)
  - Output: matriz de probabilidade de placares → vitória/empate/derrota, over/under, ambas marcam, placar mais provável
  - Cold start (1ª rodada): funcionar com só o prior + forma recente fora da Copa; documentar a dependência no output
- [ ] `src/modelos/mercados.py` — distribuições dos mercados secundários (apenas para os dados que a Fase 0 confirmou como disponíveis):
  - Escanteios: Poisson ou Binomial Negativa a partir das médias das seleções
  - Cartões/faltas: idem, mais perfil do árbitro quando disponível
  - Chutes por time
  - Se não há média disponível → retornar `None` (não inventar)
- [ ] Validar calibração básica em jogos históricos (ex.: Copa 2022) — não para tunar, mas para verificar que não há bug óbvio

### Parâmetros a versionar no código (nunca mudar silenciosamente)

```python
DECAIMENTO_TEMPORAL = 0.005      # peso de jogos antigos
SHRINKAGE_PRIOR = 0.7            # força do shrinkage em direção ao prior (0=sem prior, 1=só prior)
JANELA_FORMA_RECENTE = 10        # últimos N jogos para forma
HA_REAL = 0.3                    # vantagem de casa para anfitriões (em log-odds, a calibrar)
BANDA_AJUSTE_PP = 0.10           # banda da 2.2 do PRD
```

### Entregável

`python -m src.modelos.dixon_coles --jogo <id>` imprime previsões calculadas com origens `calculado`, sem erro no cold start.

---

## Fase 3 — Cérebro de IA, Pesquisa e Contrato de Saída

**Dependência:** Fase 2 (previsões calculadas disponíveis).

**Objetivo:** pipeline completo [0]→[4] gerando previsões validadas na tabela `previsoes`.

### Tarefas

- [ ] `src/ia/pesquisa.py` — pesquisa qualitativa via Claude com web search:
  - Buscas dirigidas: escalação provável, lesões, suspensões, árbitro designado, situação de classificação no grupo
  - Rotular fontes como primárias / secundárias / fracas
  - Retornar resultado estruturado (não texto livre)
- [ ] `prompts/sintese_v1.md` — prompt de síntese (ARTEFATO VERSIONADO):
  - Implementa todos os Princípios do PRD Seção 2
  - Instrui sobre a regra de ajuste limitado (banda ±10pp)
  - Instrui sobre `fatores_ausentes` obrigatório
  - Define o schema de saída JSON (Seção 6.8)
  - Instrui sobre head-to-head com peso baixo (PRD 6.6)
  - Instrui sobre bom senso (PRD 2.5): não forçar profundidade sem dados
- [ ] `src/ia/validacao.py` — validador pydantic do contrato de saída (PRD Seção 6.8):
  - Schema completo com todos os campos
  - Regras da banda: `|estimada − original| ≤ 0.10` quando híbrido
  - Repair de 1 tentativa (reenviar erro à IA)
  - Nunca gravar dado malformado no banco
- [ ] `src/ia/sintese.py` — orquestrador da síntese:
  - Monta o contexto completo (prior + modelo + pesquisa + dados duros)
  - Chama o prompt versionado
  - Passa pelo validador
  - Registra em `relatorios` + `previsoes`
  - Registra `prompt_versao` e `modelo_versao` no relatório
- [ ] Eval mínima do prompt: 3–5 jogos históricos com expectativas qualitativas:
  - "Se escalação ausente → deve aparecer em `fatores_ausentes`"
  - "Se ajuste > 10pp → deve virar `qualitativo`"
  - "Se só prior disponível → incerteza deve ser `media` ou `alta`"

### Entregável

`python -m src.ia.sintese --jogo <id>` grava um relatório completo com previsões validadas no banco.

---

## Fase 4 — Relatório HTML

**Dependência:** Fase 3 (previsões no banco).

**Objetivo:** relatório legível e claro para o grupo, com a estrutura da PRD Seção 8.

### Tarefas

- [ ] `src/relatorio/template.html` — template do relatório:
  - Cabeçalho: jogo, fase, data/hora, estádio, altitude (quando relevante), timestamp de geração, versão do prompt/modelo, flag de relatório oficial
  - Resumo executivo
  - Previsões por mercado: previsão + probabilidade + incerteza + **etiqueta de origem visualmente distinta** + justificativa
  - Quando híbrido: mostrar valor calculado original → valor ajustado + motivo
  - Fatores considerados
  - **Fatores NÃO avaliados** (obrigatório — PRD 2.4)
  - Fontes
- [ ] `src/relatorio/gerador.py` — gera o HTML a partir do relatório no banco
- [ ] Tratamento visual de incerteza: cor/etiqueta/posição para distinguir previsões sólidas de palpites (PRD 8.3)

### Entregável

`python -m src.relatorio.gerador --relatorio <id>` gera `relatorios/jogo_<id>.html` abrível em qualquer browser.

---

## Fase 5 — Interface Streamlit

**Dependência:** Fases 1–4 funcionando via linha de comando.

**Objetivo:** o produto utilizável de ponta a ponta pelo grupo.

### Tarefas

- [ ] `src/interface/app.py` — interface Streamlit:
  - Listar jogos da Copa com data/hora/fase/grupo
  - Seleção de jogo e botão "Analisar"
  - Barra de progresso enquanto o pipeline roda
  - Visualização do relatório gerado (inline ou iframe do HTML)
  - Lista de relatórios anteriores para o jogo (re-runs)
  - Botão para marcar relatório como "oficial" (ou automático via `hora_utc`)
  - Indicação de qual relatório é o oficial para cada jogo
- [ ] Modo `MOCK_AI=true` para testar a UI sem chamar a API Anthropic

### Entregável

`streamlit run src/interface/app.py` → o grupo consegue usar o produto de ponta a ponta.

---

## Fase 6 — Ciclo de Validação (durante a Copa)

**Dependência:** jogos acontecendo e relatórios oficiais gerados.

**Objetivo:** painel honesto de calibração.

### Tarefas

- [ ] `src/dados/resultados.py` — preencher `resultado_real` após cada jogo:
  - Automático via API-Football quando disponível
  - Fallback: formulário manual no Streamlit
- [ ] `src/validacao/calibracao.py` — calcular Brier score e log-loss:
  - **Apenas sobre relatórios oficiais** (`eh_relatorio_oficial = true`)
  - Por mercado e agregado
- [ ] Painel de calibração no Streamlit:
  - Gráfico de calibração (probabilidade prevista vs. frequência real)
  - **Aviso explícito de ruído nas primeiras rodadas** (PRD 9.5)
  - "Este painel é descritivo. Não mudar o modelo com base em poucos jogos."

### Entregável

Painel de calibração atualizado após cada rodada, com aviso de ruído.

---

## Não-objetivos (lembrete rápido)

- Bolão / leaderboard
- Plataforma de apostas
- Análise ao vivo
- Mercados de jogador (v1)
- Multi-usuário / login
- Re-treino de ML
- Dados pagos

Ver PRD Seção 11 para a lista completa.
