# Prompt de Síntese Copa Analyst — v1

**Versão:** 1
**Status:** Rascunho — preencher na Fase 3
**Última mudança:** 2026-06-04

---

## Contexto para a IA

Este arquivo é um **artefato versionado**. Ele define o comportamento do modelo de IA na etapa de síntese do pipeline Copa Analyst. **Nunca** colocar este conteúdo como string inline no código Python — sempre carregar deste arquivo.

Regras de manutenção:
- Toda mudança de conteúdo = novo arquivo `sintese_v2.md` (não editar este)
- A versão do prompt (`prompt_versao = "v1"`) é registrada em todo relatório gerado
- Rodar a eval mínima após qualquer mudança

---

## Prompt do Sistema

> **TODO (Fase 3):** escrever o prompt completo aqui.
>
> O prompt deve implementar, de forma explícita e testável, os seguintes requisitos do PRD:
>
> - **Princípio 2.1** — Honestidade epistêmica: nunca emitir número mais preciso do que a base sustenta
> - **Princípio 2.2** — Regra de ajuste limitado:
>   - Híbrido: mover dentro de ±10pp, registrar original + ajustado + motivo
>   - Fora da banda: rebaixar para `qualitativo` e zerar `probabilidade_calculada_original`
>   - Rebaixar `incerteza` como alternativa ao ajuste numérico
> - **Princípio 2.3** — Rastreabilidade: toda afirmação com fonte ou input rastreável
> - **Princípio 2.4** — Declarar o que não sabe: `fatores_ausentes` **obrigatório**, não opcional
> - **Princípio 2.5** — Bom senso: não forçar profundidade sem dados; profundidade real onde há base
> - **Seção 6.6** — Head-to-head com peso baixo: 2 jogos em 20 anos não é sinal forte
> - **Seção 6.8** — Output **apenas** no schema JSON estrito abaixo; nada fora do schema
>
> Inputs que o prompt receberá:
> - Rating prior de cada seleção
> - Previsões calculadas (Dixon-Coles) para resultado, gols, mercados secundários
> - Dados duros: forma recente, head-to-head, contexto físico (altitude, viagem)
> - Material de pesquisa: escalação, lesões, árbitro, notícias, situação no grupo
> - Lista de fatores que **não** foram possíveis de avaliar (do pipeline de dados)
> - Parâmetros do modelo usados (decaimento, shrinkage, janela)

---

## Schema JSON de Saída (invariante — não mudar sem bumpar versão)

```json
{
  "resumo_executivo": "string",
  "fatores_avaliados": ["string"],
  "fatores_ausentes": ["string"],
  "previsoes": [
    {
      "mercado": "resultado | total_gols | ambas_marcam | escanteios | cartoes_amarelos | faltas | chutes_time",
      "previsao": "string",
      "probabilidade_estimada": 0.0,
      "probabilidade_calculada_original": 0.0,
      "incerteza": "baixa | media | alta",
      "origem": "calculado | qualitativo | hibrido",
      "justificativa": "string",
      "fontes": ["url ou descrição do input"]
    }
  ]
}
```

**Regras que o validador (`src/ia/validacao.py`) vai enforce:**
- `mercado` deve ser do enum — fora = alucinação, linha rejeitada
- `origem = "calculado"` → `probabilidade_estimada == probabilidade_calculada_original`
- `origem = "hibrido"` → ambos presentes, `|estimada − original| ≤ 0.10`
- `origem = "qualitativo"` → `probabilidade_calculada_original` é null
- `probabilidade_estimada` ∈ [0,1] quando presente
- `fatores_ausentes` não pode ser array vazio se algum dado estava ausente

---

## Eval Mínima

Rodar após **toda** mudança de prompt. Casos esperados:

| Cenário | Expectativa |
|---|---|
| Escalação não disponível | Aparece em `fatores_ausentes`; `incerteza` rebaixada nos mercados afetados |
| Sem dados de escanteios da seleção A | Escanteios aparecem em `fatores_ausentes` ou com `origem = "qualitativo"` e `incerteza = "alta"` |
| Ajuste qualitativo > 10pp sugerido pela IA | `origem` deve ser `"qualitativo"`, não `"hibrido"`; `probabilidade_calculada_original` deve ser null |
| Árbitro desconhecido | Cartões/faltas com `incerteza` elevada; árbitro em `fatores_ausentes` |
| 1ª rodada (cold start) | Relatório explicita dependência do prior; `incerteza` geral não é `"baixa"` |
| Head-to-head de 2 jogos em 20 anos | Não deve aparecer como sinal forte na `justificativa` |
