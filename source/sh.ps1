param(
    [string]$ScriptFile,
    [string[]]$RemainingArgs
)

if (-not $ScriptFile) {
    python "$PSScriptRoot\sh.py"
    exit $LASTEXITCODE
}

python "$PSScriptRoot\sh.py" $ScriptFile @RemainingArgs
exit $LASTEXITCODE
