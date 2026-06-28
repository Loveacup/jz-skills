$ErrorActionPreference = "Stop"
node "$PSScriptRoot/lib/check-version.mjs" @args
exit $LASTEXITCODE
