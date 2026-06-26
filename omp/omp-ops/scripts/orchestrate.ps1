$ErrorActionPreference = "Stop"
node "$PSScriptRoot/lib/orchestrate.mjs" @args
exit $LASTEXITCODE
