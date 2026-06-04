# Copa Analyst — Sistema de Análise Preditiva · Copa do Mundo 2026

## Visão do Projeto

Ferramenta de análise pré-jogo para um grupo de amigos que cobre a Copa do Mundo 2026. O sistema combina um modelo estatístico (Dixon-Coles ancorado num rating prior) com pesquisa qualitativa via IA para gerar um relatório por partida, com previsões para múltiplos mercados, cada uma com probabilidade estimada, nível de incerteza, origem (calculado / qualitativo / híbrido) e justificativa rastreável.

**Não é** uma plataforma de apostas, bolão, ou ferramenta ao vivo. É uma ferramenta de análise pré-jogo rodada localmente.

## Fonte única de verdade

O PRD está em `PRD_Copa_Analyst_v1.1.md`. Toda decisão de implementação deve ser rastreável a uma seção dele. Se surgir uma dúvida que o PRD não responde, **atualizar o PRD antes de improvisar no código**.

---

## Stack Técnica

| Camada | Tecnologia |
|---|---|
| Backend / lógica | Python 3.12+ |
| Banco | SQLite (via `sqlite3` nativo) |
| IA / pesquisa | API da Anthropic — Claude com web search habilitado |
| Validação de saída da IA | `pydantic` v2 |
| Motor estatístico | `numpy`, `scipy`, `statsmodels` |
| Interface | Streamlit (MVP) |
| Gerenciamento de env | `python-dotenv` |

---

## Arquitetura do Pipeline

```
[0] RATING PRIOR GLOBAL        → src/modelos/rating_prior.py
      ↓
[1] COLETA DE DADOS DUROS      → src/dados/ingestao.py + cache SQLite
      ↓
[2] PESQUISA QUALITATIVA       → src/ia/pesquisa.py (Claude + web search)
      ↓
[3] MODELO ESTATÍSTICO         → src/modelos/dixon_coles.py + mercados.py
      ↓
[4] SÍNTESE POR IA             → src/ia/sintese.py + src/ia/validacao.py
      ↓
[5] RELATÓRIO HTML             → src/relatorio/gerador.py
      ↓
[6] INTERFACE STREAMLIT        → src/interface/app.py
```

---

## Estrutura de Arquivos

```
copa-analyst/
  PRD_Copa_Analyst_v1.1.md      ← Fonte única de verdade do produto
  CLAUDE.md                     ← Este arquivo
  README.md                     ← Como rodar o projeto
  .env.example                  ← Template de variáveis de ambiente
  docs/
    ROADMAP.md                  ← Fases de implementação com contexto de urgência
    DECISIONS.md                ← Decisões arquiteturais e pendências
  src/
    dados/
      ingestao.py               ← openfootball + API-Football (cache-first)
      openfootball.py           ← Parser específico do openfootball/worldcup
      api_football.py           ← Cliente API-Football com rate limiting
    modelos/
      rating_prior.py           ← Elo próprio OU ingestão de ranking público
      dixon_coles.py            ← D-C ancorado no prior + shrinkage
      mercados.py               ← Distribuições para escanteios, cartões, etc.
    ia/
      pesquisa.py               ← Buscas web dirigidas via Claude
      sintese.py                ← Orquestrador: monta prompt, chama IA, valida
      validacao.py              ← Schema pydantic + regras da banda (2.2 do PRD)
    relatorio/
      gerador.py                ← HTML standalone por jogo
      template.html             ← Template do relatório
    interface/
      app.py                    ← Streamlit: selecionar jogo, disparar, ler
    db/
      schema.sql                ← DDL do SQLite
      repositorio.py            ← Toda a leitura/escrita no banco (nunca direto)
  prompts/
    sintese_v1.md               ← Prompt de síntese — ARTEFATO VERSIONADO
  dados/
    copa_analyst.db             ← SQLite (gitignored)
    cache/                      ← Respostas cacheadas da API-Football (gitignored)
```

---

## Princípios Inegociáveis (do PRD Seção 2)

Antes de implementar qualquer coisa, entender estes princípios. Eles têm **precedência sobre qualquer decisão de implementação**.

### 2.1 Honestidade epistêmica
O maior risco não é errar — é soar confiante sobre coisas que são estimativas frágeis. **Nunca** emitir um número que pareça mais preciso do que a base que o sustenta.

### 2.2 Separação cálculo / qualitativo + ajuste limitado
Toda previsão carrega uma etiqueta: `calculado`, `qualitativo` ou `híbrido`. Quando híbrido, a IA só pode:
1. Mover a probabilidade dentro de **±10 pontos percentuais** (banda fixa no código)
2. Rebaixar a confiança (subir `incerteza`) sem mudar o número
3. Virar `qualitativo` puro — aí perde o número calculado

Fora da banda → forçar `qualitativo`. **Nunca** deixar palpite herdar aparência de cálculo.

