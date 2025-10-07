# -*- coding: utf-8 -*-
"""
Generate 100 complete test queries for integration testing
Now covering all 12 supported languages: FR, EN, ES, DE, IT, PT, PL, NL, ID, HI, ZH, TH
"""

import json
from pathlib import Path

# Read existing base queries
base_file = Path(__file__).parent / "test_queries.json"

# Language distribution (12 languages total)
# FR: 25, EN: 20, ES: 10, DE: 10, IT: 8, PT: 7, PL: 5, NL: 5, ID: 4, HI: 3, ZH: 2, TH: 1
# Total: 100 queries

queries = []
query_id = 1

# ============================================================================
# FRENCH QUERIES (25 queries)
# ============================================================================
french_queries = [
    ('Quel poids pour Ross 308 à 35 jours ?', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Indice de consommation Cobb 500 à 42 jours', 'production', 'standard', ['breed', 'age_days', 'metric_type'], 'performance_issue', 200, 600),
    ('Gain moyen quotidien Ross 308 semaine 5', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Ross 308 vs Cobb 500 poids à 35 jours', 'production', 'comparative', ['breed', 'age_days'], 'comparison', 600, 1200),
    ('Traitement coccidiose poulets', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Protocole vaccination Gumboro', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Mortalité élevée 5% causes possibles', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Énergie métabolisable aliment croissance', 'nutrition', 'standard', ['production_phase'], 'general_info', 400, 900),
    ('Méthionine + cystine aliment démarrage', 'nutrition', 'standard', ['production_phase'], 'general_info', 400, 900),
    ('Comment réduire le FCR poulets', 'production', 'standard', [], 'optimization', 600, 1200),
    ('Optimiser croissance poulets chair', 'production', 'standard', [], 'optimization', 600, 1200),
    ('Améliorer uniformité troupeau', 'production', 'standard', [], 'optimization', 600, 1200),
    ('Ventilation minimale poulailler hiver', 'environment', 'standard', [], 'general_info', 400, 900),
    ('Température idéale démarrage poussins', 'environment', 'standard', [], 'general_info', 400, 900),
    ('Densité oiseaux au sol m2', 'environment', 'standard', [], 'general_info', 400, 900),
    ('Planifier bande 20000 poulets', 'management', 'standard', [], 'planning', 400, 900),
    ('Âge optimal abattage Ross 308', 'production', 'standard', ['breed'], 'planning', 400, 900),
    ('Uniformité Ross 308 à 42 jours', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Livabilité Ross 308 28 jours', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Consommation aliment cumulée Cobb 500 42 jours', 'nutrition', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Ross 308 vs Cobb 500 rendement carcasse', 'production', 'comparative', ['breed'], 'comparison', 600, 1200),
    ('Bronchite infectieuse prévention', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Biosécurité élevage poulets mesures', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Formulation aliment 3 phases poulets', 'nutrition', 'standard', [], 'general_info', 400, 900),
    ('Calendrier gestion troupeau 42 jours', 'management', 'standard', [], 'planning', 400, 900),
]

for q, domain, qtype, entities, context, min_len, max_len in french_queries:
    queries.append({
        'id': query_id,
        'query': q,
        'language': 'fr',
        'domain': domain,
        'query_type': qtype,
        'expected_entities': entities,
        'expected_context': context,
        'min_response_length': min_len,
        'max_response_length': max_len
    })
    query_id += 1

# ============================================================================
# ENGLISH QUERIES (20 queries)
# ============================================================================
english_queries = [
    ('Body weight Ross 308 week 6', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('European efficiency factor Cobb 500', 'production', 'standard', ['breed'], 'performance_issue', 200, 600),
    ('Cumulative feed intake Ross 308 at 35 days', 'nutrition', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Compare Ross 308 Cobb 500 feed conversion', 'production', 'comparative', ['breed'], 'comparison', 600, 1200),
    ('Newcastle disease symptoms broilers', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Salmonella control in poultry', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Coccidiosis vaccination program', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Protein requirements grower phase', 'nutrition', 'standard', ['production_phase'], 'general_info', 400, 900),
    ('Crude fiber maximum broiler feed', 'nutrition', 'standard', [], 'general_info', 400, 900),
    ('Vitamin E requirements broilers', 'nutrition', 'standard', [], 'general_info', 400, 900),
    ('How to improve daily weight gain', 'production', 'standard', [], 'optimization', 600, 1200),
    ('Reduce mortality rate broilers', 'health', 'standard', [], 'optimization', 600, 1200),
    ('How to increase feed efficiency', 'nutrition', 'standard', [], 'optimization', 600, 1200),
    ('Temperature grower phase broilers', 'environment', 'standard', [], 'general_info', 400, 900),
    ('Lighting program broilers', 'environment', 'standard', [], 'general_info', 400, 900),
    ('Air quality ammonia levels poultry', 'environment', 'standard', [], 'general_info', 400, 900),
    ('How many days to reach 2.8kg Ross 308', 'production', 'standard', ['breed'], 'planning', 400, 900),
    ('Flock planning 50000 birds', 'management', 'standard', [], 'planning', 400, 900),
    ('Target slaughter weight Cobb 500', 'production', 'standard', ['breed'], 'planning', 400, 900),
    ('Ross 308 Cobb 500 daily gain comparison', 'production', 'comparative', ['breed'], 'comparison', 600, 1200),
]

for q, domain, qtype, entities, context, min_len, max_len in english_queries:
    queries.append({
        'id': query_id,
        'query': q,
        'language': 'en',
        'domain': domain,
        'query_type': qtype,
        'expected_entities': entities,
        'expected_context': context,
        'min_response_length': min_len,
        'max_response_length': max_len
    })
    query_id += 1

# ============================================================================
# SPANISH QUERIES (10 queries)
# ============================================================================
spanish_queries = [
    ('Ganancia diaria Cobb 500 día 35', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Peso corporal Ross 308 21 días', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Comparar Ross 308 Cobb 500 peso 35 días', 'production', 'comparative', ['breed', 'age_days'], 'comparison', 600, 1200),
    ('Síntomas enfermedad Newcastle pollos', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Calcio fósforo ratio pollitos', 'nutrition', 'standard', [], 'general_info', 400, 900),
    ('Mejorar ganancia diaria pollos', 'production', 'standard', [], 'optimization', 600, 1200),
    ('Humedad relativa óptima pollos', 'environment', 'standard', [], 'general_info', 400, 900),
    ('Planificar lote 30000 pollos', 'management', 'standard', [], 'planning', 400, 900),
    ('Ross 308 vs Cobb 500 conversión alimenticia', 'production', 'comparative', ['breed'], 'comparison', 600, 1200),
    ('Protocolo vacunación Gumboro pollos', 'health', 'standard', [], 'health_concern', 400, 900),
]

for q, domain, qtype, entities, context, min_len, max_len in spanish_queries:
    queries.append({
        'id': query_id,
        'query': q,
        'language': 'es',
        'domain': domain,
        'query_type': qtype,
        'expected_entities': entities,
        'expected_context': context,
        'min_response_length': min_len,
        'max_response_length': max_len
    })
    query_id += 1

# ============================================================================
# GERMAN QUERIES (10 queries)
# ============================================================================
german_queries = [
    ('Körpergewicht Ross 308 Tag 35', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Futterverwertung Cobb 500 Tag 42', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Ross 308 vs Cobb 500 Gewicht Vergleich', 'production', 'comparative', ['breed'], 'comparison', 600, 1200),
    ('Newcastle-Krankheit Symptome Geflügel', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Proteinbedarf Mastphase Broiler', 'nutrition', 'standard', ['production_phase'], 'general_info', 400, 900),
    ('Futterverwertung verbessern Broiler', 'production', 'standard', [], 'optimization', 600, 1200),
    ('Temperatur Aufzuchtphase Küken', 'environment', 'standard', [], 'general_info', 400, 900),
    ('Herdengröße planen 40000 Vögel', 'management', 'standard', [], 'planning', 400, 900),
    ('Kokzidiose Behandlung Hühner', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Energiebedarf Wachstumsphase Futter', 'nutrition', 'standard', [], 'general_info', 400, 900),
]

for q, domain, qtype, entities, context, min_len, max_len in german_queries:
    queries.append({
        'id': query_id,
        'query': q,
        'language': 'de',
        'domain': domain,
        'query_type': qtype,
        'expected_entities': entities,
        'expected_context': context,
        'min_response_length': min_len,
        'max_response_length': max_len
    })
    query_id += 1

# ============================================================================
# ITALIAN QUERIES (8 queries)
# ============================================================================
italian_queries = [
    ('Peso corporeo Ross 308 a 35 giorni', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Indice di conversione Cobb 500 42 giorni', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Confronto Ross 308 Cobb 500 peso', 'production', 'comparative', ['breed'], 'comparison', 600, 1200),
    ('Sintomi malattia Newcastle polli', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Fabbisogno proteico fase crescita', 'nutrition', 'standard', ['production_phase'], 'general_info', 400, 900),
    ('Migliorare efficienza alimentare polli', 'production', 'standard', [], 'optimization', 600, 1200),
    ('Temperatura ideale fase svezzamento', 'environment', 'standard', [], 'general_info', 400, 900),
    ('Pianificazione lotto 25000 polli', 'management', 'standard', [], 'planning', 400, 900),
]

for q, domain, qtype, entities, context, min_len, max_len in italian_queries:
    queries.append({
        'id': query_id,
        'query': q,
        'language': 'it',
        'domain': domain,
        'query_type': qtype,
        'expected_entities': entities,
        'expected_context': context,
        'min_response_length': min_len,
        'max_response_length': max_len
    })
    query_id += 1

# ============================================================================
# PORTUGUESE QUERIES (7 queries)
# ============================================================================
portuguese_queries = [
    ('Peso corporal Ross 308 aos 35 dias', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Conversão alimentar Cobb 500 42 dias', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Comparar Ross 308 Cobb 500 ganho peso', 'production', 'comparative', ['breed'], 'comparison', 600, 1200),
    ('Sintomas doença Newcastle frangos', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Necessidade proteína fase crescimento', 'nutrition', 'standard', ['production_phase'], 'general_info', 400, 900),
    ('Melhorar eficiência alimentar frangos', 'production', 'standard', [], 'optimization', 600, 1200),
    ('Temperatura ideal fase inicial pintinhos', 'environment', 'standard', [], 'general_info', 400, 900),
]

for q, domain, qtype, entities, context, min_len, max_len in portuguese_queries:
    queries.append({
        'id': query_id,
        'query': q,
        'language': 'pt',
        'domain': domain,
        'query_type': qtype,
        'expected_entities': entities,
        'expected_context': context,
        'min_response_length': min_len,
        'max_response_length': max_len
    })
    query_id += 1

# ============================================================================
# POLISH QUERIES (5 queries)
# ============================================================================
polish_queries = [
    ('Masa ciała Ross 308 w 35 dniu', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Wskaźnik konwersji Cobb 500 42 dni', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Porównanie Ross 308 Cobb 500 waga', 'production', 'comparative', ['breed'], 'comparison', 600, 1200),
    ('Objawy choroby Newcastle kurczęta', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Zapotrzebowanie białko faza wzrostu', 'nutrition', 'standard', ['production_phase'], 'general_info', 400, 900),
]

for q, domain, qtype, entities, context, min_len, max_len in polish_queries:
    queries.append({
        'id': query_id,
        'query': q,
        'language': 'pl',
        'domain': domain,
        'query_type': qtype,
        'expected_entities': entities,
        'expected_context': context,
        'min_response_length': min_len,
        'max_response_length': max_len
    })
    query_id += 1

# ============================================================================
# DUTCH QUERIES (5 queries)
# ============================================================================
dutch_queries = [
    ('Lichaamsgewicht Ross 308 dag 35', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Voederconversie Cobb 500 42 dagen', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Vergelijking Ross 308 Cobb 500 gewicht', 'production', 'comparative', ['breed'], 'comparison', 600, 1200),
    ('Newcastle ziekte symptomen kippen', 'health', 'standard', [], 'health_concern', 400, 900),
    ('Eiwitbehoefte groeifase vleeskuikens', 'nutrition', 'standard', ['production_phase'], 'general_info', 400, 900),
]

for q, domain, qtype, entities, context, min_len, max_len in dutch_queries:
    queries.append({
        'id': query_id,
        'query': q,
        'language': 'nl',
        'domain': domain,
        'query_type': qtype,
        'expected_entities': entities,
        'expected_context': context,
        'min_response_length': min_len,
        'max_response_length': max_len
    })
    query_id += 1

# ============================================================================
# INDONESIAN QUERIES (4 queries)
# ============================================================================
indonesian_queries = [
    ('Berat badan Ross 308 hari 35', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Konversi pakan Cobb 500 42 hari', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Perbandingan Ross 308 Cobb 500 berat', 'production', 'comparative', ['breed'], 'comparison', 600, 1200),
    ('Gejala penyakit Newcastle ayam', 'health', 'standard', [], 'health_concern', 400, 900),
]

for q, domain, qtype, entities, context, min_len, max_len in indonesian_queries:
    queries.append({
        'id': query_id,
        'query': q,
        'language': 'id',
        'domain': domain,
        'query_type': qtype,
        'expected_entities': entities,
        'expected_context': context,
        'min_response_length': min_len,
        'max_response_length': max_len
    })
    query_id += 1

# ============================================================================
# HINDI QUERIES (3 queries)
# ============================================================================
hindi_queries = [
    ('Ross 308 का वजन 35 दिन में', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Cobb 500 फीड रूपांतरण 42 दिन', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('न्यूकैसल रोग के लक्षण मुर्गियों में', 'health', 'standard', [], 'health_concern', 400, 900),
]

for q, domain, qtype, entities, context, min_len, max_len in hindi_queries:
    queries.append({
        'id': query_id,
        'query': q,
        'language': 'hi',
        'domain': domain,
        'query_type': qtype,
        'expected_entities': entities,
        'expected_context': context,
        'min_response_length': min_len,
        'max_response_length': max_len
    })
    query_id += 1

# ============================================================================
# CHINESE QUERIES (2 queries)
# ============================================================================
chinese_queries = [
    ('Ross 308 在35天的体重', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
    ('Cobb 500 饲料转化率 42天', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
]

for q, domain, qtype, entities, context, min_len, max_len in chinese_queries:
    queries.append({
        'id': query_id,
        'query': q,
        'language': 'zh',
        'domain': domain,
        'query_type': qtype,
        'expected_entities': entities,
        'expected_context': context,
        'min_response_length': min_len,
        'max_response_length': max_len
    })
    query_id += 1

# ============================================================================
# THAI QUERY (1 query)
# ============================================================================
thai_queries = [
    ('น้ำหนักตัว Ross 308 ที่ 35 วัน', 'production', 'standard', ['breed', 'age_days'], 'performance_issue', 200, 600),
]

for q, domain, qtype, entities, context, min_len, max_len in thai_queries:
    queries.append({
        'id': query_id,
        'query': q,
        'language': 'th',
        'domain': domain,
        'query_type': qtype,
        'expected_entities': entities,
        'expected_context': context,
        'min_response_length': min_len,
        'max_response_length': max_len
    })
    query_id += 1

# ============================================================================
# BUILD METADATA AND SAVE
# ============================================================================

# Count by language
lang_count = {}
for q in queries:
    lang = q['language']
    lang_count[lang] = lang_count.get(lang, 0) + 1

# Count by domain
domain_count = {}
for q in queries:
    domain = q['domain']
    domain_count[domain] = domain_count.get(domain, 0) + 1

data = {
    'metadata': {
        'description': f'{len(queries)} realistic test queries covering 12 languages and all system features',
        'total_queries': len(queries),
        'languages': lang_count,
        'domains': domain_count,
        'version': '2.0',
        'last_updated': '2025-10-06'
    },
    'queries': queries
}

# Save
with open(base_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f'OK - Generated {len(queries)} total test queries')
print('\nLanguage distribution:')
for lang, count in sorted(lang_count.items()):
    print(f'   - {lang.upper()}: {count}')

print('\nDomain distribution:')
for domain, count in sorted(domain_count.items()):
    print(f'   - {domain}: {count}')

print(f'\nFile saved to: {base_file}')
