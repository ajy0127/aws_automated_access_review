param(
    [string]$Region = "us-east-1",
    [string]$Profile = ""
)

$ErrorActionPreference = "Continue"

# Set AWS profile if specified
$awsProfileArgs = @()
if ($Profile) {
    $awsProfileArgs += "--profile", $Profile
    Write-Host "Using AWS profile: $Profile"
}

Write-Host "=== AWS Services Configuration Proof ===" -ForegroundColor Cyan
Write-Host "Region: $Region"
Write-Host ""

# Security Hub - Detailed check
Write-Host "1. SECURITY HUB:" -ForegroundColor Yellow
Write-Host "Command: aws securityhub get-enabled-standards --region $Region"
try {
    $result = aws securityhub get-enabled-standards --region $Region @awsProfileArgs 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Security Hub is ENABLED" -ForegroundColor Green
        Write-Host "Standards enabled:" -ForegroundColor Green
        $standards = $result | ConvertFrom-Json
        foreach ($standard in $standards.StandardsSubscriptions) {
            Write-Host "  - $($standard.StandardsArn)" -ForegroundColor Gray
        }
    } else {
        Write-Host "❌ Security Hub NOT enabled" -ForegroundColor Red
        Write-Host "Error: $result" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Error checking Security Hub: $_" -ForegroundColor Red
}
Write-Host ""

# IAM Access Analyzer - Detailed check
Write-Host "2. IAM ACCESS ANALYZER:" -ForegroundColor Yellow
Write-Host "Command: aws accessanalyzer list-analyzers --region $Region"
try {
    $result = aws accessanalyzer list-analyzers --region $Region @awsProfileArgs 2>&1
    if ($LASTEXITCODE -eq 0) {
        $analyzers = $result | ConvertFrom-Json
        if ($analyzers.analyzers.Count -gt 0) {
            Write-Host "✅ IAM Access Analyzer is ENABLED" -ForegroundColor Green
            Write-Host "Analyzers found:" -ForegroundColor Green
            foreach ($analyzer in $analyzers.analyzers) {
                Write-Host "  - Name: $($analyzer.name), Status: $($analyzer.status)" -ForegroundColor Gray
            }
        } else {
            Write-Host "❌ No analyzers found" -ForegroundColor Red
        }
    } else {
        Write-Host "❌ IAM Access Analyzer NOT accessible" -ForegroundColor Red
        Write-Host "Error: $result" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Error checking IAM Access Analyzer: $_" -ForegroundColor Red
}
Write-Host ""

# Amazon SES - Detailed check
Write-Host "3. AMAZON SES:" -ForegroundColor Yellow
Write-Host "Command: aws ses get-send-quota --region $Region"
try {
    $result = aws ses get-send-quota --region $Region @awsProfileArgs 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Amazon SES is ENABLED" -ForegroundColor Green
        $quota = $result | ConvertFrom-Json
        Write-Host "  - Max 24 Hour Send: $($quota.Max24HourSend)" -ForegroundColor Gray
        Write-Host "  - Max Send Rate: $($quota.MaxSendRate)" -ForegroundColor Gray
        
        # Check verified identities
        Write-Host "Checking verified email identities..." -ForegroundColor Yellow
        $identities = aws ses list-verified-email-addresses --region $Region @awsProfileArgs 2>&1
        if ($LASTEXITCODE -eq 0) {
            $emailList = $identities | ConvertFrom-Json
            if ($emailList.VerifiedEmailAddresses.Count -gt 0) {
                Write-Host "✅ Verified email addresses:" -ForegroundColor Green
                foreach ($email in $emailList.VerifiedEmailAddresses) {
                    Write-Host "  - $email" -ForegroundColor Gray
                }
            } else {
                Write-Host "⚠️ No verified email addresses found" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "❌ Amazon SES NOT enabled" -ForegroundColor Red
        Write-Host "Error: $result" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Error checking Amazon SES: $_" -ForegroundColor Red
}
Write-Host ""

# Amazon Bedrock - Detailed check
Write-Host "4. AMAZON BEDROCK:" -ForegroundColor Yellow
Write-Host "Command: aws bedrock list-foundation-models --region $Region"
try {
    $result = aws bedrock list-foundation-models --region $Region @awsProfileArgs 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Amazon Bedrock is ENABLED" -ForegroundColor Green
        $models = $result | ConvertFrom-Json
        $claudeModels = $models.modelSummaries | Where-Object { $_.modelName -like "*claude*" }
        if ($claudeModels.Count -gt 0) {
            Write-Host "✅ Claude models available:" -ForegroundColor Green
            foreach ($model in $claudeModels) {
                Write-Host "  - $($model.modelId)" -ForegroundColor Gray
            }
        } else {
            Write-Host "⚠️ No Claude models found - you may need to request access" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ Amazon Bedrock NOT enabled" -ForegroundColor Red
        Write-Host "Error: $result" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Error checking Amazon Bedrock: $_" -ForegroundColor Red
}
Write-Host ""

Write-Host "=== SUMMARY ===" -ForegroundColor Cyan
Write-Host "Run individual commands above to verify each service manually."
Write-Host "All services must show ✅ before proceeding with deployment."
