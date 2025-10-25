# 📅 Politique de Conservation des Données - Intelia Expert

**Date de création** : 2025-10-24
**Version** : 1.0
**Conformité GDPR** : Article 5(1)(e) - Limitation de la conservation

---

## 📋 Vue d'Ensemble

Ce document définit la durée de conservation des données personnelles collectées par Intelia Expert et la base légale justifiant chaque période de conservation, conformément au Règlement Général sur la Protection des Données (RGPD).

---

## 🎯 Principe Général

Intelia Expert applique le principe de **conservation proportionnée** : nous ne conservons vos données personnelles que le temps strictement nécessaire aux finalités pour lesquelles elles ont été collectées.

---

## 📊 Tableau des Durées de Conservation

| Type de Données | Durée de Conservation | Base Légale GDPR | Justification |
|---|---|---|---|
| **Profil utilisateur** | Tant que le compte est actif | Article 6(1)(b) - Exécution du contrat | Nécessaire pour fournir le service |
| **Conversations & Messages** | Tant que le compte est actif | Article 6(1)(b) - Exécution du contrat | Fonctionnalité essentielle : historique accessible |
| **Images médicales** | Tant que le compte est actif | Article 6(1)(b) - Exécution du contrat | Contexte médical nécessaire aux consultations |
| **Statistiques d'utilisation** | Tant que le compte est actif | Article 6(1)(f) - Intérêt légitime | Amélioration continue du service |
| **Données de facturation** | 10 ans après la dernière transaction | Obligation légale fiscale | Code Général des Impôts (Art. L102 B) |
| **Sessions expirées** | 7 jours après expiration | Article 6(1)(f) - Intérêt légitime | Sécurité et détection d'anomalies |
| **Logs applicatifs** | 12 mois maximum | Article 6(1)(f) - Intérêt légitime | Diagnostic technique et sécurité |
| **Données anonymisées** | Indéfiniment | N/A - Hors scope GDPR | Données non identifiantes (analytique) |

---

## 🔍 Détails par Catégorie de Données

### 1. Données de Profil

**Quelles données ?**
- Nom et prénom
- Adresse email
- Numéro de téléphone (si fourni)
- Pays et langue
- Préférences utilisateur

**Durée de conservation** : Tant que votre compte est actif

**Suppression** :
- Immédiate lors de la fermeture de compte (via Profil → Sécurité → Supprimer mon compte)
- Les données sont **anonymisées** (remplacées par un identifiant anonyme "anonymous-xxxxxxxx") et non supprimées complètement

**Base légale** : Article 6(1)(b) - Exécution du contrat
**Justification** : Ces informations sont indispensables pour vous identifier et personnaliser votre expérience.

---

### 2. Conversations et Messages

**Quelles données ?**
- Historique complet de vos conversations avec l'assistant IA
- Messages envoyés et reçus
- Contexte conversationnel
- Métadonnées (date, heure, durée)

**Durée de conservation** : **Indéfiniment tant que votre compte est actif**

**Suppression** :
- Les conversations ne sont **jamais supprimées automatiquement**
- Lors de la fermeture de compte, elles sont **anonymisées** (le user_id est remplacé par "anonymous-xxxxxxxx")
- Les conversations anonymisées sont conservées pour l'analytique mais ne peuvent plus être reliées à vous

**Base légale** : Article 6(1)(b) - Exécution du contrat
**Justification** :
- L'historique conversationnel est une **fonctionnalité clé** du service
- Permet la continuité des conversations multi-sessions
- Amélioration continue du modèle IA
- Comparable à ChatGPT, Claude.ai, et autres assistants IA qui conservent l'historique indéfiniment

**Vos droits** :
- ✅ Vous pouvez **exporter** votre historique à tout moment (Profil → Exporter mes données)
- ✅ Vous pouvez **supprimer votre compte** à tout moment (Profil → Sécurité → Supprimer mon compte)
- ✅ Vous pouvez demander la **suppression d'une conversation spécifique** en contactant confidentialite@intelia.com

---

### 3. Images Médicales

**Quelles données ?**
- Photos et documents médicaux téléchargés
- Métadonnées (date, taille, type)
- Lien avec les conversations

**Durée de conservation** : Tant que votre compte est actif

**Suppression** :
- Lors de la fermeture de compte, les métadonnées sont anonymisées
- Les fichiers physiques restent sur le stockage cloud mais ne peuvent plus être reliés à vous
- Vous pouvez demander la suppression complète en contactant confidentialite@intelia.com

**Base légale** : Article 6(1)(b) - Exécution du contrat
**Justification** : Les images médicales fournissent le contexte nécessaire pour les consultations de santé.

---

### 4. Données de Facturation (Stripe)

**Quelles données ?**
- Informations de paiement (4 derniers chiffres carte)
- Historique des transactions
- Abonnements et factures
- Customer ID Stripe

**Durée de conservation** : **10 ans après la dernière transaction**

**Suppression** :
- Lors de la fermeture de compte, ces données sont **anonymisées** (email remplacé)
- Conservation obligatoire pour conformité fiscale même après anonymisation
- Seules les données nécessaires à la comptabilité sont conservées

**Base légale** : Article 6(1)(c) - Obligation légale
**Justification** : Le Code Général des Impôts (Art. L102 B) impose la conservation des pièces comptables pendant 10 ans.

**Note** : Cette conservation est **obligatoire par la loi** et ne peut être contournée par une demande de suppression GDPR.

