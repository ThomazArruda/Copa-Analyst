# PRD — Sistema de Análise Preditiva Multifatorial · Copa do Mundo 2026

**Versão:** 1.1
**Status:** Aprovado para implementação
**Idioma do produto:** Português (BR)
**Tipo de documento:** Product Requirements Document para desenvolvimento assistido por Claude Code

> **Mudanças da v1.0 → v1.1** (motivadas por revisão técnica pré-implementação):
> - **Modelo:** Dixon-Coles agora é **ancorado num rating prior global** (não roda from scratch), porque seleções não formam um grafo de partidas conexo. (Seção 7.1.)
> - **Cold start:** fonte de força pré-torneio definida explicitamente para a 1ª rodada. (Seção 6.2, 7.1.)
> - **Vantagem de casa:** parametrizada — zero em campo neutro, real só para os 3 anfitriões. (Seção 7.1.)
> - **Ajuste qualitativo limitado:** a IA não re-numera livremente; opera dentro de bandas e regras. (Seção 2.2, 6.5.)
> - **Contrato de saída da IA:** schema JSON estrito + validação + repair. Nova Seção 6.8.
> - **Prompt como artefato versionado** no repo, com eval mínima. (Seção 4.3, 10 Fase 3.)
> - **`acertou` removido** como métrica (contradizia a 9.3); vira campo derivado só de display. (Seção 5.5, 9.3.)
> - **Free tier do API-Football:** caveat de temporadas limitadas + amistosos com cobertura inconsistente; validação obrigatória na Fase 1. (Seção 4.4, 10 Fase 1.)
> - **xG:** assumido como majoritariamente indisponível; modelo de gols roda em gols crus + rating. (Seção 5.3, 7.1.)
> - **Re-run / qual relatório conta:** semântica definida. (Seção 5.4, 6.1, 9.1.)
> - **Mercados de jogador (7.3) movidos para fora do escopo v1.** (Seção 7.3, 11.)

---

## 0. Como ler este documento

Este PRD é a fonte única de verdade do projeto. Toda decisão de implementação deve ser rastreável a uma seção daqui. Se durante o desenvolvimento surgir uma dúvida que o PRD não responde, a resposta correta é **parar e atualizar o PRD primeiro**, não improvisar no código.

As seções estão ordenadas da intenção para o detalhe: começa pela visão e pelos princípios (o "porquê"), passa pela arquitetura e modelo de dados (o "como"), detalha o fluxo de análise e a especificação de cada mercado (o "o quê"), e fecha com fases de implementação e não-objetivos (os limites).

---

## 1. Visão geral

### 1.1 O problema

Um grupo de amigos analisa partidas de futebol manualmente antes de cada jogo, cruzando histórico recente, escalações, estatísticas, notícias e contexto para prever resultados e mercados. O processo é trabalhoso, inconsistente entre jogos, limitado pela quantidade de informação que humanos conseguem processar em tempo hábil, e impossível de escalar para todos os jogos de uma Copa do Mundo com 104 partidas.

### 1.2 A solução

Um sistema que automatiza essa análise multifatorial para um jogo específico, sob demanda, combinando:

- **Dados estatísticos duros** (histórico, forma, médias de mercados) processados por modelos numéricos ancorados num rating prior.
- **Pesquisa qualitativa atual** (escalações, notícias, contexto) coletada e sintetizada por uma IA com acesso à web.

O sistema gera um **relatório pré-jogo** por partida, contendo previsões para múltiplos mercados (vencedor, gols, escanteios, cartões, chutes, faltas, etc.), cada uma acompanhada de seu **nível de incerteza**, sua **probabilidade estimada**, e a **justificativa rastreável** de onde aquela previsão veio.

### 1.3 O que este sistema NÃO é

Não é um sistema de apostas, não é um bolão, não é um placar de competição entre os usuários, e não opera durante o jogo. É uma ferramenta de análise pré-jogo. (Ver Seção 11 — Não-objetivos.)

### 1.4 Contexto de uso

Os usuários (o grupo de amigos) usam o relatório como insumo para uma competição informal de palpites que eles conduzem **manualmente, por fora do sistema**. O sistema não precisa saber que essa competição existe. Seu único trabalho é produzir a melhor análise honesta possível de um jogo.

---

## 2. Princípios de design (inegociáveis)

Estes princípios têm precedência sobre qualquer decisão de implementação. Quando houver conflito entre "fazer parecer impressionante" e um princípio abaixo, o princípio vence.

### 2.1 Honestidade epistêmica acima de tudo

O maior risco do projeto não é errar uma previsão — é **soar confiante e preciso sobre coisas que são, na verdade, estimativas frágeis**. Um número como "68% de chance de +2 chutes do Vini Jr" parece científico mas, se derivado de leitura qualitativa, é um palpite com verniz de exatidão. O sistema deve sempre deixar claro o grau de solidez de cada afirmação.

### 2.2 Separação entre cálculo e estimativa qualitativa — e ajuste qualitativo *limitado*

