$ErrorActionPreference = 'Stop'

$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$Utf8Strict = [System.Text.UTF8Encoding]::new($false, $true)
[Console]::OutputEncoding = $Utf8NoBom
$OutputEncoding = $Utf8NoBom

if ($PSVersionTable.PSEdition -eq 'Desktop') {
    Write-Warning 'Detected Windows PowerShell 5.1. Prefer: pwsh -NoProfile -ExecutionPolicy Bypass -File ~/.claude/scripts/init-project.ps1 ...'
}

function Get-UserHome {
    if ($env:HOME) { return $env:HOME }
    if ($env:USERPROFILE) { return $env:USERPROFILE }
    return $HOME
}

function Write-Utf8Text {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Content
    )

    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
}

function Read-Utf8TextStrict {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.File]::ReadAllText($Path, $Utf8Strict)
}

function Get-ObjectPropertyValue {
    param(
        $Object,
        [Parameter(Mandatory = $true)][string]$Name,
        $Default = $null
    )

    if ($null -eq $Object) {
        return $Default
    }

    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) {
            return $Object[$Name]
        }
        return $Default
    }

    $prop = $Object.PSObject.Properties[$Name]
    if ($null -ne $prop) {
        return $prop.Value
    }
    return $Default
}

function ConvertTo-PrettyJson {
    param($Object)
    return (($Object | ConvertTo-Json -Depth 20) -replace "`r?`n", "`n") + "`n"
}

function ConvertTo-JsonStringLiteral {
    param([string]$Value)
    return ($Value | ConvertTo-Json -Compress)
}

function Write-IfNew {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content,
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][bool]$Force
    )

    $exists = Test-Path -LiteralPath $Path
    if ($exists -and -not $Force) {
        Write-Output "  SKIP  $Label"
        return $false
    }

    Write-Utf8Text -Path $Path -Content $Content
    $action = if ($exists) { 'OVERWRITE' } else { 'CREATE' }
    Write-Output "  $action  $Label"
    return $true
}

function Get-FullPathSafe {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path)
}

