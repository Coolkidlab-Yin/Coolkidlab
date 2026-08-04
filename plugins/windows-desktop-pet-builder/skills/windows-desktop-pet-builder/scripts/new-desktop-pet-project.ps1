param(
    [Parameter(Mandatory = $true)]
    [string] $ProjectPath,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $PetName
)

$ErrorActionPreference = 'Stop'

$resolvedProjectPath = [IO.Path]::GetFullPath($ProjectPath)
if (Test-Path -LiteralPath $resolvedProjectPath) {
    $existing = @(Get-ChildItem -LiteralPath $resolvedProjectPath -Force)
    if ($existing.Count -gt 0) {
        throw "Target folder is not empty: $resolvedProjectPath"
    }
}
else {
    New-Item -ItemType Directory -Path $resolvedProjectPath | Out-Null
}

$directories = @(
    'assets\photos',
    'assets\sprites',
    'src',
    'tests',
    'docs',
    'logs',
    'dist'
)

foreach ($relativeDirectory in $directories) {
    New-Item -ItemType Directory -Force -Path (
        Join-Path $resolvedProjectPath $relativeDirectory
    ) | Out-Null
}

$utf8NoBom = New-Object Text.UTF8Encoding($false)
$configuration = [ordered]@{
    petName = $PetName
    visualStyle = 'semi-realistic 2.5D'
    autonomySeconds = [ordered]@{
        minimum = 50
        maximum = 300
    }
    sourcePhotos = 'assets/photos'
    generatedSprites = 'assets/sprites'
    createdUtc = [DateTime]::UtcNow.ToString('o')
}

$configurationPath = Join-Path $resolvedProjectPath 'pet-project.json'
[IO.File]::WriteAllText(
    $configurationPath,
    ($configuration | ConvertTo-Json -Depth 4),
    $utf8NoBom
)

$gitignore = @'
assets/photos/**
!assets/photos/.gitkeep
dist/
logs/
*.log
.env
.env.*
'@
[IO.File]::WriteAllText(
    (Join-Path $resolvedProjectPath '.gitignore'),
    $gitignore,
    $utf8NoBom
)

[IO.File]::WriteAllText(
    (Join-Path $resolvedProjectPath 'assets\photos\.gitkeep'),
    '',
    $utf8NoBom
)

$templatePath = Join-Path (Split-Path -Parent $PSScriptRoot) 'assets\project-brief-template.md'
if (-not (Test-Path -LiteralPath $templatePath)) {
    throw "Project brief template not found: $templatePath"
}

$brief = [IO.File]::ReadAllText($templatePath).Replace('{{PET_NAME}}', $PetName)
[IO.File]::WriteAllText(
    (Join-Path $resolvedProjectPath 'docs\project-brief.md'),
    $brief,
    $utf8NoBom
)

Write-Output "Project created: $resolvedProjectPath"
Write-Output "Configuration: $configurationPath"
Write-Output 'Copy private source photos into assets\photos before running the build workflow.'