Toda previsão carrega uma etiqueta de **origem**:

- **`calculado`** — derivado de um modelo estatístico com base em dados quantitativos (ex.: probabilidade de vitória via Dixon-Coles ancorado).
- **`qualitativo`** — derivado do raciocínio da IA sobre pesquisa e contexto (ex.: impacto de uma lesão, momento psicológico).
- **`híbrido`** — o número vem do modelo, mas foi ajustado por um fator qualitativo, e o relatório explica o ajuste.

O usuário deve sempre conseguir distinguir os três. Cálculo e qualitativo **se somam** — um não substitui o outro — mas nunca se disfarçam um de outro.

**Regra dura contra a re-numeração livre (anti-2.1):** quando a previsão é `híbrido`, a IA **não pode reescrever a probabilidade calculada à vontade**. Ela só pode:
1. **Mover a probabilidade calculada dentro de uma banda fixa** (default: ±10 pontos percentuais), registrando o valor original, o valor ajustado e o motivo; **ou**
2. **Rebaixar a confiança** (subir a `incerteza`) sem mudar o número; **ou**
3. **Sobrepor uma previsão puramente qualitativa** — caso em que a origem vira `qualitativo`, não `híbrido`, e a probabilidade calculada some do bloco (não fica "emprestando" credibilidade a um palpite).

Ajuste fora da banda exige a IA rebaixar a origem para `qualitativo`. Isso impede que um palpite herde a aparência de precisão de um cálculo.

### 2.3 Rastreabilidade total ("de onde veio isso?")

Cada previsão no relatório carrega sua justificativa: o número do cálculo (com os inputs que o alimentaram) ou o raciocínio + as fontes (links) que a IA usou. Nenhuma afirmação é uma caixa-preta. Se o usuário não consegue auditar de onde veio uma conclusão, ela não deve estar no relatório.

### 2.4 O sistema declara o que não sabe

Um analista honesto fala o que não conseguiu avaliar. Se a escalação ainda não saiu, se não há dados de escanteios de uma seleção, se uma fonte é fraca — o relatório diz isso explicitamente e **rebaixa a confiança** das previsões afetadas. A ausência de um dado é, ela mesma, uma informação que vai no relatório.

### 2.5 Bom senso sobre necessário vs. possível

A IA deve julgar, jogo a jogo, o que é *necessário* analisar versus o que é *possível* analisar com os dados disponíveis. Não deve forçar uma análise 1-a-1 de elenco quando não há dados individuais confiáveis, nem inventar profundidade onde não há base. Profundidade real onde há dados; honestidade sobre a limitação onde não há.

### 2.6 Calibração honesta, não acurácia inflada

A meta nunca é "acertar 90%". Em futebol, mesmo os melhores modelos do mundo acertam o vencedor em ~50-55% dos casos. Qualquer métrica de validação que sugira acurácia muito alta deve ser tratada como **suspeita de vazamento de dados (data leakage)** até prova em contrário. (Ver Seção 9 — Validação e anti-leakage.)

---

## 3. Escopo e cronograma de contexto

- **Torneio:** Copa do Mundo FIFA 2026 (Canadá, EUA, México).
- **Período:** 11 de junho a 19 de julho de 2026.
- **Formato:** 48 seleções, 12 grupos de 4, 104 partidas. Avançam os 2 primeiros de cada grupo + os 8 melhores terceiros colocados.
- **Modo de operação:** análise **sob demanda**, executada pelo usuário pouco antes de cada jogo, para capturar a escalação e as notícias mais recentes possíveis.

---

## 4. Arquitetura do sistema

### 4.1 Visão de alto nível

O sistema é um **pipeline de análise por jogo** orquestrado por uma camada de IA. O fluxo, dado um jogo selecionado pelo usuário:

```
[0] RATING PRIOR GLOBAL  (uma vez, atualizável)
    → força de cada seleção numa escala comum (Elo/SPI/FIFA),
      base que torna comparáveis times de confederações diferentes
        ↓
[1] COLETA DE DADOS DUROS
    → calendário, grupos, histórico, forma na Copa (openfootball + API-Football)
        ↓
[2] PESQUISA QUALITATIVA (web)
    → escalação provável, lesões/suspensões, notícias, declarações,
      árbitro designado, contexto de viagem/altitude/descanso
        ↓
[3] MODELO ESTATÍSTICO
    → Dixon-Coles ANCORADO no prior [0] para gols/resultado;
      distribuições para mercados secundários
        ↓
[4] SÍNTESE POR IA
    → funde [0]+[1]+[2]+[3], faz leituras qualitativas, calibra incertezas,
      decide o que sabe e o que não sabe, escreve as justificativas,
      respeitando a regra de ajuste limitado (2.2)
        ↓
[5] RELATÓRIO
    → documento pré-jogo em português, por mercado, com previsão +
      probabilidade + incerteza + origem + justificativa rastreável
```