### 2.3 Rastreabilidade total
Cada previsão carrega: o número do cálculo com seus inputs, ou o raciocínio + fontes da IA. Nenhuma caixa-preta.

### 2.4 Declarar o que não sabe
Se a escalação não saiu, sem dados de escanteios, fonte fraca → o relatório diz isso e rebaixa confiança. `fatores_ausentes` é obrigatório.

### 2.6 Calibração, não acurácia inflada
Meta ~50-55% no acerto de resultado. Se aparecer >60%, **presumir data leakage** e auditar.

---

## Modelo de Dados Chave

Ver PRD Seção 5 para o schema completo. Tabelas centrais:

- **`times`** — seleções com `rating_prior` (escala comum)
- **`jogos`** — com flag `campo_neutro` (true para ~100 dos 104 jogos)
- **`estatisticas_jogo`** — muitos campos nullable; ausência é esperada
- **`relatorios`** — append-only; `eh_relatorio_oficial = true` apenas no último antes do apito
- **`previsoes`** — tabela central; `probabilidade_calculada_original` preservado para auditoria da banda

---

## Contrato de Saída da IA (crítico)

A IA só se comunica via JSON estrito validado por pydantic. Ver PRD Seção 6.8 e `src/ia/validacao.py`.

**Regras que o validador enforce:**
- `mercado` deve ser do enum — fora = alucinação, rejeitar linha
- `origem = "calculado"` → `probabilidade_estimada == probabilidade_calculada_original`
- `origem = "hibrido"` → ambos presentes, `|estimada − original| ≤ 0.10`
- `origem = "qualitativo"` → `probabilidade_calculada_original` é null
- Probabilidade ∈ [0,1] quando presente

Falha no parse → **uma** tentativa de repair → persistindo, registrar erro, marcar mercados como não-avaliáveis. **Nunca gravar dado malformado no banco.**

---

## Prompt de Síntese

`prompts/sintese_v1.md` é o artefato mais sensível do sistema. Regras:
- **Nunca** colocar o prompt como string inline no código Python
- Mudança de prompt = novo arquivo (`sintese_v2.md`) + bump de versão
- A versão do prompt é registrada em todo relatório gerado (`prompt_versao`)
- Rodar a eval mínima a cada mudança (ver `docs/ROADMAP.md` Fase 3)

---

## Variáveis de Ambiente

```bash
# Obrigatória
ANTHROPIC_API_KEY=sk-ant-...

# Opcional (development)
API_FOOTBALL_KEY=...         # Free tier: 100 req/dia — cacheie tudo
MOCK_AI=true                 # Pula chamadas à API Anthropic durante dev de UI

# Configuração do modelo
COPA_DB_PATH=dados/copa_analyst.db
COPA_BAND_PP=0.10            # Banda de ajuste qualitativo (default 10pp, PRD 2.2)
```

---

## Regras de Desenvolvimento

### Cache agressivo (obrigatório)
- Dados históricos de Copas anteriores → imutáveis, puxar uma vez
- API-Football: **toda resposta** vai ao SQLite cache antes de qualquer processamento
- Nunca repetir requisição cuja resposta não mudou
- Limite: 100 req/dia no free tier — esgotar o limite é um bug

### Vantagem de casa
- `campo_neutro = true` → **HA = 0 no modelo**, sem exceção
- HA real apenas quando Canadá, EUA ou México jogam em casa
- A flag `campo_neutro` é o que o código consulta — não inferir do nome do time

### Cold start (1ª rodada)
- Sem "forma na Copa" → previsão repousa no prior + forma recente fora da Copa
- O relatório deve **explicitar** essa dependência
- Incerteza default: **média** na 1ª rodada

### Data leakage (regra de ouro)
- Toda previsão travada com timestamp **antes do apito inicial**
- Apenas relatório com `eh_relatorio_oficial = true` entra na validação da Seção 9
- Se acurácia de resultado > 60% → auditar, não comemorar

### Mercados de jogador
- **Fora do escopo v1** — se solicitado, o sistema responde que está fora de escopo
- Campo `entidade` reservado para v2

---

## Fluxo de Trabalho Claude Code

### Para toda fase nova
```
/gsd:discuss-phase N    → travar decisões antes de escrever código
/gsd:plan-phase N       → criar plano atômico com research
/gsd:execute-phase N    → executar em waves com commits atômicos
/gsd:verify-work N      → validar entregáveis
```

### Para tarefas pequenas (bug, ajuste de prompt, tweaks)
```
/gsd:quick
```

### Antes de qualquer mudança no modelo estatístico
1. Ler `docs/DECISIONS.md` — verificar decisões pendentes sobre rating prior
2. Confirmar que `campo_neutro` está sendo respeitado
3. Versionar qualquer mudança de parâmetro (decaimento, shrinkage, janela de forma)

---

## Contexto de Urgência

A Copa começa em **11 de junho de 2026**. O pipeline (Fases 0–5) precisa estar funcional para o Jogo 1. Ver `docs/ROADMAP.md` para priorização.
