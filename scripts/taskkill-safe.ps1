param(
    [Parameter(Position = 0)]
    [Alias('Pid')]
    [string]$TargetPid,

    [int]$Port,

    [string[]]$ProcessName,

    [switch]$Force = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-ProcessIds {
    param(
        [string]$PidValue,
        [int]$PortValue,
        [string[]]$NameValue
    )

    $resolved = @()

    if ($PidValue) {
        $trimmed = $PidValue.Trim()
        if ($trimmed -notmatch '^[0-9]+$') {
            throw "PID must be numeric. Received: '$PidValue'"
        }

        $resolved += [int]$trimmed
    }

    if ($PortValue -gt 0) {
        $tcp = Get-NetTCPConnection -LocalPort $PortValue -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique

        foreach ($ownerPid in $tcp) {
            if ($ownerPid -isnot [int]) {
                $ownerPid = [int]$ownerPid
            }
            $resolved += $ownerPid
        }
    }

    foreach ($name in @($NameValue)) {
        if ([string]::IsNullOrWhiteSpace($name)) { continue }
        $matching = Get-CimInstance Win32_Process -Filter "Name = '$name'" -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty ProcessId

        foreach ($match in @($matching)) {
            $resolved += [int]$match
        }
    }

    if (-not $resolved) {
        throw "No PID, port, or process name was supplied. Use -Pid, -Port, or -ProcessName."
    }

    $resolved | Sort-Object -Unique
}

$targetPids = Resolve-ProcessIds -PidValue $TargetPid -PortValue $Port -NameValue $ProcessName

foreach ($targetPid in $targetPids) {
    $process = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
    if (-not $process) {
        Write-Warning "PID $targetPid is not running; skipping."
        continue
    }

    $processName = $process.ProcessName
    if ($Force) {
        Stop-Process -Id $targetPid -Force -ErrorAction Stop
    }
    else {
        Stop-Process -Id $targetPid -ErrorAction Stop
    }

    Write-Host "Stopped PID $targetPid ($processName)"
}
