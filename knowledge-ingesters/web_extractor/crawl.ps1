# ============================
# Lightweight Web Crawler (PowerShell)
# But : extraire uniquement les URLs d'un site (sans télécharger les pages complètes)
# ============================

param(
    [string]$StartUrl = "https://www.poultryhub.org/",
    [int]$MaxDepth = 3
)

# Accepter TLS récents
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$visited = New-Object System.Collections.Generic.HashSet[string]
$queue = New-Object System.Collections.Queue

# obtenir le host de départ (pour filtrer le domaine)
$baseUri = [Uri]$StartUrl
$domain = $baseUri.Host

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LIGHTWEIGHT WEB CRAWLER" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Start URL: $StartUrl" -ForegroundColor White
Write-Host "Domain: $domain" -ForegroundColor White
Write-Host "Max Depth: $MaxDepth" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor Cyan

# on démarre
$queue.Enqueue(@{ Url = $StartUrl; Depth = 0 })
$visited.Add($StartUrl) | Out-Null

$results = @()
$errorCount = 0

while ($queue.Count -gt 0) {
    $item = $queue.Dequeue()
    $url = $item.Url
    $depth = $item.Depth

    Write-Host "[Depth $depth] $url" -ForegroundColor Cyan

    try {
        # Créer une requête HTTP HEAD d'abord pour vérifier que la page existe
        # Plus léger qu'un GET complet
        $headRequest = [System.Net.HttpWebRequest]::Create($url)
        $headRequest.Method = "HEAD"
        $headRequest.Timeout = 10000  # 10 secondes
        $headRequest.UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) InteliaCrawler/1.0"

        try {
            $headResponse = $headRequest.GetResponse()
            $headResponse.Close()
        } catch {
            # Si HEAD échoue, essayer GET (certains serveurs bloquent HEAD)
        }

        # Télécharger seulement le HTML (pas les images, CSS, JS)
        # UseBasicParsing = plus rapide, pas de parsing complet
        $webClient = New-Object System.Net.WebClient
        $webClient.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) InteliaCrawler/1.0")
        $webClient.Encoding = [System.Text.Encoding]::UTF8

        # Télécharger uniquement le HTML (léger)
        $html = $webClient.DownloadString($url)
        $webClient.Dispose()

        # on ajoute l'URL trouvée aux résultats
        $results += [pscustomobject]@{
            Url   = $url
            Depth = $depth
        }

        Write-Host "  Found URLs: $($visited.Count)" -ForegroundColor Gray

        # si on est déjà à la profondeur max, on ne suit pas les liens
        if ($depth -ge $MaxDepth) {
            Write-Host "  Max depth reached - skipping links" -ForegroundColor Yellow
            continue
        }

        # Extraire les liens avec regex (plus rapide que parser HTML complet)
        # Chercher href="..." et href='...'
        $linkPattern = 'href\s*=\s*["' + "'" + ']([^"' + "'" + ']+)["' + "'" + ']'
        $matches = [regex]::Matches($html, $linkPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)

        $newLinksCount = 0
        foreach ($match in $matches) {
            $link = $match.Groups[1].Value

            # Ignorer les liens vides, ancres pures, javascript, mailto
            if (-not $link -or $link -eq "#" -or $link.StartsWith("javascript:") -or $link.StartsWith("mailto:") -or $link.StartsWith("tel:")) {
                continue
            }

            # normaliser les liens relatifs
            try {
                $absolute = (New-Object System.Uri($baseUri, $link)).AbsoluteUri
            } catch {
                continue
            }

            # filtrer sur le même domaine
            $uri = [Uri]$absolute
            if ($uri.Host -ne $domain) { continue }

            # éviter les ancres
            if ($absolute -match '#') {
                $absolute = $absolute.Split('#')[0]
            }

            # éviter les query strings si vous voulez (optionnel)
            # Décommenter pour ignorer ?param=value
            # if ($absolute -match '\?') {
            #     $absolute = $absolute.Split('?')[0]
            # }

            # éviter de crawler 1000 fois le même
            if (-not $visited.Contains($absolute)) {
                $visited.Add($absolute) | Out-Null
                $queue.Enqueue(@{ Url = $absolute; Depth = $depth + 1 })
                $newLinksCount++
            }
        }

        Write-Host "  New links queued: $newLinksCount" -ForegroundColor Green

    } catch {
        Write-Host "  ERROR: $_" -ForegroundColor Red
        $errorCount++

        # Ajouter quand même l'URL aux résultats (mais marquer comme erreur)
        $results += [pscustomobject]@{
            Url   = $url
            Depth = $depth
        }
        continue
    }

    # Petit délai pour ne pas surcharger le serveur
    Start-Sleep -Milliseconds 500
}

# dédoublonner / trier
$results = $results | Sort-Object Depth, Url | Select-Object -Unique -Property Url, Depth

# Statistiques finales
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "CRAWL COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total URLs found: $($results.Count)" -ForegroundColor Green
Write-Host "Errors encountered: $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { "Yellow" } else { "Green" })
Write-Host "========================================`n" -ForegroundColor Cyan

# Exporter en format texte (une URL par ligne)
$outFile = "crawl.txt"
$results | ForEach-Object { $_.Url } | Out-File -FilePath $outFile -Encoding UTF8

# Aussi exporter en CSV pour Excel (optionnel)
$csvFile = "site-urls.csv"
$results | Export-Csv -Path $csvFile -NoTypeInformation -Encoding UTF8

Write-Host "Output files:" -ForegroundColor Green
Write-Host "  - $outFile (text file, one URL per line)" -ForegroundColor White
Write-Host "  - $csvFile (CSV for Excel)" -ForegroundColor White
Write-Host "`nYou can now:" -ForegroundColor White
Write-Host "  1. Review URLs in $outFile" -ForegroundColor Gray
Write-Host "  2. Copy URLs to websites.xlsx" -ForegroundColor Gray
Write-Host "  3. Run: python web_auto_classifier.py" -ForegroundColor Gray
Write-Host "  4. Run: python web_batch_processor.py" -ForegroundColor Gray
