# Create CollabTrans shortcut with environment variables
param(
    [string]$TargetPath,
    [string]$ShortcutPath,
    [string]$WorkingDirectory,
    [string]$Description
)

# Create WScript.Shell object
$WshShell = New-Object -comObject WScript.Shell

# Create shortcut
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $WorkingDirectory
$Shortcut.Description = $Description

# Set environment variables for the shortcut
# Note: This requires creating a batch file wrapper or using a different approach
# For now, we'll create a simple shortcut and rely on the application's built-in config

$Shortcut.Save()

Write-Host "Created shortcut: $ShortcutPath"
Write-Host "Target: $TargetPath"
Write-Host "Working Directory: $WorkingDirectory"
