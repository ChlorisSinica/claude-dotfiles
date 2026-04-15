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