-- ============================================================================
-- MIGRATION 28: Synchroniser les quotas des plans vers les utilisateurs
-- Date: 2025-01-21
-- Description: Propage les quotas de billing_plans vers monthly_usage_tracking
-- ============================================================================

-- Afficher l'état AVANT la migration
SELECT
    'AVANT MIGRATION' as etape,
    ubi.plan_name,
    bp.monthly_quota as quota_plan,
    COUNT(mut.user_email) as nb_utilisateurs,
    COUNT(DISTINCT mut.monthly_quota) as nb_quotas_differents,
    STRING_AGG(DISTINCT mut.monthly_quota::TEXT, ', ' ORDER BY mut.monthly_quota::TEXT) as quotas_actuels
FROM user_billing_info ubi
LEFT JOIN billing_plans bp ON ubi.plan_name = bp.plan_name
LEFT JOIN monthly_usage_tracking mut ON ubi.user_email = mut.user_email
    AND mut.month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
WHERE ubi.custom_monthly_quota IS NULL
GROUP BY ubi.plan_name, bp.monthly_quota
ORDER BY ubi.plan_name;

-- ============================================================================
-- SYNCHRONISATION: Mettre à jour tous les quotas du mois en cours
-- ============================================================================

UPDATE monthly_usage_tracking mut
SET
    monthly_quota = bp.monthly_quota,
    current_status = CASE
        WHEN questions_used >= bp.monthly_quota THEN 'quota_exceeded'
        ELSE 'active'
    END,
    quota_exceeded_at = CASE
        WHEN questions_used >= bp.monthly_quota AND quota_exceeded_at IS NULL THEN CURRENT_TIMESTAMP
        WHEN questions_used < bp.monthly_quota THEN NULL
        ELSE quota_exceeded_at
    END,
    last_updated = CURRENT_TIMESTAMP
FROM user_billing_info ubi
JOIN billing_plans bp ON ubi.plan_name = bp.plan_name
WHERE mut.user_email = ubi.user_email
  AND ubi.custom_monthly_quota IS NULL
  AND mut.month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
  AND mut.monthly_quota != bp.monthly_quota;

-- Afficher le nombre de lignes mises à jour
SELECT
    'LIGNES MISES À JOUR' as resultat,
    (SELECT COUNT(*) FROM monthly_usage_tracking) as total_lignes;

-- ============================================================================
-- Afficher l'état APRÈS la migration
-- ============================================================================

SELECT
    'APRÈS MIGRATION' as etape,
    ubi.plan_name,
    bp.monthly_quota as quota_plan,
    COUNT(mut.user_email) as nb_utilisateurs,
    COUNT(DISTINCT mut.monthly_quota) as nb_quotas_differents,
    STRING_AGG(DISTINCT mut.monthly_quota::TEXT, ', ' ORDER BY mut.monthly_quota::TEXT) as quotas_actuels
FROM user_billing_info ubi
LEFT JOIN billing_plans bp ON ubi.plan_name = bp.plan_name
LEFT JOIN monthly_usage_tracking mut ON ubi.user_email = mut.user_email
    AND mut.month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
WHERE ubi.custom_monthly_quota IS NULL
GROUP BY ubi.plan_name, bp.monthly_quota
ORDER BY ubi.plan_name;

-- ============================================================================
-- Vérification détaillée par utilisateur
-- ============================================================================

SELECT
    'DÉTAIL PAR UTILISATEUR' as section,
    mut.user_email,
    ubi.plan_name,
    bp.monthly_quota as quota_plan,
    mut.monthly_quota as quota_utilisateur,
    mut.questions_used,
    mut.current_status,
    CASE
        WHEN mut.monthly_quota = bp.monthly_quota THEN '✅ OK'
        ELSE '❌ DÉSYNCHRONISÉ'
    END as statut_sync
FROM monthly_usage_tracking mut
JOIN user_billing_info ubi ON mut.user_email = ubi.user_email
JOIN billing_plans bp ON ubi.plan_name = bp.plan_name
WHERE mut.month_year = TO_CHAR(CURRENT_DATE, 'YYYY-MM')
  AND ubi.custom_monthly_quota IS NULL
ORDER BY ubi.plan_name, mut.user_email;

-- ============================================================================
-- COMMENTAIRES
-- ============================================================================

COMMENT ON TABLE monthly_usage_tracking IS 'Usage mensuel - quota synchronisé automatiquement depuis billing_plans';

-- Message de succès
SELECT
    '✅ MIGRATION 28 TERMINÉE' as statut,
    'Les quotas ont été synchronisés avec billing_plans' as message,
    CURRENT_TIMESTAMP as execute_le;
