$ErrorActionPreference = "Stop"
node "$PSScriptRoot/lib/install-skill.mjs" @args
exit $LASTEXITCODE
