$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvPath = Join-Path $projectRoot ".venv-installer"
$buildDir = Join-Path $PSScriptRoot "build"
$distDir = Join-Path $PSScriptRoot "dist"
$installerScript = Join-Path $PSScriptRoot "SIFO_installer.iss"

Write-Host "==> Proyecto: $projectRoot"
Write-Host "==> Creando entorno de compilación..."
if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
}

$pythonExe = Join-Path $venvPath "Scripts\python.exe"

& $pythonExe -m pip install --upgrade pip setuptools wheel
& $pythonExe -m pip install -r (Join-Path $projectRoot "requirements.txt")
& $pythonExe -m pip install pyinstaller

Write-Host "==> Generando ejecutable con PyInstaller..."
Set-Location $projectRoot
$pyInstallerArgs = @(
    "--noconfirm",
    "--clean",
    "--onedir",
    "--windowed",
    "--name", "SIFO",
    "--distpath", $distDir,
    "--workpath", $buildDir,
    "--specpath", $buildDir,
    "--add-data", ("{0};datos" -f (Join-Path $projectRoot "datos")),
    "--add-data", ("{0};capas" -f (Join-Path $projectRoot "capas")),
    "--add-data", ("{0};recursos" -f (Join-Path $projectRoot "recursos")),
    "--add-data", ("{0};." -f (Join-Path $projectRoot "config.py")),
    (Join-Path $projectRoot "app.py")
)

& $pythonExe -m PyInstaller @pyInstallerArgs

if (-not (Test-Path $distDir)) {
    throw "No se pudo crear la carpeta dist del instalador."
}

$exeOutput = Join-Path $distDir "SIFO\SIFO.exe"
if (-not (Test-Path $exeOutput)) {
    throw "No se encontró el ejecutable generado en: $exeOutput"
}

Write-Host "==> Ejecutable generado en: $exeOutput"

if (Get-Command iscc -ErrorAction SilentlyContinue) {
    Write-Host "==> Compilando instalador con Inno Setup..."
    & iscc $installerScript
} else {
    Write-Warning "Inno Setup no está instalado o no está en PATH. Se generó el ejecutable, pero el instalador .exe no se compiló."
    Write-Host "Instalá Inno Setup desde: https://jrsoftware.org/isinfo.php"
    Write-Host "y luego ejecutá: iscc "$installerScript""
}

Write-Host "==> Proceso finalizado."
Write-Host "==> Si el instalador compiló, el archivo final estará en: $PSScriptRoot\output"
