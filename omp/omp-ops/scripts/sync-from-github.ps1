$ErrorActionPreference = "Stop"
node "$PSScriptRoot/lib/sync-from-github.mjs" @args
exit $LASTEXITCODE
