# Copa Analyst — registra a tarefa agendada de ingestão diária (Windows).
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\registrar_tarefa_diaria.ps1            # 09:00 (padrão)
#   powershell -ExecutionPolicy Bypass -File scripts\registrar_tarefa_diaria.ps1 -Hora 08:30
# Remover:
#   Unregister-ScheduledTask -TaskName "CopaAnalyst-IngestaoDiaria" -Confirm:$false

param(
    [string]$Hora = "09:00",
    [string]$NomeTarefa = "CopaAnalyst-IngestaoDiaria"
)

$raiz   = Split-Path -Parent $PSScriptRoot
$script = Join-Path $raiz "scripts\ingestao_diaria.ps1"

if (-not (Test-Path $script)) { throw "Script não encontrado: $script" }

$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument ("-NoProfile -ExecutionPolicy Bypass -File `"{0}`"" -f $script)
$trigger = New-ScheduledTaskTrigger -Daily -At $Hora
# StartWhenAvailable: se a máquina estava desligada na hora, roda assim que possível (não perde o dia)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $NomeTarefa -Action $action -Trigger $trigger `
    -Settings $settings -Description "Copa Analyst: atualizar resultados + coletar stats (100 req/dia)" -Force | Out-Null

Write-Output "Tarefa '$NomeTarefa' registrada para rodar diariamente às $Hora."
Write-Output "Ver: Get-ScheduledTask -TaskName '$NomeTarefa'"