function Get-RelativePathUnix {
    param(
        [Parameter(Mandatory = $true)][string]$BasePath,
        [Parameter(Mandatory = $true)][string]$ChildPath
    )

    $baseFull = (Get-FullPathSafe -Path $BasePath).TrimEnd('\', '/')
    $childFull = Get-FullPathSafe -Path $ChildPath
    if ($childFull.StartsWith($baseFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $childFull.Substring($baseFull.Length).TrimStart('\', '/').Replace('\', '/')
    }
    throw "Path '$ChildPath' is not inside '$BasePath'."
}

function Substitute-Content {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Content,
        [Parameter(Mandatory = $true)]$Preset
    )

    $result = $Content
    foreach ($prop in $Preset.PSObject.Properties) {
        $placeholder = '{{' + $prop.Name + '}}'
        $value = if ($null -eq $prop.Value) { '' } else { [string]$prop.Value }
        $result = $result.Replace($placeholder, $value)
    }
    return $result
}

function Should-SkipTemplateFile {
    param(
        [Parameter(Mandatory = $true)][string]$RelativePath,
        [Parameter(Mandatory = $true)][bool]$WorkflowOnly,
        [Parameter(Mandatory = $true)][bool]$IsCodexMain
    )

    if (-not $WorkflowOnly) {
        return $false
    }

    if ($IsCodexMain) {
        return $RelativePath.StartsWith('context/') -or $RelativePath.StartsWith('reviews/')
    }

    return $RelativePath.StartsWith('context/') -or $RelativePath -eq 'agents/sessions.json'
}

function Copy-TemplateTree {
    param(
        [Parameter(Mandatory = $true)][string]$TemplateDir,
        [Parameter(Mandatory = $true)][string]$DestDir,
        [Parameter(Mandatory = $true)]$Preset,
        [Parameter(Mandatory = $true)][bool]$Force,
        [Parameter(Mandatory = $true)][bool]$WorkflowOnly,
        [Parameter(Mandatory = $true)][bool]$IsCodexMain
    )

    foreach ($src in Get-ChildItem -LiteralPath $TemplateDir -Recurse -File) {
        $rel = Get-RelativePathUnix -BasePath $TemplateDir -ChildPath $src.FullName
        if (Should-SkipTemplateFile -RelativePath $rel -WorkflowOnly $WorkflowOnly -IsCodexMain $IsCodexMain) {
            Write-Output "  SKIP  $rel (workflow-only)"
            continue
        }

        $dst = Join-Path $DestDir ($rel -replace '/', '\')
        $exists = Test-Path -LiteralPath $dst
        if ($exists -and -not $Force) {
            Write-Output "  SKIP  $rel"
            continue
        }

        $parent = Split-Path -Parent $dst
        if ($parent) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }

        try {
            $content = Read-Utf8TextStrict -Path $src.FullName
            $content = Substitute-Content -Content $content -Preset $Preset
            Write-Utf8Text -Path $dst -Content $content
        } catch [System.Text.DecoderFallbackException] {
            Copy-Item -LiteralPath $src.FullName -Destination $dst -Force
        }

        $action = if ($exists) { 'OVERWRITE' } else { 'COPY' }
        Write-Output "  $action  $rel"
    }
}

function Get-VerifyPrefixes {
    param([string]$VerifyCommand)

    $prefixes = New-Object System.Collections.Generic.HashSet[string]
    foreach ($rawPart in ($VerifyCommand -split '&&')) {
        $part = $rawPart.Trim()
        if (-not $part) { continue }

        if ($part.StartsWith('"')) {
            $end = $part.IndexOf('"', 1)
            if ($end -gt 0) {
                [void]$prefixes.Add("Bash($($part.Substring(0, $end + 1)):*)")
            }
            continue
        }

        if ($part.StartsWith('& ')) {
            $inner = $part.Substring(2).Trim()
            if ($inner.StartsWith('"')) {
                $end = $inner.IndexOf('"', 1)
                if ($end -gt 0) {
                    [void]$prefixes.Add("Bash(& $($inner.Substring(0, $end + 1)):*)")
                }
            }
            continue
        }

        $tokens = @($part -split '\s+' | Where-Object { $_ -ne '' })
        if ($tokens.Count -eq 0) { continue }

        $keepFlags = @('-m', '-c')
        $prefixTokens = New-Object System.Collections.Generic.List[string]
        foreach ($token in $tokens) {
            if (($token.StartsWith('-') -or $token.StartsWith('/')) -and -not ($keepFlags -contains $token)) {
                break
            }
            $null = $prefixTokens.Add($token)
            if ($token -eq '-c') {
                break
            }
        }

        $prefix = if ($prefixTokens.Count -gt 0) {
            ($prefixTokens -join ' ')
        } else {
            $tokens[0]
        }
        [void]$prefixes.Add("Bash(${prefix}:*)")
    }

    return @($prefixes | Sort-Object)
}

function Add-IfMissing {
    param(
        [Parameter(Mandatory = $true)]$List,
        [Parameter(Mandatory = $true)][string]$Value
    )

    if (-not $List.Contains($Value)) {
        $null = $List.Add($Value)
    }
}

function Get-FileExtensionsFromPatterns {
    param([string]$Patterns)

    $exts = New-Object System.Collections.Generic.List[string]
    foreach ($pattern in ($Patterns -split ',')) {
        $trimmed = $pattern.Trim()
        if ($trimmed -like '*.*' -and $trimmed.Contains('*.')) {
            $ext = '.' + ($trimmed.Split('*.')[-1])
            Add-IfMissing -List $exts -Value $ext
        }
    }
    return @($exts)
}

function Get-GitignoreEntries {
    param([string]$RawEntries)

    $entries = New-Object System.Collections.Generic.List[string]
    foreach ($part in ($RawEntries -split ',')) {
        $entry = $part.Trim()
        if (-not $entry -or $entry -eq 'none') {
            continue
        }
        Add-IfMissing -List $entries -Value $entry
    }
    return @($entries)
}

$presetName = ''
$force = $false
$template = 'project-init'
$workflowOnly = $false
$codexMain = $false

for ($i = 0; $i -lt $args.Count; $i++) {
    $arg = [string]$args[$i]
    switch ($arg) {
        '-f' { $force = $true; continue }
        '--workflow-only' { $workflowOnly = $true; continue }
        '--skills-only' { $workflowOnly = $true; continue }
        '--codex-main' { $codexMain = $true; continue }
        '-t' {
            $i++
            if ($i -ge $args.Count) {
                throw 'ERROR: template name required after -t'
            }
            $template = [string]$args[$i]
            continue
        }
        default {
            $presetName = $arg
        }
    }
}

if ($codexMain) {
    if ($template -ne 'project-init' -and $template -ne 'codex-main') {
        throw "ERROR: --codex-main cannot be combined with -t $template"
    }
    $template = 'codex-main'
}

if (-not $presetName) {
    [Console]::Error.WriteLine('ERROR: preset name required')
    Write-Output "Usage: pwsh -NoProfile -ExecutionPolicy Bypass -File ~/.claude/scripts/init-project.ps1 [-t <template>] [--codex-main] <preset> [-f] [--workflow-only]"
    Write-Output ""
    Write-Output "Templates: project-init (default), research-survey, codex-main"
    Write-Output "Presets (project-init): python, python-pytorch, typescript, rust, ahk, ahk-v2, cpp-msvc, unity, blender"
    Write-Output "Presets (codex-main): python, python-pytorch, typescript, rust, ahk, ahk-v2, cpp-msvc, unity, blender"
    Write-Output "Presets (research-survey): survey-cv, survey-ms"
    exit 1
}

$templateSubdir = if ($template -eq 'codex-main') { '.agents' } else { '.claude' }
$destDir = if ($template -eq 'codex-main') {
    Join-Path (Get-Location).Path '.agents'
} else {
    Join-Path (Get-Location).Path '.claude'
}

$userHome = Get-UserHome
$templateDir = Join-Path $userHome ".claude\templates\$template\$templateSubdir"
$presetFile = Join-Path $userHome ".claude\templates\$template\presets.json"

if (-not (Test-Path -LiteralPath $templateDir -PathType Container)) {
    [Console]::Error.WriteLine("ERROR: Template not found: $templateDir")
    Write-Output "Run: bash ~/claude-dotfiles/setup.sh"
    exit 1
}

if (-not (Test-Path -LiteralPath $presetFile -PathType Leaf)) {
    [Console]::Error.WriteLine("ERROR: presets.json not found: $presetFile")
    exit 1
}

$presets = Read-Utf8TextStrict -Path $presetFile | ConvertFrom-Json
$preset = Get-ObjectPropertyValue -Object $presets -Name $presetName
if ($null -eq $preset) {
    $available = @($presets.PSObject.Properties.Name) -join ', '
    [Console]::Error.WriteLine("ERROR: Unknown preset '$presetName'")
    Write-Output "Available: $available"
    exit 1
}

$isResearch = $template -eq 'research-survey'
$isCodexMain = $template -eq 'codex-main'
$runtimeSettingsDir = if ($isCodexMain) {
    Join-Path (Get-Location).Path '.claude'
} else {
    $destDir
}
$runtimeSettingsPrefix = if ($isCodexMain) { '.claude/' } else { '' }
$lang = [string](Get-ObjectPropertyValue -Object $preset -Name 'LANG' -Default $presetName)
$verifyCmd = [string](Get-ObjectPropertyValue -Object $preset -Name 'VERIFY_CMD' -Default '')
$verifyShell = [string](Get-ObjectPropertyValue -Object $preset -Name 'VERIFY_SHELL' -Default 'bash')
$defaultPrimaryLogDir = if ($isCodexMain) { '.agents/logs/verify' } else { '.claude/logs/verify' }
$primaryLogDir = [string](Get-ObjectPropertyValue -Object $preset -Name 'PRIMARY_LOG_DIR' -Default $defaultPrimaryLogDir)

Write-Output "=== init-project: $presetName ==="
Write-Output "Dest: $destDir"
Write-Output ""

Copy-TemplateTree -TemplateDir $templateDir -DestDir $destDir -Preset $preset -Force $force -WorkflowOnly $workflowOnly -IsCodexMain $isCodexMain

$settingsPath = Join-Path $runtimeSettingsDir 'settings.json'

if ($isCodexMain) {
    $settingsObject = [ordered]@{
        hooks = [ordered]@{
            SessionStart = @(
                [ordered]@{
                    matcher = 'compact'
                    hooks = @(
                        [ordered]@{
                            type = 'command'
                            command = "echo 'Reminder: Follow .agents/AGENTS.md and use .agents/context/* as the working memory for $lang.'"
                        }
                    )
                }
            )
        }
    }
    Write-IfNew -Path $settingsPath -Content (ConvertTo-PrettyJson -Object $settingsObject) -Label "$runtimeSettingsPrefix`settings.json" -Force $force | Out-Null
}
elseif ($isResearch) {
    if (-not (Test-Path -LiteralPath $settingsPath) -or $force) {
        $domain = [string](Get-ObjectPropertyValue -Object $preset -Name 'DOMAIN' -Default $presetName)
        $settingsObject = [ordered]@{
            hooks = [ordered]@{
                SessionStart = @(
                    [ordered]@{
                        matcher = 'compact'
                        hooks = @(
                            [ordered]@{
                                type = 'command'
                                command = "echo 'Reminder: This is a research survey project. Domain: $domain. Use /scope to begin.'"
                            }
                        )
                    }
                )
            }
        }
        Write-IfNew -Path $settingsPath -Content (ConvertTo-PrettyJson -Object $settingsObject) -Label "$runtimeSettingsPrefix`settings.json" -Force $force | Out-Null
    }
    else {
        Write-Output "  SKIP  $runtimeSettingsPrefix`settings.json"
    }
}
else {
    $syntaxCmd = [string](Get-ObjectPropertyValue -Object $preset -Name 'SYNTAX_CHECK_CMD' -Default '')
    $syntaxEnabled = [bool](Get-ObjectPropertyValue -Object $preset -Name 'SYNTAX_CHECK_ENABLED' -Default $false)

    if ($force) {
        $settingsObject = [ordered]@{
            hooks = [ordered]@{
                SessionStart = @(
                    [ordered]@{
                        matcher = 'compact'
                        hooks = @(
                            [ordered]@{
                                type = 'command'
                                command = "echo 'Reminder: This project uses $lang. Do not mix syntax versions.'"
                            }
                        )
                    }
                )
            }
        }
        if ($syntaxEnabled -and $syntaxCmd) {
            $settingsObject.hooks.PostToolUse = @(
                [ordered]@{
                    matcher = 'Edit|Write'
                    hooks = @(
                        [ordered]@{
                            type = 'command'
                            command = 'python .claude/hooks/syntax-check.py'
                            timeout = 15
                            statusMessage = 'Syntax check...'
                        }
                    )
                }
            )
        }
        Write-IfNew -Path $settingsPath -Content (ConvertTo-PrettyJson -Object $settingsObject) -Label "$runtimeSettingsPrefix`settings.json" -Force $force | Out-Null
    }
    elseif (Test-Path -LiteralPath $settingsPath) {
        $settingsObject = Read-Utf8TextStrict -Path $settingsPath | ConvertFrom-Json
        if ($null -eq (Get-ObjectPropertyValue -Object $settingsObject -Name 'hooks')) {
            $settingsObject | Add-Member -NotePropertyName 'hooks' -NotePropertyValue ([pscustomobject]@{}) -Force
        }
        $hooks = $settingsObject.hooks
        if ($syntaxEnabled -and $syntaxCmd -and $null -eq (Get-ObjectPropertyValue -Object $hooks -Name 'PostToolUse')) {
            $hooks | Add-Member -NotePropertyName 'PostToolUse' -NotePropertyValue @(
                [ordered]@{
                    matcher = 'Edit|Write'
                    hooks = @(
                        [ordered]@{
                            type = 'command'
                            command = 'python .claude/hooks/syntax-check.py'
                            timeout = 15
                            statusMessage = 'Syntax check...'
                        }
                    )
                }
            ) -Force
            Write-Utf8Text -Path $settingsPath -Content (ConvertTo-PrettyJson -Object $settingsObject)
            Write-Output "  UPDATE $runtimeSettingsPrefix`settings.json (added PostToolUse)"
        }
        else {
            Write-Output "  SKIP  $runtimeSettingsPrefix`settings.json"
        }
    }
    else {
        $settingsObject = [ordered]@{
            hooks = [ordered]@{
                SessionStart = @(
                    [ordered]@{
                        matcher = 'compact'
                        hooks = @(
                            [ordered]@{
                                type = 'command'
                                command = "echo 'Reminder: This project uses $lang. Do not mix syntax versions.'"
                            }
                        )
                    }
                )
            }
        }
        if ($syntaxEnabled -and $syntaxCmd) {
            $settingsObject.hooks.PostToolUse = @(
                [ordered]@{
                    matcher = 'Edit|Write'
                    hooks = @(
                        [ordered]@{
                            type = 'command'
                            command = 'python .claude/hooks/syntax-check.py'
                            timeout = 15
                            statusMessage = 'Syntax check...'
                        }
                    )
                }
            )
        }
        Write-IfNew -Path $settingsPath -Content (ConvertTo-PrettyJson -Object $settingsObject) -Label "$runtimeSettingsPrefix`settings.json" -Force $force | Out-Null
    }
}

$verifyShTemplate = @'
#!/usr/bin/env bash
set -uo pipefail

VERIFY_CMD=__VERIFY_CMD_JSON__
VERIFY_SHELL=__VERIFY_SHELL_JSON__
LOG_DIR=__LOG_DIR_JSON__

mkdir -p "$LOG_DIR/history"

timestamp="$(date +%Y%m%d-%H%M%S)"
started_at="$(date -Iseconds)"
log_path="$LOG_DIR/history/${timestamp}-verify.log"
status_path="$LOG_DIR/history/${timestamp}-status.json"
latest_log="$LOG_DIR/latest.log"
latest_status="$LOG_DIR/latest.status.json"

json_escape() {
    awk -v s="$1" 'BEGIN {
        gsub(/\\/,"\\\\",s)
        gsub(/"/,"\\\"",s)
        printf "%s", s
    }'
}

exit_code=0

if [[ "$VERIFY_SHELL" == "powershell" ]]; then
    if command -v pwsh >/dev/null 2>&1; then
        pwsh -NoProfile -ExecutionPolicy Bypass -Command "$VERIFY_CMD" 2>&1 | tee "$log_path"
        exit_code=${PIPESTATUS[0]}
    elif command -v powershell >/dev/null 2>&1; then
        powershell -NoProfile -ExecutionPolicy Bypass -Command "$VERIFY_CMD" 2>&1 | tee "$log_path"
        exit_code=${PIPESTATUS[0]}
    else
        printf '%s\n' 'ERROR: PowerShell was not found but VERIFY_SHELL=powershell.' | tee "$log_path"
        exit_code=127
    fi
else
    bash -lc "$VERIFY_CMD" 2>&1 | tee "$log_path"
    exit_code=${PIPESTATUS[0]}
fi

finished_at="$(date -Iseconds)"
escaped_command="$(json_escape "$VERIFY_CMD")"
escaped_log_path="$(json_escape "$log_path")"

cat > "$status_path" <<EOF
{
  "ok": $([[ "$exit_code" -eq 0 ]] && echo true || echo false),
  "command": "$escaped_command",
  "exit_code": $exit_code,
  "started_at": "$started_at",
  "finished_at": "$finished_at",
  "log_path": "$escaped_log_path"
}
EOF

cp "$log_path" "$latest_log"
cp "$status_path" "$latest_status"

exit "$exit_code"
'@
$verifySh = $verifyShTemplate.Replace('__VERIFY_CMD_JSON__', (ConvertTo-JsonStringLiteral -Value $verifyCmd)).Replace('__VERIFY_SHELL_JSON__', (ConvertTo-JsonStringLiteral -Value $verifyShell)).Replace('__LOG_DIR_JSON__', (ConvertTo-JsonStringLiteral -Value $primaryLogDir))

$verifyPs1Template = @'
$ErrorActionPreference = "Continue"

$verifyCommand = @"
__VERIFY_CMD__
"@

$logDir = "__LOG_DIR__"
$historyDir = Join-Path $logDir "history"
New-Item -ItemType Directory -Path $historyDir -Force | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$startedAt = (Get-Date).ToString("o")
$logPath = Join-Path $historyDir "$timestamp-verify.log"
$statusPath = Join-Path $historyDir "$timestamp-status.json"
$latestLog = Join-Path $logDir "latest.log"
$latestStatus = Join-Path $logDir "latest.status.json"

try {
    Invoke-Expression $verifyCommand 2>&1 | Tee-Object -FilePath $logPath
    $exitCode = if ($LASTEXITCODE -ne $null) { [int]$LASTEXITCODE } else { 0 }
} catch {
    $_ | Out-String | Tee-Object -FilePath $logPath -Append | Out-Host
    $exitCode = 1
}

$finishedAt = (Get-Date).ToString("o")
$status = [PSCustomObject]@{
    ok = ($exitCode -eq 0)
    command = $verifyCommand.Trim()
    exit_code = $exitCode
    started_at = $startedAt
    finished_at = $finishedAt
    log_path = $logPath
}

$status | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
Copy-Item -LiteralPath $logPath -Destination $latestLog -Force
Copy-Item -LiteralPath $statusPath -Destination $latestStatus -Force

exit $exitCode
'@
$verifyPs1 = $verifyPs1Template.Replace('__VERIFY_CMD__', $verifyCmd).Replace('__LOG_DIR__', $primaryLogDir)

$codexPlanReviewPs1Template = @'
param(
    [ValidateSet("arch", "detail")]
    [string]$Phase = "arch",
    [string]$Feature = "",
    [switch]$NoPrevious
)

$ErrorActionPreference = "Stop"
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$Utf8Strict = [System.Text.UTF8Encoding]::new($false, $true)
[Console]::OutputEncoding = $Utf8NoBom
$OutputEncoding = $Utf8NoBom

function Read-Utf8TextStrict {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.File]::ReadAllText($Path, $Utf8Strict)
}

