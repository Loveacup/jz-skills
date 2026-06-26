$ErrorActionPreference = "Stop"
node "$PSScriptRoot/lib/sync-from-official.mjs" @args
exit $LASTEXITCODE