### 4.2 Componentes

| Componente | Responsabilidade | Tecnologia sugerida |
|---|---|---|
| **Rating prior** | Manter força base de cada seleção numa escala comum | Python; Elo próprio ou ingestão de ranking público |
| **Ingestão de dados** | Puxar e cachear dados de fixtures, histórico e estatísticas | Python, `requests`, cache local |
| **Camada de pesquisa** | Buscas web direcionadas e extração de conteúdo | API da Anthropic com ferramenta de web search |
| **Motor estatístico** | Dixon-Coles ancorado e distribuições de mercados | Python, `numpy`, `scipy`, `statsmodels` |
| **Orquestrador / cérebro** | Coordena o pipeline, monta o prompt de síntese, chama a IA, **valida o output** | Python + API da Anthropic |
| **Validador de saída** | Garante que o JSON da IA bate com o schema (Seção 6.8) | Python, `pydantic` |
| **Persistência** | Cache de dados, histórico de relatórios gerados, resultados | SQLite |
| **Interface** | Selecionar jogo, disparar análise, ler relatório | Ver Seção 8 |

### 4.3 Stack confirmada

- **Backend / lógica:** Python.
- **Banco:** SQLite (simplicidade; o volume de dados de uma Copa não justifica nada maior).
- **Cérebro de IA:** API da Anthropic (chave fornecida pelos usuários), modelo Claude com ferramenta de busca web habilitada.
- **Validação de saída da IA:** `pydantic` — o JSON da IA é validado contra um schema antes de tocar o banco. (Seção 6.8.)
- **Prompt de síntese:** **artefato versionado no repositório** (`prompts/sintese_vN.md`), nunca string inline no código. Mudou o prompt = novo arquivo + bump de versão registrado no relatório (`prompt_versao`). É a peça mais sensível do sistema e precisa de histórico auditável.
- **Interface:** começar com Streamlit para ter o produto rodando rápido; migrar para FastAPI + front React apenas se o projeto evoluir e a empolgação justificar. **O valor está no pipeline de análise e na honestidade do relatório, não na beleza da interface** — a interface não deve consumir o tempo das primeiras fases.

### 4.4 Fontes de dados

| Fonte | Uso | Custo | Observação |
|---|---|---|---|
| **openfootball/worldcup.json** | Calendário 2026, grupos, resultados, histórico de Copas anteriores | Grátis, domínio público, sem chave | Espinha dorsal de fixtures e estrutura. Formato JSON limpo. |
| **Rating prior** (Elo próprio e/ou ranking público FIFA/SPI) | Força base de cada seleção, ancorando o modelo no jogo 1 e além | Grátis | Resolve cold start e a incomparabilidade entre confederações. Ver 7.1. |
| **API-Football (api-sports.io)** | Estatísticas de partida (escanteios, chutes, cartões, posse), forma recente | Plano grátis 100 req/dia | **Caveat crítico:** o plano grátis dá todos os endpoints **mas limita as temporadas disponíveis**, e amistosos têm cobertura de estatísticas inconsistente. Validar na Fase 1 quais dados de seleção realmente vêm no grátis antes de depender deles. |
| **Web search (via IA)** | Escalação provável, lesões, notícias, árbitro, contexto | Custo por uso da API Anthropic | Camada qualitativa. |

**Princípio de dados:** cachear tudo localmente no SQLite. Nunca repetir uma requisição cuja resposta não mudou. Dados históricos de Copas anteriores são imutáveis — puxar uma vez e guardar.

**Realismo sobre dados de seleção (importante):** seleções jogam pouco entre si e em competições com strength-of-schedule muito diferente entre confederações. Estatísticas granulares (escanteios/chutes/cartões) de seleção no plano grátis são esparsas. O sistema é projetado para **degradar com graça**: onde o dado existe, calcula; onde não existe, declara e rebaixa (2.4). Não force número onde só há vácuo.

---

## 5. Modelo de dados (SQLite)

Esquema conceitual. Os nomes finais ficam a critério da implementação, desde que a semântica seja preservada.

### 5.1 `times` (seleções)
- `id`, `nome`, `codigo_fifa`, `grupo`, `confederacao`, `rating_prior` (força base na escala comum), `rating_prior_atualizado_em`.

### 5.2 `jogos`
- `id`, `data`, `hora_utc`, `time_mandante_id`, `time_visitante_id`, `campo_neutro` (boolean — **true para a esmagadora maioria dos jogos da Copa**), `fase` (grupo / oitavas / etc.), `grupo`, `estadio`, `cidade`, `altitude_m`, `placar_mandante` (nullable até o jogo acontecer), `placar_visitante` (nullable).
- Nota: "mandante/visitante" é nominal em campo neutro e **não deve gerar vantagem de casa** (ver 7.1). A flag `campo_neutro` é o que o modelo consulta.

