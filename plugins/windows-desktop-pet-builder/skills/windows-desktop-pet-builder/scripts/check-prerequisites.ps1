param(
    [string] $PhotoFolder
)

$ErrorActionPreference = 'Stop'

if ($env:OS -ne 'Windows_NT') {
    throw 'This skill requires Windows.'
}

$frameworkDirectory = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319'
$wpfDirectory = Join-Path $frameworkDirectory 'WPF'
$checks = @(
    [pscustomobject]@{
        Name = 'Windows PowerShell'
        Required = $true
        Found = $PSVersionTable.PSVersion.Major -ge 5
        Detail = $PSVersionTable.PSVersion.ToString()
    },
    [pscustomobject]@{
        Name = 'C# compiler'
        Required = $true
        Found = Test-Path -LiteralPath (Join-Path $frameworkDirectory 'csc.exe')
        Detail = Join-Path $frameworkDirectory 'csc.exe'
    },
    [pscustomobject]@{
        Name = 'WPF PresentationFramework'
        Required = $true
        Found = Test-Path -LiteralPath (Join-Path $wpfDirectory 'PresentationFramework.dll')
        Detail = Join-Path $wpfDirectory 'PresentationFramework.dll'
    },
    [pscustomobject]@{
        Name = 'Git'
        Required = $false
        Found = $null -ne (Get-Command git.exe -ErrorAction SilentlyContinue)
        Detail = 'Optional; required only for version control and GitHub publishing.'
    }
)

if ($PhotoFolder) {
    $photoFolderExists = Test-Path -LiteralPath $PhotoFolder -PathType Container
    $photoCount = 0
    if ($photoFolderExists) {
        $extensions = @('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff')
        $photoCount = @(
            Get-ChildItem -LiteralPath $PhotoFolder -File -Recurse |
                Where-Object { $extensions -contains $_.Extension.ToLowerInvariant() }
        ).Count
    }

    $checks += [pscustomobject]@{
        Name = 'Source photos'
        Required = $true
        Found = $photoFolderExists -and $photoCount -gt 0
        Detail = if ($photoFolderExists) {
            "$photoCount supported image file(s) in $PhotoFolder"
        }
        else {
            "Folder not found: $PhotoFolder"
        }
    }
}

$checks | Format-Table Name, Required, Found, Detail -AutoSize

$failed = @($checks | Where-Object { $_.Required -and -not $_.Found })
if ($failed.Count -gt 0) {
    Write-Error ('Missing required prerequisites: ' + (($failed.Name) -join ', '))
    exit 1
}

Write-Output 'Prerequisite check passed.'
exit 0
