# fresh_clone_check.ps1 - run the whole project from a clean clone (Week 5 Day 1 and Day 4).
# It clones the repository with its submodules, makes a new virtual environment, installs
# requirements.txt, runs the one-command pipeline and then the evidence gate in strict mode.
# This script has not been run by the person who wrote it; if a step fails, send the output.
#
#   powershell -ExecutionPolicy Bypass -File .\scripts\fresh_clone_check.ps1 -Branch main
#   powershell -ExecutionPolicy Bypass -File .\scripts\fresh_clone_check.ps1 -Branch week4-one-command -Keep

param(
  [string]$Repo = "https://github.com/VaibhavGautam01/PQC-Migration-System",
  [string]$Branch = "main",
  [switch]$Keep
)

$ErrorActionPreference = "Stop"
$dir = Join-Path $env:TEMP ("pqc-fresh-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
Write-Host "Cloning $Branch into $dir"
git clone --recurse-submodules --branch $Branch $Repo $dir
Set-Location $dir

Write-Host "`nCreating a new virtual environment"
python -m venv venv
& .\venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
& .\venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host "`nRunning the pipeline (project both)"
& .\venv\Scripts\python.exe run_pipeline.py --project both
$pipeline = $LASTEXITCODE

Write-Host "`nEvidence gate, strict (this fails until the Q6 and Q7 records are in the evidence format)"
& .\venv\Scripts\python.exe -m src.evidence_gate --strict
$gate = $LASTEXITCODE

Write-Host "`nRepository consistency check"
& .\venv\Scripts\python.exe scripts\repo_check.py
$check = $LASTEXITCODE

Write-Host "`n=== Result (0 = pass) ==="
Write-Host "pipeline: $pipeline    evidence gate (strict): $gate    repo_check: $check"
Write-Host "Clone folder: $dir"
if (-not $Keep) { Write-Host "Delete it when you are done: Remove-Item -Recurse -Force '$dir'" }
if ($pipeline -ne 0) { exit 1 }
