$ErrorActionPreference = "Stop"
node "$PSScriptRoot/lib/push-to-github.mjs" @args
exit $LASTEXITCODE
