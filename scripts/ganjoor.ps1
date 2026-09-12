# ganjoor.ps1 — thin Windows shim; forwards all args to scripts/ganjoor.py.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = Join-Path $ScriptDir "ganjoor.py"
if (Get-Command py -ErrorAction SilentlyContinue) { py -3 $target @args; exit $LASTEXITCODE }
if (Get-Command python -ErrorAction SilentlyContinue) { python $target @args; exit $LASTEXITCODE }
python3 $target @args
exit $LASTEXITCODE
