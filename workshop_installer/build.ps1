param([string]$Output = 'dist')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $root
try {
    python -m PyInstaller --noconfirm --clean --onefile --windowed --name SCT_Setup `
        --paths "$root" --distpath $Output `
        "$root\workshop_installer\entrypoint.py"
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
} finally { Pop-Location }
