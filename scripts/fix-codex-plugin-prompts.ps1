[CmdletBinding()]
param(
    [string]$PluginsRoot = ""
)

$ErrorActionPreference = "Stop"
$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)

if (-not $PluginsRoot) {
    $homeRoot = if ($env:USERPROFILE) {
        $env:USERPROFILE
    }
    elseif ([Environment]::GetFolderPath("UserProfile")) {
        [Environment]::GetFolderPath("UserProfile")
    }
    else {
        $HOME
    }
    $PluginsRoot = Join-Path $homeRoot ".codex\.tmp\plugins\plugins"
}

$promptMap = [ordered]@{
    "build-ios-apps" = "Design App Intents, build or refactor SwiftUI UI, audit performance, or debug iOS apps in Simulator."
    "life-science-research" = "Route life-science research tasks, synthesize evidence, and use bounded parallel analysis when it materially helps."
}

function Update-PluginPrompt {
    param(
        [Parameter(Mandatory = $true)][string]$PluginName,
        [Parameter(Mandatory = $true)][string]$Prompt
    )

    $manifestPath = Join-Path $PluginsRoot "$PluginName\.codex-plugin\plugin.json"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        Write-Output "SKIP  $PluginName (manifest not found)"
        return
    }

    if ($Prompt.Length -gt 128) {
        throw "defaultPrompt for $PluginName exceeds 128 characters."
    }

    $json = Get-Content -LiteralPath $manifestPath -Encoding UTF8 -Raw | ConvertFrom-Json
    $currentPrompt = [string]$json.interface.defaultPrompt
    if ($currentPrompt -eq $Prompt) {
        Write-Output "SKIP  $PluginName (already fixed)"
        return
    }

    $json.interface.defaultPrompt = $Prompt
    $output = ($json | ConvertTo-Json -Depth 20) + "`n"
    [System.IO.File]::WriteAllText($manifestPath, $output, $Utf8NoBom)
    Write-Output "UPDATE $PluginName"
    Write-Output "  Path: $manifestPath"
    Write-Output "  Prompt length: $($Prompt.Length)"
}

foreach ($entry in $promptMap.GetEnumerator()) {
    Update-PluginPrompt -PluginName $entry.Key -Prompt $entry.Value
}
