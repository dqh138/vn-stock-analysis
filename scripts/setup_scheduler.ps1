# Setup Windows Task Scheduler - chạy script một lần để tạo task
# Chạy bằng: PowerShell -ExecutionPolicy Bypass -File scripts\setup_scheduler.ps1

$scriptPath = "$PSScriptRoot\run_price_update.bat"
$taskName = "VNStockPriceUpdate"

$action = New-ScheduledTaskAction -Execute $scriptPath

# Chạy Thứ 2 - Thứ 6 lúc 16:30
$trigger = New-ScheduledTaskTrigger -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "16:30"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Cap nhat gia co phieu VN moi ngay luc 16:30" `
    -Force

Write-Host "Task '$taskName' da duoc tao thanh cong!"
Write-Host "Kiem tra tai: Task Scheduler > VNStockPriceUpdate"
