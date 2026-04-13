$ErrorActionPreference = "Stop"

function Write-ToastLog {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    try {
        $logDir = Join-Path ".claude" "logs"
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        $logPath = Join-Path $logDir "toast-notify.log"
        $timestamp = (Get-Date).ToString("o")
        Add-Content -LiteralPath $logPath -Value "$timestamp $Message"
    } catch {
        # Best effort only; notification failures must not break Claude Code hooks.
    }
}

function Read-HookInput {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return $null
    }
    return $raw | ConvertFrom-Json
}

function Get-FolderLabel {
    param([string]$PathValue)

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return "Unknown Folder"
    }

    $trimmed = $PathValue.TrimEnd('\', '/')
    $leaf = Split-Path -Path $trimmed -Leaf
    if ([string]::IsNullOrWhiteSpace($leaf)) {
        return $trimmed
    }
    return $leaf
}

function Escape-XmlText {
    param([string]$Value)

    if ($null -eq $Value) {
        return ""
    }
    return [System.Security.SecurityElement]::Escape($Value)
}

function Get-NotifierAppId {
    try {
        $startApp = Get-StartApps | Where-Object { $_.Name -eq "Windows Terminal" } | Select-Object -First 1
        if ($startApp -and $startApp.AppId) {
            return $startApp.AppId
        }
    } catch {
        Write-ToastLog "Get-StartApps failed: $($_.Exception.Message)"
    }

    return "Microsoft.WindowsTerminal_8wekyb3d8bbwe!App"
}

function Get-LaunchUri {
    param([string]$Cwd)

    $encodedCwd = [Uri]::EscapeDataString($Cwd)
    return "claude-dotfiles-toast://focus?cwd=$encodedCwd"
}

function Build-ToastContent {
    param(
        [Parameter(Mandatory = $true)]
        [psobject]$InputObject
    )

    $folder = Get-FolderLabel -PathValue $InputObject.cwd
    $summary = $folder

    switch ($InputObject.hook_event_name) {
        "Notification" {
            switch ($InputObject.notification_type) {
                "permission_prompt" {
                    return @{
                        Title = "Claude Code: Permission Needed"
                        Message = $summary
                        LaunchUri = Get-LaunchUri -Cwd $InputObject.cwd
                    }
                }
                "idle_prompt" {
                    return @{
                        Title = "Claude Code: Waiting For Input"
                        Message = $summary
                        LaunchUri = Get-LaunchUri -Cwd $InputObject.cwd
                    }
                }
                default {
                    return $null
                }
            }
        }
        "Stop" {
            return @{
                Title = "Claude Code: Response Complete"
                Message = $summary
                LaunchUri = Get-LaunchUri -Cwd $InputObject.cwd
            }
        }
        default {
            return $null
        }
    }
}

function Show-ToastNotification {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [Parameter(Mandatory = $true)]
        [string]$LaunchUri
    )

    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null

    $titleXml = Escape-XmlText -Value $Title
    $messageXml = Escape-XmlText -Value $Message
    $launchXml = Escape-XmlText -Value $LaunchUri

    $xml = @"
<toast activationType="protocol" launch="$launchXml">
  <visual>
    <binding template="ToastGeneric">
      <text>$titleXml</text>
      <text>$messageXml</text>
    </binding>
  </visual>
  <actions>
    <action content="Focus Terminal" activationType="protocol" arguments="$launchXml" />
  </actions>
  <audio src="ms-winsoundevent:Notification.Default" />
</toast>
"@

    $xmlDoc = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xmlDoc.LoadXml($xml)

    $toast = [Windows.UI.Notifications.ToastNotification]::new($xmlDoc)
    $appId = Get-NotifierAppId
    $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId)
    $notifier.Show($toast)
}

try {
    $inputObject = Read-HookInput
    if ($null -eq $inputObject) {
        exit 0
    }

    $toastContent = Build-ToastContent -InputObject $inputObject
    if ($null -eq $toastContent) {
        exit 0
    }

    Show-ToastNotification -Title $toastContent.Title -Message $toastContent.Message -LaunchUri $toastContent.LaunchUri
    exit 0
} catch {
    Write-ToastLog "notify-toast failed: $($_.Exception.Message)"
    exit 0
}