### 5.3 `estatisticas_jogo`
- Por jogo e por time: `gols`, `escanteios`, `chutes`, `chutes_no_alvo`, `faltas`, `cartoes_amarelos`, `cartoes_vermelhos`, `posse`, `xg` (nullable — **assumir majoritariamente ausente** para seleção no grátis; o modelo de gols não depende dele). Muitos campos nullable — a ausência é esperada e tratada.

### 5.4 `relatorios`
- `id`, `jogo_id`, `gerado_em` (timestamp), `prompt_versao`, `modelo_versao`, `conteudo` (o relatório completo), `fatores_avaliados` (JSON), `fatores_ausentes` (JSON — o que não pôde ser avaliado), `eh_relatorio_oficial` (boolean — ver semântica de re-run em 6.1/9.1).
- **Re-run:** relatórios são **append-only**. Rodar de novo cria um novo `relatorio` (escalação mudou, notícia nova). Apenas **um** relatório por jogo carrega `eh_relatorio_oficial = true`: o último gerado **antes do apito inicial**. É esse que conta para a validação da Seção 9.

### 5.5 `previsoes`
Tabela central. Uma linha por previsão de mercado dentro de um relatório.
- `id`, `relatorio_id`, `jogo_id`, `mercado` (ex.: "resultado", "total_gols", "escanteios", "cartoes_amarelos"), `entidade` (nullable — reservado para mercados individuais, fora do escopo v1), `previsao` (ex.: "+1.5", "vitória mandante"), `probabilidade_estimada` (0-1, nullable), `probabilidade_calculada_original` (0-1, nullable — o valor do modelo **antes** do ajuste qualitativo, para auditar a banda da 2.2), `incerteza` (baixa / média / alta), `origem` (calculado / qualitativo / híbrido), `justificativa` (texto), `fontes` (JSON de links/inputs), `gerado_em`.
- `resultado_real` (nullable — preenchido depois do jogo).
- ~~`acertou`~~ **removido como métrica** (contradiz a 9.3). Se um indicador binário for desejado **apenas para display**, deriva-se em tempo de leitura e **nunca** é usado para avaliar qualidade. A medida de qualidade é Brier/log-loss (9.3).

**Por que `previsoes` é central:** ela materializa o Princípio 2.2 (separação cálculo/qualitativo via `origem` + `probabilidade_calculada_original`), o 2.3 (rastreabilidade via `justificativa` + `fontes`), o 2.4 (incerteza explícita) e habilita a Seção 9 (validação via `resultado_real`).

---

## 6. O fluxo de análise, em detalhe

### 6.1 Entrada
Usuário seleciona um jogo (ex.: Brasil × Marrocos, Grupo C) e dispara a análise. O sistema gera um novo `relatorio` (append-only). Quando o jogo começa, o último relatório gerado antes do apito é marcado `eh_relatorio_oficial = true` — manual ou automaticamente via `hora_utc` do jogo.

### 6.2 Passo 1 — Coleta de dados duros
O sistema reúne, do cache ou das fontes:
- **Rating prior** de cada seleção (sempre disponível — resolve o cold start do jogo 1).
- Forma recente de cada seleção (últimos N jogos: resultados, gols pró/contra) **quando o free tier cobrir a temporada**.
- Forma **dentro da própria Copa** (crucial a partir da 2ª rodada: a análise do 2º jogo do Brasil muda conforme o resultado do 1º).
- Médias dos mercados secundários (escanteios, cartões, chutes, faltas) por seleção, **quando disponíveis** — caso contrário marcadas como ausentes (2.4).
- Head-to-head direto (com peso baixo — ver 6.6).
- Contexto físico do jogo: cidade, altitude, e — se calculável — distância/viagem desde o jogo anterior de cada seleção.

### 6.3 Passo 2 — Pesquisa qualitativa (web)
Buscas direcionadas via IA:
- Escalação provável e confirmações de última hora.
- Lesões, suspensões, retornos.
- Árbitro designado (determinante para cartões/faltas — ver 7).
- Notícias relevantes, clima interno, declarações.
- Situação de classificação no grupo (um time já classificado pode poupar titulares).
- Importância/motivação do jogo (vida ou morte vs. jogo decidido).

**Qualidade de fonte (operacional):** a IA deve preferir fontes primárias e veículos esportivos estabelecidos; tratar blog/rumor/fórum como sinal fraco e dizê-lo. Informação não confirmada (ex.: escalação "provável" de fonte fraca) **não rebaixa a confiança de forma silenciosa** — entra rotulada como incerta. Se nada confiável for encontrado para um fator, ele vai para `fatores_ausentes`.

### 6.4 Passo 3 — Modelo estatístico
- **Resultado e gols:** Dixon-Coles **ancorado no rating prior** (ver 7.1).
- **Mercados secundários:** distribuição apropriada por mercado a partir das médias (ver 7.2), quando há dados suficientes.