---

### 5. Sessions Utilisateur

**Quelles données ?**
- Tokens de session
- Date de connexion
- Durée de session
- Heartbeat (activité)

**Durée de conservation** :
- Sessions actives : Jusqu'à expiration (inactivité de 24h)
- Sessions expirées : **7 jours** après expiration

**Suppression** :
- Nettoyage automatique quotidien via script `cleanup_expired_sessions.py`
- Lors du logout manuel : suppression immédiate

**Base légale** : Article 6(1)(f) - Intérêt légitime
**Justification** : Conservation temporaire pour détecter des activités suspectes et améliorer la sécurité.

---

### 6. Logs Applicatifs

**Quelles données ?**
- Logs serveur (erreurs, requêtes API)
- Emails masqués (format : `j***n@e***.com`)
- Pas d'adresses IP complètes (masquées)
- Événements système

**Durée de conservation** : **Maximum 12 mois**

**Suppression** : Rotation automatique mensuelle (logs > 12 mois supprimés)

**Base légale** : Article 6(1)(f) - Intérêt légitime
**Justification** :
- Diagnostic technique (bugs, erreurs)
- Détection d'intrusions
- Amélioration de la performance

**Mesures de protection** :
- ✅ Emails masqués automatiquement (fonction `mask_email()`)
- ✅ Pas de mots de passe loggés
- ✅ Données sensibles (santé) jamais loggées en clair

---

### 7. Données Anonymisées

**Quelles données ?**
- Statistiques d'utilisation agrégées
- Métriques de performance
- Conversations anonymisées (après fermeture de compte)

**Durée de conservation** : **Indéfiniment**

**Base légale** : N/A - Hors scope GDPR (Article 4(1))
**Justification** : Les données anonymisées ne permettent plus de vous identifier et ne sont donc plus considérées comme des "données personnelles" selon le GDPR.

**Garantie d'anonymisation** :
- ✅ Remplacement du user_id par un hash MD5 tronqué (`anonymous-xxxxxxxx`)
- ✅ Email remplacé (`anonymous-xxxxxxxx@deleted.intelia.app`)
- ✅ Nom remplacé par "Anonymous User"
- ✅ Impossible de re-identifier l'utilisateur original

---

## ⏰ Processus de Nettoyage Automatique

### Script Quotidien : `cleanup_expired_sessions.py`

**Fréquence** : Tous les jours à 3h00 UTC
**Action** : Supprime les sessions expirées depuis plus de 7 jours

```sql
DELETE FROM sessions
WHERE last_activity_at < NOW() - INTERVAL '7 days'
  AND status = 'expired'
```

### Rotation des Logs : `rotate_logs.sh`

**Fréquence** : Tous les mois
**Action** : Archive et supprime les logs > 12 mois

---

## 🛡️ Vos Droits GDPR

Conformément au GDPR, vous disposez des droits suivants sur vos données :

### 1. Droit d'Accès (Article 15)
**Comment ?** Profil → Exporter mes données
**Délai** : Immédiat (export JSON)

### 2. Droit de Rectification (Article 16)
**Comment ?** Profil → Modifier mes informations
**Délai** : Immédiat

### 3. Droit à l'Effacement / Droit à l'Oubli (Article 17)
**Comment ?** Profil → Sécurité → Supprimer mon compte
**Délai** : Immédiat
**Note** : Anonymisation (pas suppression complète) pour les conversations et données de facturation

### 4. Droit à la Portabilité (Article 20)
**Comment ?** Profil → Exporter mes données
**Format** : JSON structuré
**Délai** : Immédiat

### 5. Droit d'Opposition (Article 21)
**Comment ?** Contacter confidentialite@intelia.com
**Délai** : 30 jours maximum

---

## 📞 Contact DPO (Délégué à la Protection des Données)

Pour toute question sur la conservation de vos données ou pour exercer vos droits :

**Email** : confidentialite@intelia.com
**Délai de réponse** : 30 jours maximum (Article 12 GDPR)

**Vous pouvez nous contacter pour** :
- Demander la suppression d'une conversation spécifique
- Obtenir des informations sur vos données conservées
- Exercer vos droits GDPR
- Signaler un problème de confidentialité

---

## 📚 Références Légales

- **GDPR (RGPD)** : Règlement UE 2016/679
- **Article 5(1)(e)** : Limitation de la conservation
- **Article 6(1)(b)** : Base légale - Exécution du contrat
- **Article 6(1)(c)** : Base légale - Obligation légale
- **Article 6(1)(f)** : Base légale - Intérêt légitime
- **Code Général des Impôts** : Art. L102 B (conservation comptable 10 ans)

---

## 📋 Registre des Traitements (Article 30)

Cette politique fait partie intégrante de notre **Registre des Activités de Traitement** tenu conformément à l'Article 30 du GDPR.

**Responsable du traitement** : Intelia Expert
**DPO** : confidentialite@intelia.com
**Dernière mise à jour** : 2025-10-24

---

## 🔄 Mises à Jour de cette Politique

Cette politique peut être mise à jour pour refléter :
- Des changements dans nos pratiques de conservation
- Des évolutions réglementaires
- Des améliorations de sécurité

**Notification** : Vous serez informé par email de toute modification significative.

**Historique des versions** :
- v1.0 (2025-10-24) : Première version

---

**Document généré conformément au GDPR**
**Dernière révision** : 2025-10-24