function Write-Utf8Text {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
}

function Read-SessionsState {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        $state = Read-Utf8TextStrict -Path $Path | ConvertFrom-Json -AsHashtable
        if ($null -eq $state) {
            $state = @{}
        }
    } else {
        $state = @{}
    }

    if (-not $state.ContainsKey('reviews') -or $null -eq $state['reviews']) {
        $state['reviews'] = @()
    }
    if (-not $state.ContainsKey('current') -or $null -eq $state['current']) {
        $state['current'] = @{}
    }
    if (-not $state['current'].ContainsKey('plan_review') -or $null -eq $state['current']['plan_review']) {
        $state['current']['plan_review'] = @{
            phase_a_cycles = 0
            phase_b_cycles = 0
        }
    }
    if (-not $state['current'].ContainsKey('impl_review') -or $null -eq $state['current']['impl_review']) {
        $state['current']['impl_review'] = @{
            cycle = 0
        }
    }
    return $state
}

function Write-SessionsState {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)]$State
    )

    Write-Utf8Text -Path $Path -Content (($State | ConvertTo-Json -Depth 20) -replace "`r?`n", "`n")
}

function Get-TextHash {
    param([Parameter(Mandatory = $true)][string]$Text)

    $bytes = $Utf8NoBom.GetBytes($Text)
    $hashBytes = [System.Security.Cryptography.SHA256]::HashData($bytes)
    return ([System.BitConverter]::ToString($hashBytes) -replace '-', '').ToLowerInvariant()
}

