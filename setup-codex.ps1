param([switch]$DesktopOnly)
$ErrorActionPreference = 'Stop'

$setupPython = $null
$pythonArgs = @()
foreach ($candidate in @('py', 'python', 'python3')) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if (-not $command) { continue }
    $candidateArgs = @()
    if ($candidate -eq 'py') { $candidateArgs = @('-3') }
    & $command.Source @candidateArgs -c 'import sys; sys.exit(sys.version_info < (3, 11))'
    if ($LASTEXITCODE -eq 0) {
        $setupPython = $command.Source
        $pythonArgs = $candidateArgs
        break
    }
}
if (-not $setupPython) { throw 'Install Python 3.11 or newer, then rerun setup.' }

$installer = Join-Path $PSScriptRoot 'setup-codex.py'
$temporaryInstaller = $null
try {
    if (-not (Test-Path -LiteralPath $installer)) {
        $temporaryInstaller = [IO.Path]::GetTempFileName()
        $installer = $temporaryInstaller
        Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/trungdlp/aicheap-setup/HEAD/setup-codex.py' -OutFile $installer
    }
    $setupArgs = @($installer)
    if ($DesktopOnly) { $setupArgs += '--desktop-only' }
    & $setupPython @pythonArgs @setupArgs
    $setupExitCode = $LASTEXITCODE
} finally {
    if ($temporaryInstaller) { Remove-Item -LiteralPath $temporaryInstaller -Force }
}
exit $setupExitCode
