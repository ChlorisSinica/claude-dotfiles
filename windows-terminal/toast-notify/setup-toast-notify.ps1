param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("enable", "disable")]
    [string]$Mode,
    [Parameter(Mandatory = $true)]
    [string]$TargetDir
)

$ErrorActionPreference = "Stop"

function Ensure-Property {
    param(
        [Parameter(Mandatory = $true)]
        $Object,
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        $Value
    )

    if (-not $Object.PSObject.Properties[$Name]) {
        $Object | Add-Member -MemberType NoteProperty -Name $Name -Value $Value
    }
}

function Remove-ManagedHandlers {
    param(
        [object[]]$Groups,
        [Parameter(Mandatory = $true)]
        [string]$ManagedCommand
    )

    $result = @()
    foreach ($group in @($Groups)) {
        $handlers = @()
        foreach ($handler in @($group.hooks)) {
            if ($handler.command -ne $ManagedCommand) {
                $handlers += $handler
            }
        }

        if ($handlers.Count -gt 0) {
            $group.hooks = @($handlers)
            $result += $group
        }
    }

    return @($result)
}

function Ensure-HandlerGroup {
    param(
        [object[]]$Groups,
        [Parameter(Mandatory = $true)]
        [string]$Matcher,
        [Parameter(Mandatory = $true)]
        $Handler
    )

    $result = @($Groups)
    $existing = $null
    foreach ($group in $result) {
        if ($group.matcher -eq $Matcher) {
            $existing = $group
            break
        }
    }

    if ($null -eq $existing) {
        $existing = [PSCustomObject]@{
            matcher = $Matcher
            hooks = @()
        }
        $result += $existing
    }

    $alreadyPresent = $false
    foreach ($handler in @($existing.hooks)) {
        if ($handler.command -eq $Handler.command) {
            $alreadyPresent = $true
            break
        }
    }

    if (-not $alreadyPresent) {
        $existing.hooks = @($existing.hooks) + $Handler
    }

    return @($result)
}

function Register-ToastProtocol {
    $protocolRoot = "HKCU:\Software\Classes\claude-dotfiles-toast"
    $commandKey = Join-Path $protocolRoot "shell\open\command"
    $launcher = Join-Path $PSScriptRoot "invoke-toast-target.ps1"
    $powershellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $commandValue = ('"{0}" -NoProfile -ExecutionPolicy Bypass -File "{1}" "%1"' -f $powershellExe, $launcher)

    New-Item -Path $protocolRoot -Force | Out-Null
    New-Item -Path $commandKey -Force | Out-Null
    Set-Item -Path $protocolRoot -Value "URL:Claude Dotfiles Toast"
    Set-ItemProperty -Path $protocolRoot -Name "URL Protocol" -Value ""
    Set-Item -Path $commandKey -Value $commandValue
}

$projectDir = (Resolve-Path -LiteralPath $TargetDir).Path
$claudeDir = Join-Path $projectDir ".claude"
$hooksDir = Join-Path $claudeDir "hooks"
$settingsPath = Join-Path $claudeDir "settings.json"
$backupPath = Join-Path $claudeDir "settings.toast-notify.bak.json"
$notifySource = Join-Path $PSScriptRoot "notify-toast.ps1"
$managedCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".claude/hooks/notify-toast.ps1"'
$managedHandler = [PSCustomObject]@{
    type = "command"
    command = $managedCommand
    timeout = 10
}

New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null

if (Test-Path -LiteralPath $settingsPath) {
    Copy-Item -LiteralPath $settingsPath -Destination $backupPath -Force
    $settings = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
} else {
    $settings = [PSCustomObject]@{}
}

Ensure-Property -Object $settings -Name "hooks" -Value ([PSCustomObject]@{})

if ($settings.hooks.PSObject.Properties["Notification"]) {
    $settings.hooks.Notification = @(Remove-ManagedHandlers -Groups $settings.hooks.Notification -ManagedCommand $managedCommand)
}
if ($settings.hooks.PSObject.Properties["Stop"]) {
    $settings.hooks.Stop = @(Remove-ManagedHandlers -Groups $settings.hooks.Stop -ManagedCommand $managedCommand)
}

if ($Mode -eq "enable") {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
    Copy-Item -LiteralPath $notifySource -Destination (Join-Path $hooksDir "notify-toast.ps1") -Force
    Register-ToastProtocol

    if (-not $settings.hooks.PSObject.Properties["Notification"]) {
        $settings.hooks | Add-Member -MemberType NoteProperty -Name "Notification" -Value @()
    }
    if (-not $settings.hooks.PSObject.Properties["Stop"]) {
        $settings.hooks | Add-Member -MemberType NoteProperty -Name "Stop" -Value @()
    }

    $settings.hooks.Notification = @(Ensure-HandlerGroup -Groups $settings.hooks.Notification -Matcher "permission_prompt" -Handler $managedHandler)
    $settings.hooks.Notification = @(Ensure-HandlerGroup -Groups $settings.hooks.Notification -Matcher "idle_prompt" -Handler $managedHandler)
    $settings.hooks.Stop = @(Ensure-HandlerGroup -Groups $settings.hooks.Stop -Matcher "*" -Handler $managedHandler)
} else {
    if ($settings.hooks.PSObject.Properties["Notification"] -and @($settings.hooks.Notification).Count -eq 0) {
        $settings.hooks.PSObject.Properties.Remove("Notification")
    }
    if ($settings.hooks.PSObject.Properties["Stop"] -and @($settings.hooks.Stop).Count -eq 0) {
        $settings.hooks.PSObject.Properties.Remove("Stop")
    }
}

if ($settings.hooks.PSObject.Properties.Count -eq 0) {
    $settings.PSObject.Properties.Remove("hooks")
}

$settings | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $settingsPath -Encoding UTF8
Write-Host (" [+] settings.json updated for mode: " + $Mode) -ForegroundColor Cyan
if ($Mode -eq "enable") {
    Write-Host " [+] Toast protocol registered for the current user." -ForegroundColor Cyan
}
