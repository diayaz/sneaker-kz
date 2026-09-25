# Регистрирует ежедневный запуск в Планировщике задач Windows для текущего пользователя.
#   powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1 [-Time 07:00]
# Удалить: Unregister-ScheduledTask -TaskName "SneakerKZ Daily" -Confirm:$false
param(
    [string]$Time = "07:00",
    [string]$TaskName = "SneakerKZ Daily"
)
$ErrorActionPreference = "Stop"
$script = Resolve-Path (Join-Path $PSScriptRoot "daily.ps1")

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Sneaker KZ: курсы Нацбанка РК и обновление цен магазинов" -Force | Out-Null

Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo | Select-Object TaskName, NextRunTime
