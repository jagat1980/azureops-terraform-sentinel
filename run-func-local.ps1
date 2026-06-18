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
func start --port 7071 *> '..\func-start.log'
