# 📊 Guide de Monitoring CSP - Intelia Expert

**Date** : 2025-10-19
**Endpoint** : `POST https://expert.intelia.com/api/v1/csp-report`

---

## 📋 TABLE DES MATIÈRES

1. [Monitoring en temps réel](#monitoring-en-temps-réel)
2. [Analyse des logs](#analyse-des-logs)
3. [Dashboard de monitoring](#dashboard-de-monitoring)
4. [Alertes automatiques](#alertes-automatiques)
5. [Violations courantes](#violations-courantes)
6. [Scripts d'analyse](#scripts-danalyse)

---

## 🔴 MONITORING EN TEMPS RÉEL

### **Méthode 1 : Logs backend (Production)**

Si vous avez accès au serveur de production :

```bash
# Suivre les logs en temps réel
tail -f /var/log/app/backend.log | grep "CSP Violation"

# Avec couleurs pour meilleure lisibilité
tail -f /var/log/app/backend.log | grep --color=always "CSP Violation"

# Filtrer les violations critiques uniquement
tail -f /var/log/app/backend.log | grep "CSP Violation" | grep -E "script-src|connect-src"
```

### **Méthode 2 : Logs via Docker/Railway/Render**

Si vous utilisez Railway, Render ou similaire :

```bash
# Railway CLI
railway logs -t

# Render Dashboard
# Aller sur dashboard.render.com → Votre service → Logs

# Docker Compose
docker-compose logs -f backend | grep "CSP Violation"
```

### **Méthode 3 : Monitoring CloudFlare**

CloudFlare peut logger les requêtes POST vers `/api/v1/csp-report` :

1. Dashboard CloudFlare → **Analytics** → **Logs**
2. Filtrer : `request_uri contains "/csp-report"`
3. Analyser le volume et les patterns

---

## 🔍 ANALYSE DES LOGS

### **Format du log CSP**

Chaque violation génère un log comme :

```
WARNING: CSP Violation: blocked-uri=https://evil.com/script.js, violated-directive=script-src 'self', document-uri=https://expert.intelia.com/chat, source-file=https://expert.intelia.com/_next/static/chunks/app.js, line-number=142
```

### **Champs importants**

| Champ | Description | Action |
|-------|-------------|--------|
| **blocked-uri** | Ressource bloquée | Identifier si légitime ou malveillante |
| **violated-directive** | Directive CSP violée | `script-src`, `connect-src`, etc. |
| **document-uri** | Page où la violation a eu lieu | Identifier la page affectée |
| **source-file** | Fichier source du script | Identifier le code problématique |
| **line-number** | Ligne du code | Debug précis |

---

## 📈 DASHBOARD DE MONITORING

### **Option A : Script Python simple**

Créez `monitor_csp.py` :

```python
#!/usr/bin/env python3
"""
Moniteur CSP - Analyse les violations en temps réel
"""
import re
import sys
from collections import Counter
from datetime import datetime

def parse_csp_log(log_line):
    """Parse une ligne de log CSP"""
    pattern = r'blocked-uri=([^,]+), violated-directive=([^,]+), document-uri=([^,]+)'
    match = re.search(pattern, log_line)

    if match:
        return {
            'blocked_uri': match.group(1),
            'directive': match.group(2),
            'page': match.group(3),
            'timestamp': datetime.now()
        }
    return None

def main():
    violations = []

    print("🔍 Moniteur CSP - En attente de violations...")
    print("=" * 80)

    try:
        for line in sys.stdin:
            if "CSP Violation" in line:
                violation = parse_csp_log(line)
                if violation:
                    violations.append(violation)

                    # Afficher la violation
                    print(f"\n⚠️  NOUVELLE VIOLATION - {violation['timestamp']}")
                    print(f"   Page : {violation['page']}")
                    print(f"   Directive : {violation['directive']}")
                    print(f"   Bloqué : {violation['blocked_uri']}")
                    print("-" * 80)

                    # Statistiques toutes les 10 violations
                    if len(violations) % 10 == 0:
                        print(f"\n📊 STATISTIQUES ({len(violations)} violations)")

                        # Top URIs bloquées
                        blocked_uris = Counter(v['blocked_uri'] for v in violations)
                        print("\nTop 5 URIs bloquées :")
                        for uri, count in blocked_uris.most_common(5):
                            print(f"  {count}x - {uri}")

                        # Top directives violées
                        directives = Counter(v['directive'] for v in violations)
                        print("\nTop directives violées :")
                        for directive, count in directives.most_common(5):
                            print(f"  {count}x - {directive}")

                        print("=" * 80)

    except KeyboardInterrupt:
        print(f"\n\n📊 RAPPORT FINAL ({len(violations)} violations)")

        if violations:
            # Rapport final
            blocked_uris = Counter(v['blocked_uri'] for v in violations)
            directives = Counter(v['directive'] for v in violations)
            pages = Counter(v['page'] for v in violations)

            print("\n🎯 TOP 10 URIS BLOQUÉES :")
            for uri, count in blocked_uris.most_common(10):
                print(f"  {count:3d}x - {uri}")

            print("\n🎯 DIRECTIVES VIOLÉES :")
            for directive, count in directives.most_common():
                print(f"  {count:3d}x - {directive}")

            print("\n🎯 PAGES AFFECTÉES :")
            for page, count in pages.most_common(10):
                print(f"  {count:3d}x - {page}")

if __name__ == "__main__":
    main()
```

**Usage** :

```bash
# Analyser les logs en temps réel
tail -f /var/log/backend.log | python3 monitor_csp.py

# Analyser des logs historiques
cat /var/log/backend.log | python3 monitor_csp.py
```

---

### **Option B : Dashboard Web simple**

Créez `csp_dashboard.html` :

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>CSP Dashboard - Intelia Expert</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a2e;
            color: #eee;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #16f4d0;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .stat-card {
            background: #16213e;
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid #16f4d0;
        }
        .stat-card h3 {
            margin: 0 0 10px 0;
            color: #16f4d0;
        }
        .stat-card .value {
            font-size: 2em;
            font-weight: bold;
        }
        .violations-list {
            background: #16213e;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }
        .violation {
            background: #0f3460;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 3px solid #e94560;
        }
        .violation .time {
            color: #888;
            font-size: 0.9em;
        }
        .violation .blocked {
            color: #e94560;
            font-weight: bold;
        }
        .violation .directive {
            color: #16f4d0;
        }
        #status {
            text-align: center;
            padding: 10px;
            background: #16213e;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .online {
            color: #16f4d0;
        }
        .offline {
            color: #e94560;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ CSP Monitoring Dashboard</h1>

        <div id="status">
            <span id="status-indicator" class="offline">● Déconnecté</span>
            <span id="last-update"></span>
        </div>

        <div class="stats">
            <div class="stat-card">
                <h3>Total Violations</h3>
                <div class="value" id="total-violations">0</div>
            </div>
            <div class="stat-card">
                <h3>Dernière heure</h3>
                <div class="value" id="last-hour">0</div>
            </div>
            <div class="stat-card">
                <h3>Directive la plus violée</h3>
                <div class="value" id="top-directive">-</div>
            </div>
            <div class="stat-card">
                <h3>Page affectée</h3>
                <div class="value" id="top-page">-</div>
            </div>
        </div>

        <div class="violations-list">
            <h2>📋 Violations récentes (live)</h2>
            <div id="violations-container">
                <p style="text-align: center; color: #888;">En attente de violations...</p>
            </div>
        </div>
    </div>

    <script>
        const violations = [];
        let ws;

        // Simuler la réception de violations (en production, connecter à WebSocket ou polling)
        function checkForViolations() {
            // En production, faire un fetch vers l'API qui retourne les dernières violations
            // Ici, on simule pour la démo

            fetch('/api/v1/csp-violations-recent')  // Endpoint à créer si besoin
                .then(res => res.json())
                .then(data => {
                    data.forEach(violation => addViolation(violation));
                })
                .catch(err => {
                    document.getElementById('status-indicator').className = 'offline';
                    document.getElementById('status-indicator').textContent = '● Déconnecté';
                });
        }

        function addViolation(violation) {
            violations.push({
                ...violation,
                timestamp: new Date()
            });

            // Mettre à jour le status
            document.getElementById('status-indicator').className = 'online';
            document.getElementById('status-indicator').textContent = '● Connecté';
            document.getElementById('last-update').textContent = `Dernière MAJ : ${new Date().toLocaleTimeString('fr-FR')}`;

            // Mettre à jour les stats
            updateStats();

            // Ajouter à la liste
            const container = document.getElementById('violations-container');
            if (container.querySelector('p')) {
                container.innerHTML = '';
            }

            const div = document.createElement('div');
            div.className = 'violation';
            div.innerHTML = `
                <div class="time">${new Date().toLocaleTimeString('fr-FR')}</div>
                <div><strong>Page :</strong> ${violation.document_uri || 'N/A'}</div>
                <div class="directive"><strong>Directive :</strong> ${violation.violated_directive || 'N/A'}</div>
                <div class="blocked"><strong>Bloqué :</strong> ${violation.blocked_uri || 'N/A'}</div>
            `;

            container.insertBefore(div, container.firstChild);

            // Garder seulement les 50 dernières
            while (container.children.length > 50) {
                container.removeChild(container.lastChild);
            }
        }

        function updateStats() {
            // Total
            document.getElementById('total-violations').textContent = violations.length;

            // Dernière heure
            const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
            const lastHour = violations.filter(v => v.timestamp > oneHourAgo).length;
            document.getElementById('last-hour').textContent = lastHour;

            // Directive la plus violée
            const directives = {};
            violations.forEach(v => {
                const dir = v.violated_directive || 'unknown';
                directives[dir] = (directives[dir] || 0) + 1;
            });
            const topDirective = Object.entries(directives)
                .sort((a, b) => b[1] - a[1])[0];
            if (topDirective) {
                document.getElementById('top-directive').textContent =
                    `${topDirective[0].split(' ')[0]} (${topDirective[1]})`;
            }

            // Page la plus affectée
            const pages = {};
            violations.forEach(v => {
                const page = v.document_uri || 'unknown';
                const shortPage = page.split('/').pop() || page;
                pages[shortPage] = (pages[shortPage] || 0) + 1;
            });
            const topPage = Object.entries(pages)
                .sort((a, b) => b[1] - a[1])[0];
            if (topPage) {
                document.getElementById('top-page').textContent =
                    `${topPage[0]} (${topPage[1]})`;
            }
        }

        // Polling toutes les 10 secondes
        setInterval(checkForViolations, 10000);
        checkForViolations();
    </script>
</body>
</html>
```

**Pour l'utiliser** : Héberger ce fichier sur votre serveur ou l'ouvrir localement.

---

## 🚨 ALERTES AUTOMATIQUES

### **Option 1 : Alert Slack/Discord**

Ajoutez au backend (`backend/app/main.py`) :

```python
import httpx
import os

CSP_WEBHOOK_URL = os.getenv("CSP_ALERT_WEBHOOK_URL")  # Slack/Discord webhook

@app.post("/api/v1/csp-report", tags=["Security"])
async def csp_violation_report(request: Request):
    try:
        body = await request.json()
        csp_report = body.get("csp-report", {})

        blocked_uri = csp_report.get('blocked-uri', 'unknown')
        violated_directive = csp_report.get('violated-directive', 'unknown')
        document_uri = csp_report.get('document-uri', 'unknown')

        # Log the violation
        logger.warning(
            f"CSP Violation: "
            f"blocked-uri={blocked_uri}, "
            f"violated-directive={violated_directive}, "
            f"document-uri={document_uri}"
        )

        # Alert critique si script externe bloqué
        if 'script-src' in violated_directive and blocked_uri != 'inline':
            await send_csp_alert(blocked_uri, violated_directive, document_uri)

        return JSONResponse(status_code=204, content={})

    except Exception as e:
        logger.error(f"Error processing CSP report: {e}")
        return JSONResponse(status_code=204, content={})


async def send_csp_alert(blocked_uri: str, directive: str, page: str):
    """Envoie une alerte Slack/Discord pour violation CSP critique"""
    if not CSP_WEBHOOK_URL:
        return

    try:
        message = {
            "text": f"🚨 **ALERTE CSP CRITIQUE** 🚨\n\n"
                    f"**Page affectée** : {page}\n"
                    f"**Directive violée** : {directive}\n"
                    f"**URI bloquée** : {blocked_uri}\n\n"
                    f"⚠️ Possible tentative d'injection de script malveillant"
        }

        async with httpx.AsyncClient() as client:
            await client.post(CSP_WEBHOOK_URL, json=message, timeout=5)

    except Exception as e:
        logger.error(f"Failed to send CSP alert: {e}")
```

**Configuration** :

```bash
# .env
CSP_ALERT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

---

### **Option 2 : Alert Email**

```python
import smtplib
from email.mime.text import MIMEText

async def send_email_alert(blocked_uri: str, directive: str, page: str):
    """Envoie un email d'alerte pour violation CSP"""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    alert_email = os.getenv("CSP_ALERT_EMAIL", "admin@intelia.com")

    if not smtp_user or not smtp_password:
        return

    subject = f"🚨 Alerte CSP - {page}"
    body = f"""
    Violation CSP détectée sur Intelia Expert

    Page affectée : {page}
    Directive violée : {directive}
    URI bloquée : {blocked_uri}
    Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    Cette alerte indique une possible tentative d'injection de code malveillant.
    Veuillez investiguer immédiatement.
    """

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = alert_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
```

---

## ⚠️ VIOLATIONS COURANTES

### **1. Extension de navigateur** (Non critique)

```
blocked-uri=chrome-extension://..., violated-directive=script-src 'self'
```

**Cause** : Extensions Chrome/Firefox injectent des scripts
**Action** : ✅ Ignorer (normal)

---

### **2. Script inline sans nonce** (Moyen)

```
blocked-uri=inline, violated-directive=script-src 'self', source-file=/chat, line-number=142
```

**Cause** : `<script>` inline sans attribut nonce
**Action** : ⚠️ Investiguer le code source, vérifier si légitime

---

### **3. Script externe malveillant** (CRITIQUE)

```
blocked-uri=https://evil.com/malware.js, violated-directive=script-src 'self'
```

**Cause** : Tentative d'injection XSS ou compromise du site
**Action** : 🚨 **ALERTE IMMÉDIATE** - Investiguer le vecteur d'attaque

---

### **4. API tierce non autorisée** (Moyen)

```
blocked-uri=https://analytics.thirdparty.com/track, violated-directive=connect-src 'self'
```

**Cause** : Appel API non whitelisté
**Action** : ⚠️ Vérifier si légitime → Ajouter au CSP si besoin

---

## 📊 SCRIPTS D'ANALYSE

### **Script 1 : Analyse quotidienne**

```bash
#!/bin/bash
# daily_csp_report.sh

LOG_FILE="/var/log/backend.log"
REPORT_FILE="/tmp/csp_report_$(date +%Y%m%d).txt"

echo "📊 Rapport CSP - $(date)" > $REPORT_FILE
echo "================================" >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Compter les violations
TOTAL=$(grep "CSP Violation" $LOG_FILE | wc -l)
echo "Total violations : $TOTAL" >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Top 10 URIs bloquées
echo "🎯 Top 10 URIs bloquées :" >> $REPORT_FILE
grep "CSP Violation" $LOG_FILE | \
  grep -oP 'blocked-uri=\K[^,]+' | \
  sort | uniq -c | sort -rn | head -10 >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Top directives violées
echo "🎯 Directives violées :" >> $REPORT_FILE
grep "CSP Violation" $LOG_FILE | \
  grep -oP 'violated-directive=\K[^,]+' | \
  sort | uniq -c | sort -rn >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Top pages affectées
echo "🎯 Pages affectées :" >> $REPORT_FILE
grep "CSP Violation" $LOG_FILE | \
  grep -oP 'document-uri=\K[^,]+' | \
  sort | uniq -c | sort -rn | head -10 >> $REPORT_FILE

# Afficher le rapport
cat $REPORT_FILE

# Envoyer par email (optionnel)
# mail -s "Rapport CSP quotidien" admin@intelia.com < $REPORT_FILE
```

**Cron job** :

```bash
# Exécuter tous les jours à 9h
0 9 * * * /path/to/daily_csp_report.sh
```

---

### **Script 2 : Détection d'anomalies**

```python
#!/usr/bin/env python3
"""
Détecte les anomalies dans les violations CSP
"""
import re
import sys
from collections import Counter
from datetime import datetime, timedelta

ALERT_THRESHOLD = 10  # Alerter si > 10 violations identiques en 1h

def detect_anomalies(log_file):
    violations = []

    with open(log_file, 'r') as f:
        for line in f:
            if "CSP Violation" not in line:
                continue

            # Parser le timestamp (format à adapter)
            # timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)

            blocked_uri = re.search(r'blocked-uri=([^,]+)', line)
            if blocked_uri:
                violations.append({
                    'uri': blocked_uri.group(1),
                    'timestamp': datetime.now()  # À remplacer par parsing réel
                })

    # Analyser les violations récentes (1h)
    recent = [v for v in violations
              if v['timestamp'] > datetime.now() - timedelta(hours=1)]

    # Compter les URIs
    uri_counts = Counter(v['uri'] for v in recent)

    # Alerter sur les anomalies
    print(f"\n🔍 Analyse des {len(recent)} violations récentes (1h)")
    print("=" * 60)

    for uri, count in uri_counts.most_common():
        if count > ALERT_THRESHOLD:
            print(f"\n🚨 ANOMALIE DÉTECTÉE !")
            print(f"   URI : {uri}")
            print(f"   Occurrences : {count} (seuil : {ALERT_THRESHOLD})")
            print(f"   ⚠️  Possible attaque en cours ou bug côté client")
        else:
            print(f"✅ {count:3d}x - {uri}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 detect_anomalies.py /path/to/backend.log")
        sys.exit(1)

    detect_anomalies(sys.argv[1])
```

---

## 📋 CHECKLIST DE MONITORING

Cochez ces points régulièrement :

- [ ] Les logs CSP sont accessibles et lisibles
- [ ] Aucune violation critique détectée (scripts externes malveillants)
- [ ] Les violations d'extensions de navigateur sont ignorées
- [ ] Les alertes Slack/email fonctionnent
- [ ] Le rapport quotidien est généré automatiquement
- [ ] Les anomalies (>10 violations identiques/h) sont investiguées
- [ ] La whitelist CSP est à jour avec les besoins légitimes

---

## 🎯 ACTIONS SELON LE TYPE DE VIOLATION

| Violation | Criticité | Action immédiate |
|-----------|-----------|------------------|
| **chrome-extension://** | 🟢 Faible | Ignorer |
| **inline script** | 🟡 Moyen | Vérifier le code source |
| **Script externe non whitelist** | 🔴 Critique | 🚨 Alerte + Investigation |
| **API tierce** | 🟡 Moyen | Vérifier légitimité → Whitelist |
| **Même violation >50x/h** | 🔴 Critique | 🚨 Anomalie → Investigation |

---

## ✅ RÉSUMÉ - QUICK START

**Pour commencer le monitoring maintenant** :

1. **Logs en temps réel** :
   ```bash
   tail -f /var/log/backend.log | grep "CSP Violation"
   ```

2. **Rapport quotidien** :
   ```bash
   chmod +x daily_csp_report.sh
   ./daily_csp_report.sh
   ```

3. **Dashboard Python** :
   ```bash
   tail -f /var/log/backend.log | python3 monitor_csp.py
   ```

4. **Alertes Slack** (optionnel) :
   - Ajouter `CSP_ALERT_WEBHOOK_URL` dans `.env`
   - Redéployer le backend

---

**Prochaine étape recommandée** : Configurer le rapport quotidien en cron job pour recevoir un email chaque matin avec les violations de la veille.

---

*Guide créé le 2025-10-19 dans le cadre de l'optimisation OWASP #2 (CSP Monitoring).*
