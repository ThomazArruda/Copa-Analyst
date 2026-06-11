# Copa Analyst — ingestão diária (Agendador de Tarefas do Windows)
# Roda: (1) atualizar resultados Copa 2026  (2) coletar stats (idempotente, 100 req/dia)
# Saída registrada em dados/logs/ingestao_diaria_<data>.log
#
# Registrar/alterar a tarefa: ver scripts/registrar_tarefa_diaria.ps1

$ErrorActionPreference = "Continue"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

$py = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

$logDir = Join-Path $raiz "dados\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force $logDir | Out-Null }
$log = Join-Path $logDir ("ingestao_diaria_{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

function Log($msg) { "$((Get-Date).ToString('s'))  $msg" | Tee-Object -FilePath $log -Append }

Log "=== Ingestão diária iniciada ==="

Log "--- atualizar resultados Copa 2026 ---"
& $py -m src.dados.ingestao atualizar *>> $log

Log "--- coletar stats (API-Football, cache-first, aborta ao bater 100/dia) ---"
& $py -m src.dados.ingestao stats *>> $log

Log "--- jogos recentes / amistosos (TheSportsDB) ---"
& $py -m src.dados.ingestao recentes *>> $log

Log "=== Ingestão diária concluída ==="
