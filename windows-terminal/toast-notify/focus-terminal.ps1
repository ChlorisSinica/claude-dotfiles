param(
    [string]$Cwd
)

$ErrorActionPreference = "Stop"

$signature = @"
using System;
using System.Runtime.InteropServices;
public static class NativeWindow {
    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool IsIconic(IntPtr hWnd);
}
"@

try {
    Add-Type -TypeDefinition $signature -ErrorAction SilentlyContinue | Out-Null
} catch {
    # Ignore duplicate type registration across repeated runs.
}

function Get-FolderLabel {
    param([string]$PathValue)

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return $null
    }

    $trimmed = $PathValue.TrimEnd('\', '/')
    $leaf = Split-Path -Path $trimmed -Leaf
    if ([string]::IsNullOrWhiteSpace($leaf)) {
        return $trimmed
    }
    return $leaf
}

function Get-TerminalCandidates {
    Get-Process -Name WindowsTerminal -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 }
}

function Select-TerminalProcess {
    param(
        [Parameter(Mandatory = $true)]
        [System.Diagnostics.Process[]]$Processes,
        [string]$FolderLabel
    )

    if ([string]::IsNullOrWhiteSpace($FolderLabel)) {
        return $Processes | Sort-Object StartTime -Descending | Select-Object -First 1
    }

    $titleMatches = $Processes | Where-Object {
        $_.MainWindowTitle -and $_.MainWindowTitle.IndexOf($FolderLabel, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
    } | Sort-Object StartTime -Descending

    if ($titleMatches) {
        return $titleMatches | Select-Object -First 1
    }

    return $Processes | Sort-Object StartTime -Descending | Select-Object -First 1
}

try {
    $processes = @(Get-TerminalCandidates)
    if (-not $processes -or $processes.Count -eq 0) {
        exit 0
    }

    $folderLabel = Get-FolderLabel -PathValue $Cwd
    $target = Select-TerminalProcess -Processes $processes -FolderLabel $folderLabel
    if ($null -eq $target) {
        exit 0
    }

    $handle = $target.MainWindowHandle
    if ($handle -eq 0) {
        exit 0
    }

    if ([NativeWindow]::IsIconic($handle)) {
        [void][NativeWindow]::ShowWindowAsync($handle, 9)
    } else {
        [void][NativeWindow]::ShowWindowAsync($handle, 5)
    }

    [void][NativeWindow]::SetForegroundWindow($handle)
    exit 0
} catch {
    exit 0
}
