param(
    [Parameter(Mandatory=$true)][string]$Msi,
    [Parameter(Mandatory=$true)][string]$ProductCode,
    [Parameter(Mandatory=$true)][string]$Output
)
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$workspaceRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot '..'))
$qaRoot = [IO.Path]::GetFullPath($Output)
$installPath = [IO.Path]::GetFullPath((Join-Path $workspaceRoot ('work\msi-installed-test\' + [IO.Path]::GetFileName($qaRoot) + '\SchwiPet')))
if (-not $installPath.StartsWith($workspaceRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Installer test target is outside the workspace.'
}
$msiPath = (Resolve-Path -LiteralPath $Msi).Path
$desktopLink = Join-Path ([Environment]::GetFolderPath('DesktopDirectory')) '休比桌宠.lnk'
$startFolder = Join-Path ([Environment]::GetFolderPath('Programs')) '休比桌宠'
$productKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{' + $ProductCode.Trim('{}') + '}'
if ((Test-Path -LiteralPath $installPath) -or (Test-Path -LiteralPath $desktopLink) -or (Test-Path -LiteralPath $startFolder) -or (Test-Path -LiteralPath $productKey)) {
    throw 'A previous installation or shortcut exists; the test will not replace it.'
}
New-Item -ItemType Directory -Path $qaRoot -Force | Out-Null
$checks = [System.Collections.Generic.List[string]]::new()
$installed = $false
$result = @{ok=$false; checks=$checks}
try {
    $installLog = Join-Path $qaRoot 'install.log'
    $args = '/i "' + $msiPath + '" /qn /norestart INSTALLFOLDER="' + $installPath + '" /L*v "' + $installLog + '"'
    $process = Start-Process -FilePath msiexec.exe -ArgumentList $args -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -notin @(0,3010)) { throw "MSI install returned $($process.ExitCode)" }
    $installed = $true
    $checks.Add('MSI installs successfully for the current user')
    if (-not (Test-Path -LiteralPath $desktopLink) -or -not (Test-Path -LiteralPath (Join-Path $startFolder '休比桌宠.lnk'))) {
        throw 'Desktop or Start menu shortcut is missing.'
    }
    $checks.Add('Desktop and Start menu shortcuts created')
    $source = Join-Path $repoRoot 'dist\SchwiPet'
    foreach ($file in Get-ChildItem -LiteralPath $source -Recurse -File) {
        $relative = [IO.Path]::GetRelativePath($source, $file.FullName)
        $target = Join-Path $installPath $relative
        if (-not (Test-Path -LiteralPath $target)) { throw "Missing installed file: $relative" }
        if ((Get-FileHash -LiteralPath $target).Hash -ne (Get-FileHash -LiteralPath $file.FullName).Hash) {
            throw "Installed file differs: $relative"
        }
    }
    $checks.Add('All installed application files match the build')
    $guiOutput = Join-Path $qaRoot 'installed-gui'
    $dataDir = Join-Path $qaRoot 'settings'
    $appArgs = '--self-test "' + $guiOutput + '" --data-dir "' + $dataDir + '"'
    $app = Start-Process -FilePath (Join-Path $installPath 'SchwiPet.exe') -ArgumentList $appArgs -WindowStyle Hidden -PassThru -Wait
    if ($app.ExitCode -ne 0) { throw "Installed application test returned $($app.ExitCode)" }
    $guiReport = Get-Content -LiteralPath (Join-Path $guiOutput 'smoke-test.json') -Raw | ConvertFrom-Json
    if (-not $guiReport.ok) { throw 'Installed GUI checks failed.' }
    $checks.Add('Installed application passes its native GUI checks')
    $settingsHash = (Get-FileHash -LiteralPath (Join-Path $dataDir 'settings.json')).Hash
    $removeLog = Join-Path $qaRoot 'uninstall.log'
    $removeArgs = '/x {' + $ProductCode.Trim('{}') + '} /qn /norestart /L*v "' + $removeLog + '"'
    $remove = Start-Process -FilePath msiexec.exe -ArgumentList $removeArgs -WindowStyle Hidden -PassThru -Wait
    if ($remove.ExitCode -notin @(0,3010)) { throw "MSI uninstall returned $($remove.ExitCode)" }
    $installed = $false
    if ((Test-Path -LiteralPath $desktopLink) -or (Test-Path -LiteralPath $startFolder) -or (Test-Path -LiteralPath (Join-Path $installPath 'SchwiPet.exe'))) {
        throw 'Uninstall left application files or shortcuts.'
    }
    $checks.Add('Uninstall removes the application and its shortcuts')
    if ((Get-FileHash -LiteralPath (Join-Path $dataDir 'settings.json')).Hash -ne $settingsHash) { throw 'Settings changed during uninstall.' }
    $checks.Add('User settings are preserved')
    $result.ok = $true
} catch {
    $result.error = $_.Exception.Message
} finally {
    if ($installed) {
        $cleanup = Start-Process -FilePath msiexec.exe -ArgumentList ('/x {' + $ProductCode.Trim('{}') + '} /qn /norestart') -WindowStyle Hidden -PassThru -Wait
        $result.cleanup_exit = $cleanup.ExitCode
    }
    $result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $qaRoot 'installer-verification.json') -Encoding utf8
    $result | ConvertTo-Json -Depth 5
}
if (-not $result.ok) { exit 1 }
