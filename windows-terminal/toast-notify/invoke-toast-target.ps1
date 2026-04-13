param(
    [string]$UriString
)

$ErrorActionPreference = "Stop"

function Get-QueryParameters {
    param([Uri]$Uri)

    $result = @{}
    $query = $Uri.Query.TrimStart('?')
    if ([string]::IsNullOrWhiteSpace($query)) {
        return $result
    }

    foreach ($pair in $query.Split('&')) {
        if ([string]::IsNullOrWhiteSpace($pair)) {
            continue
        }

        $parts = $pair.Split('=', 2)
        $name = [Uri]::UnescapeDataString($parts[0])
        $value = ""
        if ($parts.Count -gt 1) {
            $value = [Uri]::UnescapeDataString($parts[1])
        }
        $result[$name] = $value
    }

    return $result
}

try {
    if ([string]::IsNullOrWhiteSpace($UriString)) {
        exit 0
    }

    $uri = [Uri]$UriString
    $query = Get-QueryParameters -Uri $uri
    $cwd = $query["cwd"]

    $scriptRoot = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
    $focusScript = Join-Path $scriptRoot "focus-terminal.ps1"
    if (-not (Test-Path -LiteralPath $focusScript)) {
        exit 0
    }

    & $focusScript -Cwd $cwd
    exit 0
} catch {
    exit 0
}
