# UEFN TOOLBELT - capture_uefn_window.ps1
# =========================================
# Zero-engine-cost screenshot: grabs the UEFN editor window via the Win32
# PrintWindow API. No in-engine render, no shader compilation, no VRAM
# allocation - safe on low-VRAM machines where take_high_res_screenshot
# OOM-crashes the editor (D3D12 "Out of video memory").
#
# Workflow (AI agent or human):
#   1. Position the camera via MCP set_viewport_camera / viewport_goto.
#   2. powershell -File capture_uefn_window.ps1 -OutPath shot.png
#   3. Read the PNG from disk.
#
# The window must not be minimized (background is fine).

param(
    [string]$OutPath = "$env:TEMP\uefn_capture.png",
    [string]$ProcessName = "UnrealEditorFortnite-Win64-Shipping"
)

Add-Type -AssemblyName System.Drawing

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Cap {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint nFlags);
    [DllImport("user32.dll")]
    public static extern bool IsIconic(IntPtr hWnd);
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

$proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $proc) { Write-Error "No $ProcessName window found"; exit 1 }

$hwnd = $proc.MainWindowHandle
if ([Win32Cap]::IsIconic($hwnd)) { Write-Error "Window is minimized - restore it first"; exit 2 }

$rect = New-Object Win32Cap+RECT
[Win32Cap]::GetWindowRect($hwnd, [ref]$rect) | Out-Null
$w = $rect.Right - $rect.Left
$h = $rect.Bottom - $rect.Top
if ($w -le 0 -or $h -le 0) { Write-Error "Bad window rect ${w}x${h}"; exit 3 }

$bmp = New-Object System.Drawing.Bitmap($w, $h)
$gfx = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $gfx.GetHdc()
# PW_RENDERFULLCONTENT (2) - captures DirectX-composited content
$ok = [Win32Cap]::PrintWindow($hwnd, $hdc, 2)
$gfx.ReleaseHdc($hdc)
$gfx.Dispose()

if (-not $ok) { Write-Error "PrintWindow failed"; $bmp.Dispose(); exit 4 }

$dir = Split-Path $OutPath -Parent
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
$bmp.Save($OutPath, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "saved: $OutPath (${w}x${h})"
