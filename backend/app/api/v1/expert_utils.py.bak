# Dans expert_utils.py, remplacer la fonction process_question_with_enhanced_prompt

async def process_question_with_enhanced_prompt(
    question: str, 
    language: str = "fr", 
    speed_mode: str = "balanced",
    extracted_entities: Dict = None,
    conversation_context: str = ""
) -> str:
    """Traite une question avec prompt amélioré AVEC DONNÉES DE RÉFÉRENCE ROSS 308"""
    
    try:
        import openai
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return get_fallback_response_enhanced(question, language)
        
        openai.api_key = api_key
        
        # ✅ DONNÉES DE RÉFÉRENCE ROSS 308 INTÉGRÉES
        reference_data = """
DONNÉES DE RÉFÉRENCE AVICULTURE (UTILISATION OBLIGATOIRE) :

🐔 Ross 308 - Poids Standards (À UTILISER EXACTEMENT) :
- Jour 1: 42-45g
- Jour 7: 160-180g  
- Jour 12: 340-370g ← CRITIQUE ! (JAMAIS 700-900g)
- Jour 14: 430-470g
- Jour 21: 800-900g
- Jour 28: 1400-1600g
- Jour 35: 2000-2300g
- Jour 42: 2500-2800g

🐔 Cobb 500 - Poids Standards :
- Jour 12: 320-350g
- Jour 21: 750-850g
- Jour 42: 2400-2700g

RÈGLES CRITIQUES OBLIGATOIRES :
- Ross 308 jour 12 = 340-370g (JAMAIS autre chose !)
- Si contexte mentionne Ross 308 + âge = réponse PRÉCISE obligatoire
- Utilise TOUJOURS ces données exactes, jamais d'approximations
"""

        # ✅ PROMPT AMÉLIORÉ avec détection contextuelle
        enhanced_prompts = {
            "fr": f"""{reference_data}

Tu es un expert en production avicole spécialisé en santé et nutrition animale. Tu assists tous les acteurs de la filière : fermiers, vétérinaires, nutritionnistes, consultants et techniciens.

CONSIGNES CRITIQUES:
1. UTILISE OBLIGATOIREMENT les données de référence ci-dessus
2. Si le contexte mentionne "Ross 308" et un âge, donne la réponse EXACTE
3. Ross 308 de 12 jours = 340-370g (JAMAIS 700-900g !)
4. Si pronom "son/sa/ses" + âge mentionné = utilise la race du contexte
5. Commence par répondre directement avec les chiffres exacts

Contexte conversationnel disponible:
{conversation_context}

EXEMPLE CRITIQUE :
Contexte précédent: "Ross 308"
Question: "Quel est son poids idéal au jour 12 ?"
Réponse CORRECTE: "Pour un Ross 308 de 12 jours, le poids idéal se situe entre 340-370 grammes selon les standards de performance. Si vos poulets pèsent moins de 320g à cet âge, cela peut indiquer un problème nutritionnel."

IMPORTANT: 
- Détecte les références contextuelles ("son", "sa", "ils", etc.)
- Utilise le contexte fourni pour identifier la race
- Donne TOUJOURS des réponses chiffrées précises
- UTILISE les données de référence ci-dessus OBLIGATOIREMENT""",

            "en": f"""{reference_data}

You are an expert in poultry production specialized in animal health and nutrition. You assist all stakeholders in the industry: farmers, veterinarians, nutritionists, consultants and technicians.

CRITICAL INSTRUCTIONS:
1. USE the reference data above MANDATORILY
2. If context mentions "Ross 308" and age, give EXACT answer
3. Ross 308 at 12 days = 340-370g (NEVER 700-900g!)
4. If pronoun "its/their" + age mentioned = use breed from context
5. Start by directly answering with exact figures

Available conversational context:
{conversation_context}

IMPORTANT: Always use the reference data above, never approximations!""",

            "es": f"""{reference_data}

Eres un experto en producción avícola especializado en salud y nutrición animal. Asistes a todos los actores de la industria: granjeros, veterinarios, nutricionistas, consultores y técnicos.

INSTRUCCIONES CRÍTICAS:
1. USA los datos de referencia arriba OBLIGATORIAMENTE
2. Si el contexto menciona "Ross 308" y edad, da respuesta EXACTA
3. Ross 308 a los 12 días = 340-370g (¡NUNCA 700-900g!)
4. Si pronombre "su/sus" + edad mencionada = usa raza del contexto
5. Comienza respondiendo directamente con cifras exactas

Contexto conversacional disponible:
{conversation_context}

IMPORTANTE: Usa SIEMPRE los datos de referencia arriba, ¡nunca aproximaciones!"""
        }
        
        system_prompt = enhanced_prompts.get(language.lower(), enhanced_prompts["fr"])
        
        # ✅ DEBUG LOG pour voir le contexte
        logger.info(f"🔍 [Expert Utils] Question: {question}")
        logger.info(f"🔍 [Expert Utils] Contexte: {conversation_context[:100]}...")
        
        # Configuration par mode
        model_config = {
            "fast": {"model": "gpt-3.5-turbo", "max_tokens": 400},
            "balanced": {"model": "gpt-4o-mini", "max_tokens": 600},
            "quality": {"model": "gpt-4o-mini", "max_tokens": 800}
        }
        
        config = model_config.get(speed_mode, model_config["balanced"])
        
        response = openai.chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(question)}
            ],
            temperature=0.1,  # ← Réduire pour plus de précision
            max_tokens=config["max_tokens"],
            timeout=20
        )
        
        answer = response.choices[0].message.content
        logger.info(f"🤖 [Expert Utils] Réponse GPT: {answer[:100]}...")
        
        return str(answer) if answer else get_fallback_response_enhanced(question, language)
        
    except Exception as e:
        logger.error(f"❌ [Expert Utils] Erreur OpenAI: {e}")
        return get_fallback_response_enhanced(question, language)