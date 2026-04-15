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
$currentCycle = [int]$sessionsState['current']['impl_review']['cycle'] + 1
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
$null = Get-TextHash -Text $bundleText
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
