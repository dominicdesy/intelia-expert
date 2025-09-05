# Scanner simple pour problemes encodage
param($Path = "C:\intelia_gpt\intelia-expert\backend")

Write-Host "=== SCANNER ENCODAGE ===" -ForegroundColor Cyan
Write-Host "Chemin: $Path"

$Files = Get-ChildItem $Path -Recurse -Include "*.py","*.md","*.txt" | Where-Object {
    $_.FullName -notmatch "__pycache__|\.git|node_modules"
}

Write-Host "Fichiers: $($Files.Count)"

$Problems = @()
foreach ($f in $Files) {
    try {
        $content = Get-Content $f.FullName -Raw -Encoding UTF8
        if ($content) {
            $issueCount = 0
            
            # Compter les patterns problematiques avec regex simple
            $badChars = @("Ã©","Ã¨","Ã ","Ã§","Ã´","Ã¢","â†","â€","Â°","ðŸ")
            
            foreach ($char in $badChars) {
                $matches = [regex]::Matches($content, [regex]::Escape($char))
                $issueCount += $matches.Count
            }
            
            if ($issueCount -gt 0) {
                $Problems += [PSCustomObject]@{
                    File = $f.Name
                    Path = $f.FullName
                    Issues = $issueCount
                }
                Write-Host "PROBLEME: $($f.Name) - $issueCount caracteres" -ForegroundColor Red
            }
        }
    } catch {
        Write-Host "Erreur: $($f.Name)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== RESULTAT ===" -ForegroundColor Cyan
Write-Host "Fichiers scannes: $($Files.Count)" -ForegroundColor Green
Write-Host "Fichiers avec problemes: $($Problems.Count)" -ForegroundColor Red

if ($Problems.Count -gt 0) {
    Write-Host ""
    Write-Host "PRIORITES (par nombre de problemes):" -ForegroundColor Yellow
    $Problems | Sort-Object Issues -Descending | ForEach-Object {
        Write-Host "  $($_.File): $($_.Issues) problemes" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "Pour corriger le premier fichier:" -ForegroundColor Green
    $first = ($Problems | Sort-Object Issues -Descending)[0]
    Write-Host "  `$f = `"$($first.Path)`"" -ForegroundColor Gray
} else {
    Write-Host "Aucun probleme detecte!" -ForegroundColor Green
}