### 6.5 Passo 4 — Síntese por IA
A IA recebe **tudo**: o rating prior, os outputs do modelo, os dados duros, e o material de pesquisa. Seu trabalho:
1. Para cada mercado, decidir a previsão final fundindo número + contexto, **respeitando a regra de ajuste limitado (2.2)**: banda de ±10pp, ou rebaixar confiança, ou virar `qualitativo` puro.
2. Etiquetar a origem (calculado / qualitativo / híbrido) coerentemente com o ajuste feito.
3. Atribuir incerteza honesta (baixa / média / alta).
4. Escrever a justificativa rastreável.
5. **Listar explicitamente os fatores que não pôde avaliar** e rebaixar confiança conforme necessário.
6. Aplicar bom senso (2.5): não inventar profundidade sem base.
7. Emitir o resultado **no schema JSON estrito da Seção 6.8** — nada fora do schema.

### 6.6 Tratamento do head-to-head
Seleções se enfrentam muito pouco; o histórico direto é estatisticamente fraco. O sistema **usa, mas com peso baixo**, e a IA deve ser instruída a não supervalorizar ("o Brasil nunca perdeu pro Marrocos" quando foram 2 jogos em 20 anos não é sinal forte).

### 6.7 Passo 5 — Geração do relatório
Ver Seção 8.

### 6.8 Contrato de saída da IA (a interface mais crítica do sistema)
A síntese (6.5) **só** se comunica com o resto do sistema por um JSON estrito. Esta é a fronteira onde mais erros silenciosos nascem; por isso é especificada, validada e reparada.

**Schema (conceitual):**
```json
{
  "resumo_executivo": "string",
  "fatores_avaliados": ["string", ...],
  "fatores_ausentes": ["string", ...],
  "previsoes": [
    {
      "mercado": "resultado | total_gols | ambas_marcam | escanteios | cartoes_amarelos | faltas | chutes_time",
      "previsao": "string",
      "probabilidade_estimada": 0.0,                 // ou null
      "probabilidade_calculada_original": 0.0,       // ou null se origem=qualitativo
      "incerteza": "baixa | media | alta",
      "origem": "calculado | qualitativo | hibrido",
      "justificativa": "string",
      "fontes": ["url ou descrição de input", ...]
    }
  ]
}
```

**Regras de validação (rejeitar/reparar se violadas):**
- `mercado` deve estar no enum; mercado fora da lista = alucinação → rejeitar a linha.
- Se `origem = "calculado"`: `probabilidade_estimada == probabilidade_calculada_original`.
- Se `origem = "hibrido"`: ambos presentes e `|estimada − original| ≤ 0.10` (banda da 2.2). Fora da banda → forçar `origem = "qualitativo"` e zerar `probabilidade_calculada_original`.
- Se `origem = "qualitativo"`: `probabilidade_calculada_original` deve ser `null`.
- `probabilidade_estimada`, quando presente, ∈ [0,1].

**Manejo de falha:** se o JSON não parsear ou falhar no schema, o orquestrador faz **uma** tentativa de repair (reenvia à IA o erro de validação pedindo correção). Persistindo a falha, o relatório registra o erro e marca os mercados afetados como não-avaliáveis — **nunca grava dado malformado no banco**.

---

## 7. Especificação dos mercados

Para cada mercado: o que se calcula, o que se pesquisa, e como se expressa a previsão. **Todo mercado combina, quando possível, base numérica + leitura qualitativa** (Princípio 2.2), sempre com incerteza e justificativa.

### 7.1 Resultado (1X2) e total de gols — base predominantemente CALCULADA
- **Método:** Dixon-Coles **ancorado num rating prior**, não from scratch. Justificativa: seleções de confederações diferentes mal se enfrentam, então não existe um grafo de partidas conexo que permita estimar forças ofensiva/defensiva numa escala comum só com os jogos disponíveis — D-C puro sobre esse grafo produz números instáveis e incomparáveis entre confederações. O prior (Elo próprio e/ou ranking público) fornece a escala comum; o D-C ajusta a forma recente e a distribuição de placares em torno dela.
  - Concretamente: o prior entra como **força base** de ataque/defesa de cada seleção; os parâmetros do D-C são estimados/ajustados a partir dos jogos disponíveis **com regularização em direção ao prior** (priors informativos ou shrinkage), de modo que poucos jogos não façam a estimativa explodir.
  - Produz uma matriz de probabilidade de placares, da qual se derivam: vitória/empate/derrota, over/under gols (0.5, 1.5, 2.5, 3.5), ambas marcam, placar mais provável.
- **Vantagem de casa:** **zero para jogos em campo neutro** (`campo_neutro = true`, a maioria). Aplicar HA real **apenas** para Canadá, EUA e México quando jogarem em seu próprio país. Tratar HA fixo para todos os jogos injetaria viés em ~100 partidas.
- **Cold start (1ª rodada):** sem "forma na Copa", a previsão repousa quase só no prior + forma recente fora da Copa (quando disponível). O relatório deve **explicitar** essa dependência e tender a incerteza média.
- **Parâmetros a fixar no código (e versionar):** decaimento temporal (peso de jogos antigos), força do shrinkage em direção ao prior, janela de "forma recente".
- **Ajuste qualitativo (híbrido):** a IA pode ajustar dentro da banda da 2.2 (escalação poupada, lesão de artilheiro), **explicando o ajuste** e registrando o valor original.
- **Expressão:** probabilidade calculada + faixa de incerteza + nota qualitativa quando houver ajuste.

