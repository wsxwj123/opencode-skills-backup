$logFile = "C:\Users\Administrator\.config\opencode\skills\skill-manager\data\automation.log"
$reportFile = "C:\Users\Administrator\.config\opencode\skills\skill-manager\data\latest_weekly_report.json"
$pythonScript = "C:\Users\Administrator\.config\opencode\skills\skill-manager\scripts\scan_and_check.py"
$targetDir = "C:\Users\Administrator\.config\opencode\skills"

$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $logFile -Value "[$date] Starting weekly skill check..."

try {
    # Run python script and capture output to file
    $output = python $pythonScript $targetDir
    $output | Out-File -FilePath $reportFile -Encoding utf8
    
    Add-Content -Path $logFile -Value "[$date] Check completed. Report saved to $reportFile"
} catch {
    Add-Content -Path $logFile -Value "[$date] Error during execution: $_"
}
