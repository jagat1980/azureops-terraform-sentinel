$ErrorActionPreference = 'Stop'
Set-Location 'C:\myailearn\projects\azureops-test-harness\azureops-brain'
Get-Content '..\.env' | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
        $parts = $line.Split('=', 2)
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim().Trim('"').Trim("'"), 'Process')
    }
}
$env:AI_PROVIDER = 'azure_openai'
$env:PATH = "C:\Users\azureadmin\AppData\Roaming\npm;C:\myailearn\projects\azureops-test-harness\azureops-brain\.venv\Scripts;" + $env:PATH
func start --port 7071