### 7.2 Escanteios, cartões, faltas, chutes (time) — base HÍBRIDA
- **Método numérico:** modelar cada um como distribuição (Poisson ou Binomial Negativa) a partir das médias das seleções. **Cartões e faltas dependem fortemente do árbitro** — incorporar o perfil disciplinar do árbitro designado quando conhecido.
- **Camada qualitativa:** estilo de jogo e confronto tático (time que cruza muito gera mais escanteios contra defesa que afasta de cabeça; pressão alta gera mais faltas; etc.).
- **Expressão:** preferencialmente como **faixa + probabilidade de linha** ("esperado 9-11 escanteios; ~60% de passar de 9.5"), não número cravado. Incerteza tende a média/alta.
- **Honestidade obrigatória:** se não há dados de médias daquela seleção (cenário **provável** no free tier — ver 4.4), a previsão é puramente qualitativa, etiquetada como tal, com incerteza alta — ou declarada como não-avaliável. Não inventar média a partir de nada.

### 7.3 Mercados de jogador (ex.: chutes do Vini Jr) — **FORA DO ESCOPO v1**
Movido para fora do escopo v1 por coerência com o Princípio 2.1. O próprio mercado é, hoje, o mais frágil do sistema:
- **Realidade:** dados individuais de seleção no plano grátis são fracos ou ausentes. Qualquer número aqui seria palpite com verniz de exatidão — exatamente o que 2.1 condena.
- **Decisão:** **não implementar no v1.** O campo `entidade` no schema fica reservado para uma futura v2, condicionada à existência de uma fonte de dados individual confiável. Se um usuário pedir um mercado de jogador, o sistema responde que está fora de escopo — não improvisa.

### 7.4 Fatores transversais que toda análise deve considerar
- **Viagem / fuso / altitude:** muito relevante nesta Copa (três países, distâncias continentais, Cidade do México a 2.240m). Time que jogou longe e voa para a altitude poucos dias antes tem desvantagem física real.
- **Árbitro:** o fator mais subestimado para cartões e faltas.
- **Rodízio/descanso:** time classificado pode poupar; destrói previsões baseadas na escalação ideal.
- **Importância do jogo:** o formato de 12 grupos cria muitos cenários de "jogo morto" na última rodada — detectar e ajustar intensidade esperada.
- **Confronto tático:** estilos que se anulam ou se potencializam.

---

## 8. O relatório (output)

### 8.1 Formato
- **Idioma:** português.
- **Formato técnico:** HTML standalone (renderiza bonito, abre em qualquer navegador, fácil de gerar e guardar). Markdown como alternativa leve se preferível em alguma fase.

### 8.2 Estrutura do relatório
1. **Cabeçalho:** jogo, fase, data/hora, estádio, cidade (e altitude/contexto físico se relevante), timestamp de geração, versão do prompt/modelo, e se é o relatório oficial.
2. **Resumo executivo:** o cenário do jogo em poucas linhas — a leitura geral da IA.
3. **Previsões por mercado:** para cada mercado, um bloco com: a previsão, a probabilidade estimada (quando aplicável), a faixa de incerteza, a **etiqueta de origem** (calculado / qualitativo / híbrido), e a justificativa. Quando híbrido, **mostrar o valor calculado original e o ajuste** (transparência da banda 2.2).
4. **Fatores considerados:** lista do que entrou na análise.
5. **Fatores NÃO avaliados:** lista explícita do que faltou (escalação não saiu, sem dados de escanteios, etc.) e como isso afetou a confiança. (Princípio 2.4.)
6. **Fontes:** links e inputs usados, para auditoria. (Princípio 2.3.)

### 8.3 Tratamento visual da incerteza
A incerteza deve ser **visualmente óbvia**, não escondida em letra miúda. Previsões de alta confiança e palpites frágeis não podem parecer a mesma coisa. Usar cor/etiqueta/posição para que o leitor distinga em um relance o que é sólido do que é especulativo. A etiqueta de origem também deve ser visualmente distinta (ex.: cálculo vs. qualitativo).

---

## 9. Validação e defesa contra data leakage

Esta seção existe porque o caso que inspirou o projeto (um vídeo que alegava 83-85% de acerto) foi, por admissão do próprio autor, resultado de **vazamento de dados** — features que embutiam o resultado. É o erro mais comum e mais traiçoeiro da área.

### 9.1 Regra de ouro
**Toda previsão é registrada e travada antes do apito inicial.** Nenhuma avaliação pode usar dado que só existiria depois ou por causa do jogo. O timestamp `gerado_em` em `previsoes`, combinado com `eh_relatorio_oficial` no relatório (o último antes do apito), é a prova de que a previsão precedeu o resultado. **Apenas previsões do relatório oficial entram na validação.**

