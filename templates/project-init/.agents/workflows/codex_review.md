---
description: Automated Code Review and Refinement with Codex
---

# Automated Code Review and Refinement Workflow

This workflow automatically uses the Codex CLI to review recent code changes, saves the session ID to `.agents/sessions.json` for persistence, solicits follow-up refinement if needed, and loops the review process.

1. Retrieve the latest uncommitted or staged changes for review.
```bash
git status --short
```

2. Request an automated code review from Codex and capture the output to extract the Session ID.
```powershell
$reviewOutput = codex review "Check for best practices, potential bugs, and stylistic issues."
Write-Output $reviewOutput

$sessionId = [regex]::Match($reviewOutput, '([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})').Groups[1].Value
if ($sessionId) {
    $sessionsFile = ".agents/sessions.json"
    $sessions = if (Test-Path $sessionsFile) { Get-Content $sessionsFile -Raw | ConvertFrom-Json } else { @{} }
    $sessions.last_review = $sessionId
    $sessions | ConvertTo-Json -Depth 5 | Set-Content $sessionsFile
    Write-Host "Saved Session ID ($sessionId) to sessions.json"
} else {
    Write-Host "Warning: Could not extract Session ID."
}
```

3. Based on the review output, instruct Codex to iteratively apply fixes.
```powershell
$sessionsFile = ".agents/sessions.json"
if (Test-Path $sessionsFile) {
    $sessions = Get-Content $sessionsFile -Raw | ConvertFrom-Json
    $sessionId = $sessions.last_review
    if ($sessionId) {
        Write-Host "Resuming session $sessionId..."
        codex exec resume --full-auto $sessionId "Please apply the suggested fixes from the review to the codebase."
    } else {
        codex exec resume --full-auto --last "Please apply the suggested fixes from the review to the codebase."
    }
} else {
    codex exec resume --full-auto --last "Please apply the suggested fixes from the review to the codebase."
}
```

4. Check the status after the fixes are applied.
```bash
git diff
```
