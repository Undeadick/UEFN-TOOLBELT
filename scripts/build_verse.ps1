# UEFN TOOLBELT - build_verse.ps1
# =========================================
# Trigger "Build Verse Code" in the UEFN editor from outside the process.
#
# Epic exposes no Python API to start a Verse build (see PIPELINE.md, phase 5),
# so this closes the last manual click in the AI build loop: focus the UEFN
# window and send its built-in hotkey Ctrl+Shift+B.
#
# Workflow (AI agent):
#   1. verse_write_file / verse_template_deploy  (deploy .verse via MCP)
#   2. powershell -File build_verse.ps1
#   3. poll tb.run("verse_build_status") until a fresh SUCCESS/FAILED appears
#   4. on FAILED: verse_patch_errors -> fix -> redeploy -> goto 2
#
# The window must not be minimized. Focus is briefly stolen from the user.

param(
    [string]$ProcessName = "UnrealEditorFortnite-Win64-Shipping"
)

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Bv {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
}
"@

$proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $proc) { Write-Error "No $ProcessName window found"; exit 1 }

$hwnd = $proc.MainWindowHandle
if ([Win32Bv]::IsIconic($hwnd)) { [Win32Bv]::ShowWindow($hwnd, 9) | Out-Null }  # SW_RESTORE

[Win32Bv]::SetForegroundWindow($hwnd) | Out-Null
Start-Sleep -Milliseconds 600

if ([Win32Bv]::GetForegroundWindow() -ne $hwnd) {
    Write-Error "Could not focus the UEFN window (foreground lock?)"; exit 2
}

# Ctrl+Shift+B = Build Verse Code (UEFN built-in shortcut)
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait("^+b")
Write-Output "sent Ctrl+Shift+B to UEFN - poll verse_build_status for the result"