### 9.2 Sinal de alarme
Se em qualquer validação a acurácia aparente passar de ~60% no acerto de resultado (1X2), **presumir leakage** e auditar, em vez de comemorar. Acurácia legítima de resultado em futebol vive na faixa de 50-55%.

### 9.3 Métrica honesta
Avaliar com **Brier score** e **log-loss**, não com "acertou/errou" binário. Se o sistema diz "70% Brasil" e o Brasil perde, isso não é necessariamente um erro — era esperado acontecer em 30% dos casos. A calibração das probabilidades ao longo de muitos jogos é a medida real de qualidade. **Não existe coluna `acertou` como métrica** (ver 5.5); qualquer indicador binário é só display.

### 9.4 Atualização de resultados (alimentar o ciclo)
Após cada jogo, o `resultado_real` das previsões é preenchido para (a) permitir avaliação de calibração e (b) alimentar a "forma na Copa" das próximas análises. Mecanismo: **automático via API-Football com fallback manual** — o sistema tenta puxar sozinho; se o dado estiver ausente ou atrasado, ele solicita ao usuário, que fornece quando possível.

### 9.5 Sobre "aprender com os erros" e o tamanho da amostra
Com ~104 jogos, não há volume para machine learning que realmente aprenda sem overfit. O que o sistema faz não é re-treino: é **calibração e tracking** — medir honestamente o quão bem calibradas estão as previsões e ajustar a postura de confiança.

**Aviso de ruído (importante):** Brier/log-loss sobre poucos jogos é estatisticamente barulhento. Nas primeiras rodadas os números de calibração **não significam quase nada** e não devem motivar mudanças no modelo. O painel de calibração (Fase 6) é **descritivo, não acionável no meio do torneio**. Gerenciar a expectativa: o sistema não vira um oráculo ao longo da Copa; ele se torna mais honesto sobre suas próprias incertezas.

---

## 10. Fases de implementação

Ordenadas por valor entregue / esforço. Cada fase produz algo funcional.

### Fase 0 — Validação de viabilidade de dados (curta, mas obrigatória)
- Registrar conta no API-Football e **verificar empiricamente** quais temporadas/competições de seleção o free tier expõe e se traz estatísticas de partida (escanteios/chutes/cartões) para jogos de seleção e amistosos.
- Decidir a fonte do rating prior (Elo próprio a partir do openfootball histórico vs. ranking público).
- **Entregável:** um documento curto dizendo exatamente quais dados o projeto pode contar como disponíveis. Isso define o quanto de 7.2 é calculável vs. qualitativo. **Não pular esta fase** — ela protege contra construir em cima de dados que não existem.

### Fase 1 — Fundação de dados
- Ingerir openfootball: calendário 2026, grupos, e históricos de Copas anteriores.
- Construir/ingerir o **rating prior** de cada seleção.
- Montar o SQLite com o esquema da Seção 5.
- Integrar API-Football com cache para forma recente e estatísticas (dentro do que a Fase 0 confirmou).
- **Entregável:** conseguir listar os jogos da Copa e, dado um jogo, reunir os dados duros disponíveis + o prior.

### Fase 2 — Motor estatístico
- Implementar Dixon-Coles **ancorado no prior** (shrinkage/regularização) para resultado e gols.
- Vantagem de casa parametrizada (zero em neutro; real para anfitriões).
- Implementar distribuições dos mercados secundários a partir de médias, onde houver dados.
- **Entregável:** dado um jogo, gerar as previsões puramente calculadas, com comportamento sensato no cold start.

### Fase 3 — Cérebro de IA, pesquisa e contrato de saída
- Integrar a API da Anthropic com web search.
- Escrever o **prompt de síntese versionado** (`prompts/sintese_v1.md`) que implementa os Princípios da Seção 2 (separação de origem, ajuste limitado, incerteza honesta, declaração do que não sabe, bom senso).
- Implementar o **validador de saída** (Seção 6.8): schema `pydantic`, regras da banda, repair de uma tentativa.
- **Eval mínima do prompt:** um punhado de jogos de teste com expectativas qualitativas (ex.: "se a escalação não saiu, deve aparecer em `fatores_ausentes`"), rodada a cada mudança de prompt.
- **Entregável:** o pipeline completo de [0] a [4], produzindo previsões validadas na tabela `previsoes`.

### Fase 4 — Relatório
- Gerar o HTML standalone com a estrutura da Seção 8, incluindo o tratamento visual da incerteza e da origem, e a exibição do ajuste híbrido (original → ajustado).
- **Entregável:** relatório legível e bonito por jogo.

### Fase 5 — Interface
- Streamlit: selecionar jogo, disparar análise, visualizar/guardar relatório, marcar o relatório oficial.
- **Entregável:** o produto utilizável de ponta a ponta pelo grupo.

