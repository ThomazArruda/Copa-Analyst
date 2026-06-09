# Deploy fixo (nuvem) — Copa Analyst

Deploy de um único container (FastAPI serve API + UI) com **dados persistentes**
e **senha de acesso**. Grupo fechado (você + parceiro), IA real.

## O que já está pronto no repo

- `Dockerfile` — build do front (Node) + runtime Python num só container.
- `.dockerignore` — mantém a imagem enxuta, embarca o banco-semente.
- `deploy/seed_db/copa_analyst.db` — banco-semente (5,5 MB) copiado para o
  volume no 1º boot (startup `_semear_banco`). Depois, os dados vivem no volume.
- Auth Basic (`APP_USER`/`APP_PASSWORD`) — ativa só se `APP_PASSWORD` existir.
- `COPA_DB_PATH=/data/copa_analyst.db` — caminho no volume persistente.

## Variáveis de ambiente (secrets no host)

| Var | Obrigatória | Observação |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | IA real (síntese + pesquisa) |
| `API_FOOTBALL_KEY` | ✅ | stats (100 req/dia) |
| `APP_PASSWORD` | ✅ (deploy) | senha de acesso; sem ela o site fica aberto |
| `APP_USER` | — | default `copa` |
| `CLAUDE_MODEL` | — | default `claude-sonnet-4-6` |
| `RESEND_API_KEY`, `EMAIL_*` | — | só se quiser email diário |
| `COPA_DB_PATH` | — | já definido na imagem (`/data/...`) |

> O volume **tem que** ser montado em `/data` para o banco persistir entre deploys.

---

## Opção A — Render (dashboard, ~US$7/mês pelo disco persistente)

1. Render → **New → Web Service** → conectar o repo `ThomazArruda/Copa-Analyst`.
2. **Runtime: Docker** (usa o `Dockerfile` da raiz).
3. **Instance Type: Starter** (o free não tem disco persistente).
4. **Disks → Add Disk:** mount path `/data`, 1 GB.
5. **Environment:** adicionar os secrets da tabela acima (`APP_PASSWORD`, chaves).
6. Deploy. URL fica `https://<nome>.onrender.com`.

## Opção B — Fly.io (volume grátis, precisa do CLI + cartão no cadastro)

```bash
# instalar flyctl e logar (abre o navegador)
fly auth login
fly launch --no-deploy           # detecta o Dockerfile; cria fly.toml
fly volumes create dados --size 1 --region gru   # volume persistente (São Paulo)
# montar o volume em /data no fly.toml: [mounts] source="dados" destination="/data"
fly secrets set ANTHROPIC_API_KEY=... API_FOOTBALL_KEY=... APP_PASSWORD=...
fly deploy
```
URL fica `https://<app>.fly.dev`.

---

## Pós-deploy

- Abrir a URL → o navegador pede usuário/senha (`APP_USER`/`APP_PASSWORD`).
- "Atualizar Dados" puxa resultados; gerar relatório usa IA real (gasta créditos).
- A ingestão diária agendada (`CopaAnalyst-IngestaoDiaria`) é **local** (Windows);
  na nuvem, use o botão "Atualizar Dados" ou configure um cron do host.

## Atualizar o deploy

`git push` na branch conectada → o host rebuilda. O volume `/data` preserva os
dados; o banco-semente só é usado quando o volume está vazio.