function Append-Section {
    param(
        [Parameter(Mandatory = $true)]$Builder,
        [Parameter(Mandatory = $true)][string]$Title,
        [AllowNull()]$Content
    )

    $text = if ($null -eq $Content) { "" } else { [string]$Content }
    if (-not $text.Trim()) {
        return
    }

    [void]$Builder.AppendLine("---")
    [void]$Builder.AppendLine("# $Title")
    [void]$Builder.AppendLine("")
    [void]$Builder.AppendLine($text.TrimEnd())
    [void]$Builder.AppendLine("")
}

function Get-FeatureName {
    param([Parameter(Mandatory = $true)][string]$PlanContent)

    if ($Feature) {
        return $Feature
    }

    $objectiveMatch = [regex]::Match($PlanContent, '(?ms)^## Objective\s+(.*?)(?=^## |\z)')
    if ($objectiveMatch.Success) {
        $normalized = ($objectiveMatch.Groups[1].Value -replace '\s+', ' ').Trim()
        if ($normalized) {
            return $normalized
        }
    }

    $firstHeading = [regex]::Match($PlanContent, '(?m)^#\s+(.+)$')
    if ($firstHeading.Success) {
        return $firstHeading.Groups[1].Value.Trim()
    }

    return "Unnamed feature"
}

$repoRoot = (Get-Location).Path
$agentsDir = Join-Path $repoRoot ".agents"
$contextDir = Join-Path $agentsDir "context"
$reviewsDir = Join-Path $agentsDir "reviews"
$promptsDir = Join-Path $agentsDir "prompts"
$sessionsPath = Join-Path $reviewsDir "sessions.json"

$planPath = Join-Path $contextDir "plan.md"
$tasksPath = Join-Path $contextDir "tasks.md"
$snippetsPath = Join-Path $contextDir "snippets.md"
$bundlePath = Join-Path $contextDir "_codex_input.tmp"

if (-not (Test-Path -LiteralPath $planPath -PathType Leaf)) {
    throw "Missing file: $planPath"
}
if (-not (Test-Path -LiteralPath $tasksPath -PathType Leaf)) {
    throw "Missing file: $tasksPath"
}

$phaseConfig = if ($Phase -eq "arch") {
    [ordered]@{
        PromptPath = Join-Path $promptsDir "codex_plan_arch_review.md"
        ContextOutput = Join-Path $contextDir "codex_plan_arch_review.md"
        ReviewOutput = Join-Path $reviewsDir "plan-arch-review.md"
        PreviousTitle = "Previous Architecture Review"
    }
} else {
    [ordered]@{
        PromptPath = Join-Path $promptsDir "codex_plan_review.md"
        ContextOutput = Join-Path $contextDir "codex_plan_tasks_review.md"
        ReviewOutput = Join-Path $reviewsDir "plan-review.md"
        PreviousTitle = "Previous Detail Review"
    }
}
$sessionsState = Read-SessionsState -Path $sessionsPath
$cycleKey = if ($Phase -eq "arch") { "phase_a_cycles" } else { "phase_b_cycles" }
$maxCycles = if ($Phase -eq "arch") { 2 } else { 3 }
$startCycle = [int]$sessionsState['current']['plan_review'][$cycleKey]
$previousBundleHash = $null