### Fase 6 — Ciclo de validação
- Preencher `resultado_real` (automático + fallback manual).
- Calcular Brier score / log-loss acumulados **apenas sobre relatórios oficiais**.
- **Entregável:** painel honesto de calibração — descritivo, com aviso explícito de ruído nas primeiras rodadas.

---

## 11. Não-objetivos (fora de escopo)

Declarados explicitamente para impedir scope creep durante o desenvolvimento.

- **Não é um bolão / leaderboard.** A competição entre os amigos é manual e externa ao sistema.
- **Não é uma plataforma de apostas.** Não integra casas de aposta, não recomenda apostar dinheiro, não calcula valor esperado de apostas.
- **Não opera ao vivo.** Apenas análise pré-jogo. Sem acompanhamento minuto a minuto.
- **Não persegue acurácia máxima a qualquer custo.** Persegue honestidade e calibração. (Princípio 2.6.)
- **Não usa dados pagos.** Apenas fontes gratuitas + custo de uso da API da Anthropic.
- **Não é multiusuário com contas/login.** É uma ferramenta do grupo, rodada localmente.
- **Não faz mercados de jogador no v1.** (Ver 7.3.) Reservado para v2 condicionada a dados individuais confiáveis.
- **Não re-treina um modelo de ML.** Faz calibração e tracking, não aprendizado. (Ver 9.5.)

---

## 12. Riscos e mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| **Dixon-Coles puro instável** entre confederações sem grafo conexo | Alto | Ancorar no rating prior + shrinkage (7.1); prior resolve escala comum e cold start |
| **Data leakage** infla acurácia e cria falsa confiança | Alto | Seção 9 inteira; travamento via relatório oficial; alarme em >60% |
| IA gera precisão falsa em mercados qualitativos | Alto | Princípios 2.1/2.2; etiqueta de origem; **ajuste limitado a banda** + validador (6.8); faixas em vez de números cravados (7.2) |
| **Free tier do API-Football sem temporadas/stats de seleção** | Alto | **Fase 0** valida antes de construir; degradar com graça para qualitativo onde faltar (4.4) |
| Output da IA malformado/alucinado quebra o pipeline | Médio | Schema estrito + validação `pydantic` + repair de 1 tentativa; nunca grava malformado (6.8) |
| Vantagem de casa fantasma em ~100 jogos neutros | Médio | `campo_neutro` no schema; HA=0 em neutro, real só para anfitriões (7.1) |
| Limite de 100 req/dia da API-Football | Médio | Cache agressivo no SQLite; dados históricos puxados uma vez |
| Escalação não sai a tempo | Médio | Modo sob demanda perto do jogo; declarar "não avaliado" e rebaixar confiança (2.4) |
| Calibração ruidosa nas primeiras rodadas mal-interpretada | Médio | Aviso de ruído explícito (9.5); painel descritivo, não acionável no meio |
| Custo da API da Anthropic por análise | Baixo | Análise sob demanda (só roda o que o grupo quer ver) |
| Expectativa irreal de "90% de acerto" | Médio | Gestão de expectativa no produto; foco em calibração, não acurácia |

---

## 13. Glossário

- **Rating prior:** força base de cada seleção numa escala comum (Elo, ranking FIFA, SPI), usada para ancorar o modelo onde os jogos disponíveis não bastam — entre confederações e na 1ª rodada.
- **Dixon-Coles:** modelo estatístico para futebol que estende o Poisson, ajustando a frequência de placares baixos; aqui usado **ancorado no rating prior**, com regularização (shrinkage) para não explodir com poucos jogos.
- **Shrinkage / regularização:** puxar uma estimativa em direção a um valor de referência (o prior) quando há poucos dados, evitando estimativas instáveis.
- **Campo neutro:** jogo em que nenhuma das equipes joga em seu próprio país; não recebe vantagem de casa. Quase todos os jogos da Copa.
- **Data leakage (vazamento de dados):** quando o modelo usa, sem perceber, informação que só existe depois do evento previsto, inflando artificialmente a acurácia.
- **Brier score:** métrica de calibração de previsões probabilísticas; mede o quão próximas as probabilidades atribuídas ficaram dos resultados reais.
- **Log-loss:** outra métrica de calibração, penaliza fortemente previsões confiantes e erradas.
- **Origem (de uma previsão):** etiqueta que indica se a previsão veio de cálculo, de raciocínio qualitativo, ou de uma combinação (com ajuste limitado a uma banda).
- **Banda de ajuste:** o intervalo máximo (default ±10pp) dentro do qual a IA pode mover uma probabilidade calculada antes de a previsão ter de virar puramente qualitativa.
- **Relatório oficial:** o último relatório gerado antes do apito inicial de um jogo; o único que conta para a validação da Seção 9.
- **Mercado:** cada tipo de previsão sobre um jogo (resultado, total de gols, escanteios, etc.).

---

*Fim do PRD v1.1.*
