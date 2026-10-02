# Script de Instalación para HGON Monitores
# Ejecutar con PowerShell como Administrador

$AppDir = "C:\HGON_Monitores"
$ExeSource = ".\dist\AppPacientes.exe"
$ConfigSource = ".\config.py"

Write-Host "--- Instalando HGON Monitores ---" -ForegroundColor Cyan

# 1. Crear directorio
if (!(Test-Path $AppDir)) {
    New-Item -Path $AppDir -ItemType Directory
    Write-Host "[OK] Directorio creado en $AppDir"
}

# 2. Copiar archivos
if (Test-Path $ExeSource) {
    Copy-Item $ExeSource -Destination $AppDir -Force
    Write-Host "[OK] Ejecutable copiado."
} else {
    Write-Error "No se encontró el ejecutable en $ExeSource. Asegúrese de haber compilado primero."
    exit
}

if (Test-Path $ConfigSource) {
    Copy-Item $ConfigSource -Destination $AppDir -Force
    Write-Host "[OK] Archivo de configuración copiado."
}

# 3. Crear Acceso Directo en el Escritorio
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\HGON Monitores.lnk")
$Shortcut.TargetPath = "$AppDir\AppPacientes.exe"
$Shortcut.WorkingDirectory = $AppDir
$Shortcut.IconLocation = "$AppDir\AppPacientes.exe,0"
$Shortcut.Save()
Write-Host "[OK] Acceso directo creado en el Escritorio."

# 4. Crear Acceso Directo en Inicio (Auto-arranque)
$StartupPath = [System.Environment]::GetFolderPath("Startup")
$StartupShortcut = $WshShell.CreateShortcut("$StartupPath\HGON Monitores.lnk")
$StartupShortcut.TargetPath = "$AppDir\AppPacientes.exe"
$StartupShortcut.WorkingDirectory = $AppDir
$StartupShortcut.Save()
Write-Host "[OK] La aplicación se iniciará automáticamente al encender la PC."

Write-Host "`nInstalación completada con éxito." -ForegroundColor Green
Write-Host "Puede configurar las pantallas editando $AppDir\config.py"
