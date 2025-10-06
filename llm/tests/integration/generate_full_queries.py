# -*- coding: utf-8 -*-
"""
Generate 100 complete test queries for integration testing
"""

import json
from pathlib import Path

# Read existing base queries
base_file = Path(__file__).parent / "test_queries.json"
with open(base_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

queries_supplement = []
base_id = 21

# Production queries (10 more)
production_queries = [
    ('Poids moyen Cobb 500 entre 30 et 40 jours', 'fr', 'production', 'standard'),
    ('Body weight Ross 308 week 6', 'en', 'production', 'standard'),
    ('Ganancia diaria Cobb 500 día 35', 'es', 'production', 'standard'),
    ('Uniformité Ross 308 à 42 jours', 'fr', 'production', 'standard'),
    ('European efficiency factor Cobb 500', 'en', 'production', 'standard'),
    ('Livabilité Ross 308 28 jours', 'fr', 'production', 'standard'),
    ('Cumulative feed intake Ross 308 at 35 days', 'en', 'nutrition', 'standard'),
    ('Consommation aliment cumulée Cobb 500 42 jours', 'fr', 'nutrition', 'standard'),
    ('Peso corporal Ross 308 21 días', 'es', 'production', 'standard'),
    ('Ross 308 vs Cobb 500 gain quotidien 28 jours', 'fr', 'production', 'comparative'),
]

for i, (q, lang, domain, qtype) in enumerate(production_queries, base_id):
    queries_supplement.append({
        'id': i, 'query': q, 'language': lang, 'domain': domain,
        'query_type': qtype, 'expected_entities': ['breed', 'age_days'],
        'expected_context': 'performance_issue' if 'compare' not in q.lower() else 'comparison',
        'min_response_length': 200 if qtype == 'standard' else 600,
        'max_response_length': 600 if qtype == 'standard' else 1200
    })

base_id += len(production_queries)

# Health queries (15 more)
health_queries = [
    ('Traitement coccidiose poulets', 'fr', 'health', 'standard'),
    ('Newcastle disease symptoms broilers', 'en', 'health', 'standard'),
    ('Protocole vaccination Gumboro', 'fr', 'health', 'standard'),
    ('Bronchite infectieuse prévention', 'fr', 'health', 'standard'),
    ('Salmonella control in poultry', 'en', 'health', 'standard'),
    ('Mortalité élevée 5% causes possibles', 'fr', 'health', 'standard'),
    ('Biosécurité élevage poulets mesures', 'fr', 'health', 'standard'),
    ('E. coli symptoms chickens', 'en', 'health', 'standard'),
    ('Ascites poulets symptômes traitement', 'fr', 'health', 'standard'),
    ('Coccidiosis vaccination program', 'en', 'health', 'standard'),
    ('Marek disease prevention', 'en', 'health', 'standard'),
    ('Diarrhée poulets causes', 'fr', 'health', 'standard'),
    ('Respiratory problems broilers treatment', 'en', 'health', 'standard'),
    ('Syndrome de mort subite poulets', 'fr', 'health', 'standard'),
    ('Infectious bursal disease control', 'en', 'health', 'standard'),
]

for i, (q, lang, domain, qtype) in enumerate(health_queries, base_id):
    queries_supplement.append({
        'id': i, 'query': q, 'language': lang, 'domain': domain,
        'query_type': qtype, 'expected_entities': [],
        'expected_context': 'health_concern',
        'min_response_length': 400, 'max_response_length': 900
    })

base_id += len(health_queries)

# Nutrition queries (15 more)
nutrition_queries = [
    ('Énergie métabolisable aliment croissance', 'fr', 'nutrition', 'standard'),
    ('Protein requirements grower phase', 'en', 'nutrition', 'standard'),
    ('Calcio fósforo ratio pollitos', 'es', 'nutrition', 'standard'),
    ('Méthionine + cystine aliment démarrage', 'fr', 'nutrition', 'standard'),
    ('Crude fiber maximum broiler feed', 'en', 'nutrition', 'standard'),
    ('Sodium chlore niveau optimal aliment', 'fr', 'nutrition', 'standard'),
    ('Vitamin E requirements broilers', 'en', 'nutrition', 'standard'),
    ('Tryptophane aliment finition poulets', 'fr', 'nutrition', 'standard'),
    ('Metabolizable energy finisher feed', 'en', 'nutrition', 'standard'),
    ('Threonine starter feed level', 'en', 'nutrition', 'standard'),
    ('Arginine besoin poulets croissance', 'fr', 'nutrition', 'standard'),
    ('Valine requirements grower phase', 'en', 'nutrition', 'standard'),
    ('Isoleucine niveau recommandé finition', 'fr', 'nutrition', 'standard'),
    ('Choline requirements broiler feed', 'en', 'nutrition', 'standard'),
    ('Formulation aliment 3 phases poulets', 'fr', 'nutrition', 'standard'),
]

for i, (q, lang, domain, qtype) in enumerate(nutrition_queries, base_id):
    queries_supplement.append({
        'id': i, 'query': q, 'language': lang, 'domain': domain,
        'query_type': qtype, 'expected_entities': ['production_phase'],
        'expected_context': 'general_info',
        'min_response_length': 400, 'max_response_length': 900
    })

base_id += len(nutrition_queries)

# Comparison queries (10 more)
comparison_queries = [
    ('Ross 308 vs Cobb 500 mortalité 42 jours', 'fr', 'production', 'comparative'),
    ('Compare Ross 308 Cobb 500 feed conversion', 'en', 'production', 'comparative'),
    ('Ross 308 vs Cobb 500 rendement carcasse', 'fr', 'production', 'comparative'),
    ('Ross 308 Cobb 500 daily gain comparison', 'en', 'production', 'comparative'),
    ('Comparar Ross 308 Cobb 500 peso 35 días', 'es', 'production', 'comparative'),
    ('Ross 308 vs Cobb 500 uniformité poids', 'fr', 'production', 'comparative'),
    ('Ross 308 Cobb 500 livability comparison', 'en', 'production', 'comparative'),
    ('Ross 308 vs Cobb 500 consommation eau', 'fr', 'production', 'comparative'),
    ('Compare Ross 308 Cobb 500 breast yield', 'en', 'production', 'comparative'),
    ('Ross 308 vs Cobb 500 EEF 42 jours', 'fr', 'production', 'comparative'),
]

for i, (q, lang, domain, qtype) in enumerate(comparison_queries, base_id):
    queries_supplement.append({
        'id': i, 'query': q, 'language': lang, 'domain': domain,
        'query_type': qtype, 'expected_entities': ['breed'],
        'expected_context': 'comparison',
        'min_response_length': 600, 'max_response_length': 1200
    })

base_id += len(comparison_queries)

# Optimization queries (10 more)
optimization_queries = [
    ('Comment réduire le FCR poulets', 'fr', 'production', 'standard'),
    ('How to improve daily weight gain', 'en', 'production', 'standard'),
    ('Optimiser croissance poulets chair', 'fr', 'production', 'standard'),
    ('Reduce mortality rate broilers', 'en', 'health', 'standard'),
    ('Améliorer uniformité troupeau', 'fr', 'production', 'standard'),
    ('How to increase feed efficiency', 'en', 'nutrition', 'standard'),
    ('Optimiser rendement carcasse', 'fr', 'production', 'standard'),
    ('Improve breast meat yield strategies', 'en', 'production', 'standard'),
    ('Réduire coûts alimentaires poulets', 'fr', 'nutrition', 'standard'),
    ('Maximize profitability broiler production', 'en', 'production', 'standard'),
]

for i, (q, lang, domain, qtype) in enumerate(optimization_queries, base_id):
    queries_supplement.append({
        'id': i, 'query': q, 'language': lang, 'domain': domain,
        'query_type': qtype, 'expected_entities': [],
        'expected_context': 'optimization',
        'min_response_length': 600, 'max_response_length': 1200
    })

base_id += len(optimization_queries)

# Environment queries (10 more)
environment_queries = [
    ('Ventilation minimale poulailler hiver', 'fr', 'environment', 'standard'),
    ('Temperature grower phase broilers', 'en', 'environment', 'standard'),
    ('Humedad relativa óptima pollos', 'es', 'environment', 'standard'),
    ('Litière copeaux bois vs paille', 'fr', 'environment', 'standard'),
    ('Lighting program broilers', 'en', 'environment', 'standard'),
    ('Densité oiseaux au sol m2', 'fr', 'environment', 'standard'),
    ('Air quality ammonia levels poultry', 'en', 'environment', 'standard'),
    ('Programme lumineux poulets croissance', 'fr', 'environment', 'standard'),
    ('Water quality requirements broilers', 'en', 'environment', 'standard'),
    ('Température idéale démarrage poussins', 'fr', 'environment', 'standard'),
]

for i, (q, lang, domain, qtype) in enumerate(environment_queries, base_id):
    queries_supplement.append({
        'id': i, 'query': q, 'language': lang, 'domain': domain,
        'query_type': qtype, 'expected_entities': [],
        'expected_context': 'general_info',
        'min_response_length': 400, 'max_response_length': 900
    })

base_id += len(environment_queries)

# Planning queries (10 more)
planning_queries = [
    ('Planifier bande 20000 poulets', 'fr', 'management', 'standard'),
    ('How many days to reach 2.8kg Ross 308', 'en', 'production', 'standard'),
    ('Calendrier gestion troupeau 42 jours', 'fr', 'management', 'standard'),
    ('Flock planning 50000 birds', 'en', 'management', 'standard'),
    ('Âge optimal abattage Ross 308', 'fr', 'production', 'standard'),
    ('Target slaughter weight Cobb 500', 'en', 'production', 'standard'),
    ('Prévision consommation aliment 30000 poulets', 'fr', 'nutrition', 'standard'),
    ('Feed budget estimation broiler flock', 'en', 'nutrition', 'standard'),
    ('Planification vaccination première semaine', 'fr', 'health', 'standard'),
    ('Production forecast next batch', 'en', 'management', 'standard'),
]

for i, (q, lang, domain, qtype) in enumerate(planning_queries, base_id):
    queries_supplement.append({
        'id': i, 'query': q, 'language': lang, 'domain': domain,
        'query_type': qtype, 'expected_entities': [],
        'expected_context': 'planning',
        'min_response_length': 400, 'max_response_length': 900
    })

# Append all new queries
data['queries'].extend(queries_supplement)

# Update metadata
data['metadata']['total_queries'] = len(data['queries'])
data['metadata']['description'] = f"{len(data['queries'])} realistic test queries covering all system features"

# Save back
with open(base_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"✅ Generated {len(data['queries'])} total test queries")
print(f"   - Production: {sum(1 for q in data['queries'] if q['domain'] == 'production')}")
print(f"   - Health: {sum(1 for q in data['queries'] if q['domain'] == 'health')}")
print(f"   - Nutrition: {sum(1 for q in data['queries'] if q['domain'] == 'nutrition')}")
print(f"   - Environment: {sum(1 for q in data['queries'] if q['domain'] == 'environment')}")
print(f"   - Management: {sum(1 for q in data['queries'] if q['domain'] == 'management')}")
