param(
    [ValidateSet('wsl2_loopback','linux_netem')]
    [string]$Profile = 'wsl2_loopback',
    [string]$Distro = 'Ubuntu',
    [string]$Protocols = 'kemtls,kemtls_pdk',
    [string]$Suites = 'crypto,handshake,oidc,load',
    [int]$Repeat = 1000,
    [int]$Warmup = 50,
    [ValidateSet('loopback','all')]
    [string]$ScenarioSet = 'loopback'
)

$ErrorActionPreference = 'Stop'

function Convert-ToWslPath([string]$windowsPath) {
    $resolved = (Resolve-Path -Path $windowsPath).Path
    $drive = $resolved.Substring(0,1).ToLowerInvariant()
    $rest = ($resolved.Substring(2) -replace '\\','/')
    return "/mnt/$drive$rest"
}

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    Write-Error 'wsl.exe is not available. Install WSL first.'
    exit 1
}

$repoWindows = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$repoWsl = Convert-ToWslPath $repoWindows

$runner = if ($Profile -eq 'linux_netem') { 'benchmarks/collect/run_all_netem.sh' } else { 'benchmarks/collect/run_all_wsl.sh' }

$cmd = @(
    'bash',
    '-lc',
    "cd '$repoWsl' && sed -i 's/\r$//' $runner benchmarks/setup_netem.sh benchmarks/collect/capture_segments.sh && bash $runner --profile '$Profile' --protocols '$Protocols' --suites '$Suites' --repeat $Repeat --warmup $Warmup --scenario-set '$ScenarioSet'"
)

Write-Host '[*] Executing in WSL:'
Write-Host "wsl -d $Distro $($cmd -join ' ')"

& wsl -d $Distro @cmd
if ($LASTEXITCODE -ne 0) {
    Write-Error "Benchmark run failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host '[*] Benchmark run completed successfully.'