for ($currentCycle = $startCycle + 1; $currentCycle -le $maxCycles; $currentCycle++) {
    $sessionsState['current']['plan_review'][$cycleKey] = $currentCycle
    Write-SessionsState -Path $sessionsPath -State $sessionsState

    $planContent = Read-Utf8TextStrict -Path $planPath
    $tasksContent = Read-Utf8TextStrict -Path $tasksPath
    $promptContent = Read-Utf8TextStrict -Path $phaseConfig.PromptPath
    $featureName = Get-FeatureName -PlanContent $planContent
    $promptContent = $promptContent.Replace('$FEATURE', $featureName)

    $builder = New-Object System.Text.StringBuilder
    Append-Section -Builder $builder -Title "Prompt" -Content $promptContent
    Append-Section -Builder $builder -Title "plan.md" -Content $planContent
    Append-Section -Builder $builder -Title "tasks.md" -Content $tasksContent
    if (Test-Path -LiteralPath $snippetsPath -PathType Leaf) {
        Append-Section -Builder $builder -Title "snippets.md" -Content (Read-Utf8TextStrict -Path $snippetsPath)
    }
    if ((-not $NoPrevious) -and (Test-Path -LiteralPath $phaseConfig.ContextOutput -PathType Leaf)) {
        Append-Section -Builder $builder -Title $phaseConfig.PreviousTitle -Content (Read-Utf8TextStrict -Path $phaseConfig.ContextOutput)
    }

    $bundleText = $builder.ToString()
    $bundleHash = Get-TextHash -Text $bundleText
    if ($null -ne $previousBundleHash -and $bundleHash -eq $previousBundleHash) {
        Write-Warning "Bundle is unchanged since the previous cycle. Stopping auto-loop."
        break
    }
    $previousBundleHash = $bundleHash

    Write-Utf8Text -Path $bundlePath -Content $bundleText
    $reviewText = Get-Content -LiteralPath $bundlePath -Encoding UTF8 -Raw | codex review -
    $reviewText = ($reviewText | Out-String).TrimEnd()
    if (-not $reviewText) {
        throw "codex review returned empty output."
    }
    $verdictMatch = [regex]::Match($reviewText, '(?m)^VERDICT:\s*(APPROVED|DISCUSS|REVISE)\s*$')
    if (-not $verdictMatch.Success) {
        $reviewText = $reviewText + "`n`nVERDICT: DISCUSS"
        $verdictMatch = [regex]::Match($reviewText, '(?m)^VERDICT:\s*(APPROVED|DISCUSS|REVISE)\s*$')
        Write-Warning "VERDICT line was not found. Appended fallback VERDICT: DISCUSS."
    }
    $reviewText = $reviewText.TrimEnd() + "`n"

    Write-Utf8Text -Path $phaseConfig.ContextOutput -Content $reviewText
    Write-Utf8Text -Path $phaseConfig.ReviewOutput -Content $reviewText
    if ($Phase -eq "detail" -and $verdictMatch.Groups[1].Value -eq "APPROVED") {
        $reviews = @($sessionsState['reviews'])
        $reviews += @{
            kind = "plan-review"
            phase_a_cycles = [int]$sessionsState['current']['plan_review']['phase_a_cycles']
            phase_b_cycles = [int]$sessionsState['current']['plan_review']['phase_b_cycles']
            date = (Get-Date).ToString("o")
            verdict = "APPROVED"
        }
        $sessionsState['reviews'] = $reviews
        $sessionsState['current']['plan_review']['phase_a_cycles'] = 0
        $sessionsState['current']['plan_review']['phase_b_cycles'] = 0
        Write-SessionsState -Path $sessionsPath -State $sessionsState
    }
    Write-Output "VERDICT: $($verdictMatch.Groups[1].Value)"
    Write-Output "Cycle: $currentCycle"
    Write-Output "Bundle: $bundlePath"
    Write-Output "Review: $($phaseConfig.ContextOutput)"
    Write-Output "Sessions: $sessionsPath"

    if ($verdictMatch.Groups[1].Value -eq "APPROVED" -or $verdictMatch.Groups[1].Value -eq "DISCUSS") {
        break
    }
    if ($currentCycle -ge $maxCycles) {
        Write-Warning "Reached max cycles for phase '$Phase'."
        break
    }
}
'@

$codexImplReviewPs1Template = @'
param(
    [string]$TaskDescription = "",
    [string[]]$Files = @(),
    [string[]]$IncludeFiles = @(),
    [switch]$NoPrevious
)

$ErrorActionPreference = "Stop"
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$Utf8Strict = [System.Text.UTF8Encoding]::new($false, $true)
[Console]::OutputEncoding = $Utf8NoBom
$OutputEncoding = $Utf8NoBom

function Read-Utf8TextStrict {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.File]::ReadAllText($Path, $Utf8Strict)
}

function Write-Utf8Text {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
}

function Read-SessionsState {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        $state = Read-Utf8TextStrict -Path $Path | ConvertFrom-Json -AsHashtable
        if ($null -eq $state) {
            $state = @{}
        }
    } else {
        $state = @{}
    }

    if (-not $state.ContainsKey('reviews') -or $null -eq $state['reviews']) {
        $state['reviews'] = @()
    }
    if (-not $state.ContainsKey('current') -or $null -eq $state['current']) {
        $state['current'] = @{}
    }
    if (-not $state['current'].ContainsKey('plan_review') -or $null -eq $state['current']['plan_review']) {
        $state['current']['plan_review'] = @{
            phase_a_cycles = 0
            phase_b_cycles = 0
        }
    }
    if (-not $state['current'].ContainsKey('impl_review') -or $null -eq $state['current']['impl_review']) {
        $state['current']['impl_review'] = @{
            cycle = 0
        }
    }
    return $state
}

function Write-SessionsState {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)]$State
    )

    Write-Utf8Text -Path $Path -Content (($State | ConvertTo-Json -Depth 20) -replace "`r?`n", "`n")
}

function Get-TextHash {
    param([Parameter(Mandatory = $true)][string]$Text)

    $bytes = $Utf8NoBom.GetBytes($Text)
    $hashBytes = [System.Security.Cryptography.SHA256]::HashData($bytes)
    return ([System.BitConverter]::ToString($hashBytes) -replace '-', '').ToLowerInvariant()
}

function Append-Section {
    param(
        [Parameter(Mandatory = $true)]$Builder,
        [Parameter(Mandatory = $true)][string]$Title,
        [AllowNull()]$Content
    )

    $text = if ($null -eq $Content) { "" } else { [string]$Content }
    if (-not $text.Trim()) {
        return
    }

    [void]$Builder.AppendLine("---")
    [void]$Builder.AppendLine("# $Title")
    [void]$Builder.AppendLine("")
    [void]$Builder.AppendLine($text.TrimEnd())
    [void]$Builder.AppendLine("")
}

