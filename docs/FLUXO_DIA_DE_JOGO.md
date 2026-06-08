# Fluxo do Dia de Jogo — operação + anti-leakage

Guia operacional para rodar o Copa Analyst em cada dia de jogo, garantindo a
**defesa contra data leakage** do PRD Seção 9. A regra de ouro: para cada jogo,
o relatório **oficial** tem de ser o último gerado **antes do apito inicial**.

---

## Por que isso importa (PRD 9.1)

A validação de calibração (Brier/log-loss) só usa relatórios marcados como
`eh_relatorio_oficial = 1`. Se um relatório gerado **depois** do apito (ou pior,
depois do fim do jogo) for marcado como oficial, ele pode embutir informação do
resultado → **data leakage**, que infla artificialmente a acurácia (PRD 9.2).

O par `(gerado_em < kickoff)` é a prova de que a previsão precedeu o resultado.

---

## Salvaguardas no código

- **`marcar_oficial_seguro`** (`src/relatorio/oficial.py`) e o endpoint
  `POST /api/relatorios/{id}/marcar-oficial` **recusam** marcar como oficial um
  relatório cujo `gerado_em` é posterior ao apito. O frontend mostra o motivo.
- **`marcar_oficiais_automatico`** varre os jogos que já começaram e fixa, para
  cada um, o último relatório gerado antes do apito. Idempotente.
- O apito (kickoff) é calculado de `data` + `hora_utc` (UTC) do jogo.

---

## Passo a passo (por jogo)

### Antes do apito

1. **Atualizar resultados/forma** (puxa jogos já encerrados via TheSportsDB):
   ```bash
   python -m src.dados.ingestao atualizar
   ```
2. **Gerar a análise** o mais perto possível do apito (para pegar escalação e
   notícias de última hora) — pela UI (página "Relatório IA" → "Gerar análise")
   ou pelo backend. Pode rodar várias vezes; cada execução cria um novo relatório
   (append-only). ⚠️ Cada relatório leva ~2–3 min por causa do rate limit da API
   Anthropic (ver memória do projeto / `docs/PLANO_PRE_COPA.md`).
3. **Marcar como oficial** o último relatório gerado antes do apito:
   - Pela UI: botão "Marcar como oficial".
   - Em lote, para todos os jogos do dia que já começaram:
     ```bash
     python -m src.relatorio.oficial auto 2026-06-11
     ```
   - Sem argumento de data, processa todos os jogos já iniciados:
     ```bash
     python -m src.relatorio.oficial auto
     ```

> Se tentar marcar oficial um relatório gerado **após** o apito, o sistema recusa
> e explica o motivo — isso é proposital (anti-leakage).

### Depois do jogo

4. **Puxar o placar** (alimenta `resultado_real` e a forma das próximas análises):
   ```bash
   python -m src.dados.ingestao atualizar
   ```
5. **Conferir a calibração** (apenas relatórios oficiais entram):
   - UI: página "Calibração", ou `GET /api/calibracao`.
   - Lembrete do PRD 9.5: com poucos jogos, Brier/log-loss são **barulhentos** e
     **não devem motivar mudanças no modelo**. O painel é descritivo.

---

## Automação da ingestão diária

A coleta de dados (resultados + stats) roda **automaticamente todo dia** via Agendador
de Tarefas do Windows. Tarefa: `CopaAnalyst-IngestaoDiaria` (padrão 09:00), que executa
`scripts/ingestao_diaria.ps1` → `ingestao atualizar` + `ingestao stats`. Logs em
`dados/logs/ingestao_diaria_<data>.log`.

```powershell
# Registrar / alterar horário
powershell -ExecutionPolicy Bypass -File scripts\registrar_tarefa_diaria.ps1 -Hora 09:00
# Conferir
Get-ScheduledTask -TaskName "CopaAnalyst-IngestaoDiaria"
# Rodar manualmente agora
Start-ScheduledTask -TaskName "CopaAnalyst-IngestaoDiaria"
# Remover
Unregister-ScheduledTask -TaskName "CopaAnalyst-IngestaoDiaria" -Confirm:$false
```

> A tarefa diária NÃO re-scrapeia Wikipedia/openfootball (dados estáticos). Para
> reconstruir tudo do zero, rode `python -m src.dados.ingestao inicial` manualmente.

## Rotina recomendada de um dia com vários jogos

| Quando | Ação |
|---|---|
| Automático (09:00) | Tarefa agendada: resultados + stats (respeita 100 req/dia) |
| ~1–2h antes de cada jogo | Gerar análise pela UI (escalação fresca) |
| Logo antes do apito | Marcar oficial (UI) **ou** `python -m src.relatorio.oficial auto <data>` |
| Após cada jogo | `python -m src.dados.ingestao atualizar` (ou esperar a tarefa do dia seguinte) |
| Fim do dia | Conferir página de Calibração |

---

## Comandos de referência

```bash
# Anti-leakage / relatório oficial
python -m src.relatorio.oficial auto [YYYY-MM-DD]   # fixa oficiais dos jogos já iniciados
python -m src.relatorio.oficial check <relatorio_id> # verifica se pode ser oficial

# Dados
python -m src.dados.ingestao atualizar              # resultados Copa 2026 (TheSportsDB)
python -m src.dados.ingestao stats                  # só stats (API-Football, cache-first) — usado na tarefa diária
python -m src.dados.ingestao inicial                # ingestão completa (re-scrape Wikipedia/openfootball + Elo + stats)
python -m src.dados.ingestao listar                 # lista jogos Copa 2026
```
