param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$previousBuildPath = $env:PATH
$previousPythonPath = $env:PYTHONPATH
Push-Location $PSScriptRoot
try {
    $pythonExecutable = (Get-Command $Python).Source
    $pythonBase = & $pythonExecutable -c 'import sys; print(sys.base_prefix)'
    # Do not collect unrelated ICU/Qt DLLs from other applications on PATH.
    $env:PATH = @((Split-Path $pythonExecutable), $pythonBase, (Join-Path $env:SystemRoot 'System32'), $env:SystemRoot) -join ';'
    $env:PYTHONPATH = $null
    & $pythonExecutable -m PyInstaller --clean --noconfirm --windowed --onedir --name SchwiPet --icon assets\schwi.ico --add-data 'assets:assets' --distpath dist --workpath build main.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
    # CPython 3.10 ships an older VC runtime; Qt needs the matching newer DLLs.
    $qtDirectory = & $pythonExecutable -c 'from pathlib import Path; import PySide6; print(Path(PySide6.__file__).parent)'
    foreach ($dll in @('vcruntime140.dll', 'vcruntime140_1.dll')) {
        Copy-Item -LiteralPath (Join-Path $qtDirectory $dll) -Destination (Join-Path 'dist\SchwiPet\_internal' $dll) -Force
    }
    & $pythonExecutable collect_notices.py dist\SchwiPet
    if ($LASTEXITCODE -ne 0) { throw 'Dependency notices could not be collected.' }
    Copy-Item -LiteralPath README.md -Destination dist\SchwiPet\README.md -Force
    Copy-Item -LiteralPath README-macOS.md -Destination dist\SchwiPet\README-macOS.md -Force
    Write-Output "Built: $PSScriptRoot\dist\SchwiPet\SchwiPet.exe"
} finally {
    $env:PATH = $previousBuildPath
    $env:PYTHONPATH = $previousPythonPath
    Pop-Location
}