function Get-RepoRelativePath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $combined = if ([System.IO.Path]::IsPathRooted($Path)) { $Path } else { Join-Path (Get-Location).Path $Path }
    $resolved = [System.IO.Path]::GetFullPath($combined)
    $root = [System.IO.Path]::GetFullPath((Get-Location).Path).TrimEnd('\', '/')
    if (-not $resolved.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside repo root: $Path"
    }
    return $resolved.Substring($root.Length).TrimStart('\', '/').Replace('\', '/')
}

function Get-UniquePaths {
    param([string[]]$InputPaths)

    $list = New-Object System.Collections.Generic.List[string]
    foreach ($path in $InputPaths) {
        if (-not $path) {
            continue
        }
        $relative = Get-RepoRelativePath -Path $path
        if (-not $list.Contains($relative)) {
            $null = $list.Add($relative)
        }
    }
    return @($list)
}

function Get-ChangedFiles {
    $output = & git diff --name-only --diff-filter=ACMRTUXB
    if ($LASTEXITCODE -ne 0) {
        throw "git diff --name-only failed."
    }
    return @($output | Where-Object { $_ -and $_.Trim() })
}

$repoRoot = (Get-Location).Path
$agentsDir = Join-Path $repoRoot ".agents"
$contextDir = Join-Path $agentsDir "context"
$reviewsDir = Join-Path $agentsDir "reviews"
$promptsDir = Join-Path $agentsDir "prompts"
$sessionsPath = Join-Path $reviewsDir "sessions.json"

$promptPath = Join-Path $promptsDir "codex_impl_review.md"
$bundlePath = Join-Path $contextDir "_codex_input.tmp"
$contextOutput = Join-Path $contextDir "codex_impl_review.md"
$reviewOutput = Join-Path $reviewsDir "impl-review.md"
$planPath = Join-Path $contextDir "plan.md"
$tasksPath = Join-Path $contextDir "tasks.md"

$sessionsState = Read-SessionsState -Path $sessionsPath
$startCycle = [int]$sessionsState['current']['impl_review']['cycle']
$maxCycles = 5
$previousBundleHash = $null

for ($currentCycle = $startCycle + 1; $currentCycle -le $maxCycles; $currentCycle++) {
    $sessionsState['current']['impl_review']['cycle'] = $currentCycle
    Write-SessionsState -Path $sessionsPath -State $sessionsState

    $targetFiles = if ($Files.Count -gt 0) { Get-UniquePaths -InputPaths $Files } else { Get-UniquePaths -InputPaths (Get-ChangedFiles) }
    if ($targetFiles.Count -eq 0) {
        throw "No files to review."
    }
    $dependencyFiles = Get-UniquePaths -InputPaths $IncludeFiles

    $taskSummary = if ($TaskDescription) {
        $TaskDescription
    } else {
        "Review changes in " + ($targetFiles -join ", ")
    }

    $promptContent = Read-Utf8TextStrict -Path $promptPath
    $promptContent = $promptContent.Replace('$TASK_DESCRIPTION', $taskSummary)
    $promptContent = $promptContent.Replace('$FILE_LIST', ($targetFiles -join ", "))

    $builder = New-Object System.Text.StringBuilder
    Append-Section -Builder $builder -Title "Prompt" -Content $promptContent
    if (Test-Path -LiteralPath $planPath -PathType Leaf) {
        Append-Section -Builder $builder -Title "plan.md" -Content (Read-Utf8TextStrict -Path $planPath)
    }
    if (Test-Path -LiteralPath $tasksPath -PathType Leaf) {
        Append-Section -Builder $builder -Title "tasks.md" -Content (Read-Utf8TextStrict -Path $tasksPath)
    }

    $diffOutput = & git diff --no-ext-diff -- @($targetFiles)
    if ($LASTEXITCODE -ne 0) {
        throw "git diff failed."
    }
    Append-Section -Builder $builder -Title "git diff" -Content (($diffOutput | Out-String).TrimEnd())

    foreach ($relativePath in $targetFiles) {
        $fullPath = Join-Path $repoRoot ($relativePath -replace '/', '\')
        if (Test-Path -LiteralPath $fullPath -PathType Leaf) {
            try {
                Append-Section -Builder $builder -Title "file: $relativePath" -Content (Read-Utf8TextStrict -Path $fullPath)
            } catch [System.Text.DecoderFallbackException] {
                Append-Section -Builder $builder -Title "file: $relativePath" -Content "[binary or non-UTF8 file omitted]"
            }
        }
    }

    foreach ($relativePath in $dependencyFiles) {
        $fullPath = Join-Path $repoRoot ($relativePath -replace '/', '\')
        if (Test-Path -LiteralPath $fullPath -PathType Leaf) {
            try {
                Append-Section -Builder $builder -Title "dependency: $relativePath" -Content (Read-Utf8TextStrict -Path $fullPath)
            } catch [System.Text.DecoderFallbackException] {
                Append-Section -Builder $builder -Title "dependency: $relativePath" -Content "[binary or non-UTF8 file omitted]"
            }
        }
    }

    if ((-not $NoPrevious) -and (Test-Path -LiteralPath $contextOutput -PathType Leaf)) {
        Append-Section -Builder $builder -Title "Previous Review" -Content (Read-Utf8TextStrict -Path $contextOutput)
    }

    $bundleText = $builder.ToString()
    $bundleHash = Get-TextHash -Text $bundleText
    if ($null -ne $previousBundleHash -and $bundleHash -eq $previousBundleHash) {
        Write-Warning "Bundle is unchanged since the previous cycle. Stopping auto-loop."
        break
    }
    $previousBundleHash = $bundleHash

    Write-Utf8Text -Path $bundlePath -Content $bundleText
    $reviewText = Get-Content -LiteralPath $bundlePath -Encoding UTF8 -Raw | codex review -
    $reviewText = ($reviewText | Out-String).TrimEnd()
    if (-not $reviewText) {
        throw "codex review returned empty output."
    }
    $verdictMatch = [regex]::Match($reviewText, '(?m)^VERDICT:\s*(APPROVED|CONDITIONAL|REVISE)\s*$')
    if (-not $verdictMatch.Success) {
        $reviewText = $reviewText + "`n`nVERDICT: CONDITIONAL"
        $verdictMatch = [regex]::Match($reviewText, '(?m)^VERDICT:\s*(APPROVED|CONDITIONAL|REVISE)\s*$')
        Write-Warning "VERDICT line was not found. Appended fallback VERDICT: CONDITIONAL."
    }
    $reviewText = $reviewText.TrimEnd() + "`n"

    Write-Utf8Text -Path $contextOutput -Content $reviewText
    Write-Utf8Text -Path $reviewOutput -Content $reviewText
    if ($verdictMatch.Groups[1].Value -eq "APPROVED") {
        $reviews = @($sessionsState['reviews'])
        $reviews += @{
            kind = "impl-review"
            cycle = $currentCycle
            date = (Get-Date).ToString("o")
            verdict = "APPROVED"
        }
        $sessionsState['reviews'] = $reviews
        $sessionsState['current']['impl_review']['cycle'] = 0
        Write-SessionsState -Path $sessionsPath -State $sessionsState
    }
    Write-Output "VERDICT: $($verdictMatch.Groups[1].Value)"
    Write-Output "Cycle: $currentCycle"
    Write-Output "Bundle: $bundlePath"
    Write-Output "Review: $contextOutput"
    Write-Output "Sessions: $sessionsPath"

    if ($verdictMatch.Groups[1].Value -eq "APPROVED") {
        break
    }
    if ($currentCycle -ge $maxCycles) {
        Write-Warning "Reached max cycles for implementation review."
        break
    }
}
'@

if ($isCodexMain) {
    Write-IfNew -Path (Join-Path (Get-Location).Path 'scripts\run-verify.sh') -Content $verifySh -Label 'scripts/run-verify.sh' -Force $force | Out-Null
    Write-IfNew -Path (Join-Path (Get-Location).Path 'scripts\run-verify.ps1') -Content $verifyPs1 -Label 'scripts/run-verify.ps1' -Force $force | Out-Null
    Write-IfNew -Path (Join-Path (Get-Location).Path 'scripts\run-codex-plan-review.ps1') -Content $codexPlanReviewPs1Template -Label 'scripts/run-codex-plan-review.ps1' -Force $force | Out-Null
    Write-IfNew -Path (Join-Path (Get-Location).Path 'scripts\run-codex-impl-review.ps1') -Content $codexImplReviewPs1Template -Label 'scripts/run-codex-impl-review.ps1' -Force $force | Out-Null
}
elseif (-not $isResearch) {
    $syntaxCmd = [string](Get-ObjectPropertyValue -Object $preset -Name 'SYNTAX_CHECK_CMD' -Default '')
    $syntaxEnabled = [bool](Get-ObjectPropertyValue -Object $preset -Name 'SYNTAX_CHECK_ENABLED' -Default $false)
    $filePatterns = [string](Get-ObjectPropertyValue -Object $preset -Name 'FILE_PATTERNS' -Default '')
    $langRules = [string](Get-ObjectPropertyValue -Object $preset -Name 'LANG_RULES' -Default '')
    $exts = Get-FileExtensionsFromPatterns -Patterns $filePatterns

    if ($syntaxEnabled -and $syntaxCmd) {
        $hookTemplate = @'
#!/usr/bin/env python3
"""PostToolUse hook: syntax check for __LANG__ files."""
import json, sys, os, subprocess

EXTENSIONS = __EXTS_JSON__
SYNTAX_CMD = __SYNTAX_CMD_JSON__

def main():
    data = json.load(sys.stdin)
    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in EXTENSIONS:
        return
    cmd = SYNTAX_CMD.replace("$FILE", file_path)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        output = (result.stderr or result.stdout).strip()
        print(output, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
'@
        $hookContent = $hookTemplate.Replace('__LANG__', $lang).Replace('__EXTS_JSON__', (($exts | ConvertTo-Json -Compress) -replace "`r?`n", '')).Replace('__SYNTAX_CMD_JSON__', ([string]($syntaxCmd | ConvertTo-Json -Compress)))
        Write-IfNew -Path (Join-Path $destDir 'hooks\syntax-check.py') -Content $hookContent -Label 'hooks/syntax-check.py' -Force $force | Out-Null
    }

    Write-IfNew -Path (Join-Path $destDir 'scripts\run-verify.sh') -Content $verifySh -Label 'scripts/run-verify.sh' -Force $force | Out-Null
    Write-IfNew -Path (Join-Path $destDir 'scripts\run-verify.ps1') -Content $verifyPs1 -Label 'scripts/run-verify.ps1' -Force $force | Out-Null

    $failureReport = @'
# Failure Report

## Summary

- Task:
- Failure pattern:
- Attempted command:
- Exit code:
- Latest status file: `.claude/logs/verify/latest.status.json`
- Latest log file: `.claude/logs/verify/latest.log`

## Latest Status Snapshot

```json
{}
```

## Latest Log Tail

```text
(paste the last 50 lines from .claude/logs/verify/latest.log here)
```

## Notes

- What was tried:
- Suspected root cause:
- Next decision needed:
'@
    Write-IfNew -Path (Join-Path $destDir 'context\failure_report.md') -Content $failureReport -Label 'context/failure_report.md' -Force $force | Out-Null

    $claudeMd = @"
# $lang Project

## Language

$lang。構文バージョンを混同しないこと。

## Coding Rules

$langRules

## Commit Messages

- 1行目 (subject): 英語。imperative form (e.g. `Fix authentication bug`)
- 2行目: 空行
- 3行目以降 (body): 日本語可。変更理由・詳細を記述

## Testing

検証コマンド: `$verifyCmd`
"@
    $claudeMdPath = Join-Path $destDir 'CLAUDE.md'
    Write-IfNew -Path $claudeMdPath -Content $claudeMd -Label 'CLAUDE.md' -Force $force | Out-Null
    if (-not (Test-Path -LiteralPath $claudeMdPath)) {
        Write-Utf8Text -Path $claudeMdPath -Content $claudeMd
    }
}

if ($isResearch) {
    $domain = [string](Get-ObjectPropertyValue -Object $preset -Name 'DOMAIN' -Default $presetName)
    $surveyRules = [string](Get-ObjectPropertyValue -Object $preset -Name 'SURVEY_RULES' -Default '')
    $keyVenues = [string](Get-ObjectPropertyValue -Object $preset -Name 'KEY_VENUES' -Default '')
    $claudeMd = @"
# Research Survey — $domain

## Domain

$domain

## Key Venues

$keyVenues

## Survey Methodology Rules

$surveyRules

## Tools

推奨 CLI ツール（全てオプション）:
- `pip install paper-qa>=5 arxiv-dl marker-pdf semanticscholar bibcure`
- Pandoc: `winget install --id JohnMacFarlane.Pandoc`

ツール検出: `/check-tools`

## Workflow

`/scope` → `/search` → `/read` → `/outline` → `/draft` → `/review` → `/convert`

## Commit Messages

- 1行目 (subject): 英語。imperative form (e.g. `Add survey section on X`)
- 2行目: 空行
- 3行目以降 (body): 日本語可。変更理由・詳細を記述
"@
    $claudeMdPath = Join-Path $destDir 'CLAUDE.md'
    Write-IfNew -Path $claudeMdPath -Content $claudeMd -Label 'CLAUDE.md' -Force $force | Out-Null
    if (-not (Test-Path -LiteralPath $claudeMdPath)) {
        Write-Utf8Text -Path $claudeMdPath -Content $claudeMd
    }
}

$localPath = Join-Path $runtimeSettingsDir 'settings.local.json.bak'
$localActive = Join-Path $runtimeSettingsDir 'settings.local.json'
if ($isResearch) {
    $localObject = [ordered]@{
        permissions = [ordered]@{
            allow = @(
                'Bash(git status:*)',
                'Bash(git diff:*)',
                'Bash(git log:*)',
                'Bash(git add:*)',
                'Bash(git commit:*)',
                'Bash(pqa:*)',
                'Bash(paper:*)',
                'Bash(marker_single:*)',
                'Bash(bibcure:*)',
                'Bash(pandoc:*)',
                'Bash(bash ~/.claude/scripts/survey-convert.sh:*)',
                'Bash(python -c:*)',
                'Bash(python3 -c:*)',
                'WebSearch',
                'WebFetch(domain:arxiv.org)',
                'WebFetch(domain:semanticscholar.org)',
                'WebFetch(domain:scholar.google.com)',
                'WebFetch(domain:openreview.net)',
                'WebFetch(domain:aclanthology.org)',
                'WebFetch(domain:papers.nips.cc)',
                'WebFetch(domain:openaccess.thecvf.com)',
                'WebFetch(domain:doi.org)'
            )
        }
    }
}
else {
    $verifyPrefixes = Get-VerifyPrefixes -VerifyCommand $verifyCmd
    $contextReadAllow = if ($isCodexMain) { 'Bash(cat .agents/context/*)' } else { 'Bash(cat .claude/context/*)' }
    $allow = New-Object System.Collections.Generic.List[string]
    foreach ($value in @(
        'Bash(git status:*)',
        'Bash(git diff:*)',
        'Bash(git log:*)',
        'Bash(git add:*)',
        'Bash(git commit:*)',
        'Bash(codex review:*)',
        $contextReadAllow,
        'WebSearch',
        'WebFetch'
    )) {
        Add-IfMissing -List $allow -Value $value
    }
    if ($isCodexMain) {
        foreach ($value in @(
            'Bash(pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/run-codex-plan-review.ps1:*)',
            'Bash(pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/run-codex-impl-review.ps1:*)',
            'Bash(./scripts/run-codex-plan-review.ps1:*)',
            'Bash(./scripts/run-codex-impl-review.ps1:*)',
            'Bash(scripts/run-codex-plan-review.ps1:*)',
            'Bash(scripts/run-codex-impl-review.ps1:*)'
        )) {
            Add-IfMissing -List $allow -Value $value
        }
    }
    foreach ($prefix in $verifyPrefixes) {
        Add-IfMissing -List $allow -Value $prefix
    }
    $localObject = [ordered]@{
        permissions = [ordered]@{
            allow = @($allow)
        }
    }
}

Write-IfNew -Path $localPath -Content (ConvertTo-PrettyJson -Object $localObject) -Label "$runtimeSettingsPrefix`settings.local.json.bak" -Force $force | Out-Null
if ($force -and (Test-Path -LiteralPath $localActive)) {
    Write-Utf8Text -Path $localActive -Content (ConvertTo-PrettyJson -Object $localObject)
    Write-Output "  UPDATE $runtimeSettingsPrefix`settings.local.json (synced with .bak)"
}

if ($isResearch) {
    $researchClaudePath = Join-Path $destDir 'CLAUDE.md'
    if (-not (Test-Path -LiteralPath $researchClaudePath)) {
        $domain = [string](Get-ObjectPropertyValue -Object $preset -Name 'DOMAIN' -Default $presetName)
        $surveyRules = [string](Get-ObjectPropertyValue -Object $preset -Name 'SURVEY_RULES' -Default '')
        $keyVenues = [string](Get-ObjectPropertyValue -Object $preset -Name 'KEY_VENUES' -Default '')
        $claudeMd = @"
# Research Survey — $domain

## Domain

$domain

## Key Venues

$keyVenues

## Survey Methodology Rules

$surveyRules

## Tools

推奨 CLI ツール（全てオプション）:
- `pip install paper-qa>=5 arxiv-dl marker-pdf semanticscholar bibcure`
- Pandoc: `winget install --id JohnMacFarlane.Pandoc`

ツール検出: `/check-tools`

## Workflow

`/scope` → `/search` → `/read` → `/outline` → `/draft` → `/review` → `/convert`

## Commit Messages

- 1行目 (subject): 英語。imperative form (e.g. `Add survey section on X`)
- 2行目: 空行
- 3行目以降 (body): 日本語可。変更理由・詳細を記述
"@
        Write-Utf8Text -Path $researchClaudePath -Content $claudeMd
    }
}

$gitignorePath = Join-Path (Get-Location).Path '.gitignore'
if (-not (Test-Path -LiteralPath $gitignorePath)) {
    Write-Utf8Text -Path $gitignorePath -Content ''
}
$gitignoreContent = Read-Utf8TextStrict -Path $gitignorePath
$gitignoreEntries = New-Object System.Collections.Generic.List[string]
if ($template -eq 'codex-main') {
    $defaultGitignoreEntries = @('.agents/', '.codex_tmp/')
}
else {
    $defaultGitignoreEntries = @('.claude/', '.codex_tmp/')
}
foreach ($entry in $defaultGitignoreEntries) {
    Add-IfMissing -List $gitignoreEntries -Value $entry
}
foreach ($entry in (Get-GitignoreEntries -RawEntries ([string](Get-ObjectPropertyValue -Object $preset -Name 'GITIGNORE_ENTRIES' -Default '')))) {
    Add-IfMissing -List $gitignoreEntries -Value $entry
}

foreach ($entry in $gitignoreEntries) {
    if (-not ($gitignoreContent -split "`r?`n" | Where-Object { $_ -eq $entry })) {
        if ($gitignoreContent.Length -gt 0 -and -not $gitignoreContent.EndsWith("`n")) {
            $gitignoreContent += "`n"
        }
        $gitignoreContent += "$entry`n"
        Write-Utf8Text -Path $gitignorePath -Content $gitignoreContent
        Write-Output "  GITIGNORE += $entry"
    }
}

Write-Output ""
Write-Output "=== Done ==="
Write-Output ""
Write-Output "Note:"
Write-Output "  Newly generated repo-local commands / skills may require reopening the Claude Code / Codex session."
Write-Output ""
Write-Output "Next:"
if ($template -eq 'research-survey') {
    Write-Output "  /scope <topic>           → 研究スコープ定義"
    Write-Output "  /search                  → 文献検索"
    Write-Output "  /read                    → 論文分析"
    Write-Output "  /outline                 → サーベイ構成案"
    Write-Output "  /draft                   → 執筆"
    Write-Output "  /review                  → 品質レビュー"
    Write-Output "  /convert                 → Markdown → LaTeX 変換"
}
elseif ($template -eq 'codex-main') {
    Write-Output "  .agents/skills/codex-research            → コードベース調査"
    Write-Output "  .agents/skills/codex-plan                → plan/tasks 作成"
    Write-Output "  .agents/skills/codex-plan-review         → plan/tasks 2 段階レビュー"
    Write-Output "  .agents/skills/codex-implement           → 実装と検証"
    Write-Output "  .agents/skills/codex-impl-review         → 実装の APPROVED まで再レビュー"
    Write-Output "  .agents/skills/codex-review              → 単発レビュー"
    Write-Output "  .agents/skills/sonnet-dp-research-bridge → Sonnet 調査 bridge"
    Write-Output "  scripts/run-codex-plan-review.ps1        → plan review runner"
    Write-Output "  scripts/run-codex-impl-review.ps1        → impl review runner"
    Write-Output "  scripts/run-verify.sh or scripts/run-verify.ps1  → 検証"
}
else {
    Write-Output "  /research                → コードベース分析"
    Write-Output "  /plan <機能>             → 設計（Discussion Points を含む）"
    Write-Output "  /sonnet-dp-research      → Discussion Points を外部調査（省略可）"
    Write-Output "  /codex-plan-review       → Codex と設計議論"
    Write-Output "  /implement               → 実装"
}
