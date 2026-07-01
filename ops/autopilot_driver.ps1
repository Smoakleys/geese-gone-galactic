<#
  External watchdog — the layer that survives full process death.

  The Stop hook (.claude/hooks/keep_going.py) keeps a SINGLE session from ending its
  turn. This driver keeps the PROCESS alive: if the Claude Code process itself exits
  or crashes, the loop relaunches it. Together they mean "the build kept running
  without the user" is enforced at both the turn level and the process level.

  Usage (from anywhere):
      pwsh ops/autopilot_driver.ps1

  It creates ops/AUTOPILOT_ON (enters enforced autonomous mode) and relaunches the
  agent until the ops/STOP kill switch appears. To stop everything:
      New-Item -ItemType File ops/STOP      # or: touch ops/STOP

  NOTE: adjust $ClaudeArgs to match your CLI (headless print mode + permission mode).
#>

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot          # ops/ -> repo root
$stop = Join-Path $repo "ops\STOP"
$go   = Join-Path $repo "ops\AUTOPILOT_ON"

$Prompt = @'
Autonomous GGG resume. cd into the repo, read docs/HANDOFF.md and ops/backlog.md, then
continue the harness build per the standing mandate (memory: ggg-autonomous-mandate). Do
NOT wait for the user. Run `python -m pytest tests/ -q` first; then pick the next
highest-value increment and drive it branch -> test -> PR -> merge. Do not stop.
'@

# Enter enforced autonomous mode; clear any stale kill switch.
if (Test-Path $stop) { Remove-Item $stop -Force }
New-Item -ItemType File -Path $go -Force | Out-Null
Write-Host "[driver] autonomous mode ON (ops/AUTOPILOT_ON). Kill switch: create ops/STOP."

# Match your installed CLI. Headless print mode keeps it non-interactive; the Stop hook
# drives the turn loop inside each invocation, this while-loop recovers from process exit.
$ClaudeArgs = @('-p', $Prompt, '--dangerously-skip-permissions')

while (-not (Test-Path $stop)) {
    Write-Host "[driver] launching claude session at $(Get-Date -Format o)"
    try {
        & claude @ClaudeArgs
    } catch {
        Write-Warning "[driver] session error: $($_.Exception.Message)"
    }
    if (Test-Path $stop) { break }
    Write-Host "[driver] session exited; relaunching in 5s (create ops/STOP to end)"
    Start-Sleep -Seconds 5
}

Remove-Item $go -Force -ErrorAction SilentlyContinue
Write-Host "[driver] ops/STOP found — autonomous mode OFF. Done."
