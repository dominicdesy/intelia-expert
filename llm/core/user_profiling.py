# -*- coding: utf-8 -*-
"""
user_profiling.py - User Profile Management for LLM Personalization
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
user_profiling.py - User Profile Management for LLM Personalization

Retrieves and applies user profiling information to personalize LLM responses:
- Production type (broiler, layer, both)
- Category in value chain (health, farm operations, nutrition, etc.)
"""

import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Supabase client singleton
_supabase_client = None


def _get_supabase_client():
    """
    Get or initialize Supabase client for querying user profiles.
    Uses SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables.

    Returns:
        Supabase client instance
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    try:
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = (
            os.getenv("SUPABASE_SERVICE_KEY") or
            os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
            os.getenv("SUPABASE_KEY") or
            os.getenv("SUPABASE_ANON_KEY")
        )

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) must be set")

        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("✅ Supabase client initialized for user profiling")
        return _supabase_client

    except ImportError:
        logger.error("❌ supabase-py library not installed. Run: pip install supabase")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase client: {e}")
        raise


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Récupère le profil utilisateur depuis Supabase

    Args:
        user_id: Auth user ID (UUID format, may have "user_" prefix)

    Returns:
        Dict with production_type (list), category (str), category_other (str), country (str)
        Returns empty dict if user not found or error occurs
    """
    try:
        # Remove "user_" prefix if present (tenant_id format -> auth_user_id format)
        clean_user_id = user_id.replace("user_", "") if user_id.startswith("user_") else user_id

        supabase = _get_supabase_client()

        # Query users table by auth_user_id
        response = supabase.table("users").select("production_type, category, category_other, country").eq("auth_user_id", clean_user_id).execute()

        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            profile = {
                'production_type': user_data.get('production_type') or [],
                'category': user_data.get('category'),
                'category_other': user_data.get('category_other'),
                'country': user_data.get('country')
            }
            logger.info(f"✅ User profile loaded: production_type={profile['production_type']}, category={profile['category']}, country={profile['country']}")
            return profile

        logger.info(f"ℹ️ No profile found for user {user_id}")
        return {}

    except Exception as e:
        logger.error(f"❌ Error fetching user profile: {e}")
        return {}


def build_personalized_system_prompt(base_prompt: str, user_profile: Dict[str, Any]) -> str:
    """
    Adapte le system prompt selon le profil utilisateur

    Args:
        base_prompt: Prompt système de base
        user_profile: {production_type: [...], category: str, category_other: str}

    Returns:
        System prompt personnalisé avec contexte utilisateur
    """
    if not user_profile:
        # No profile data, return base prompt
        return base_prompt

    personalization = ""

    # ===== 1. MEASUREMENT SYSTEM (Based on Country) =====
    country = user_profile.get('country', '')

    # USA uses Imperial system, all other countries use Metric
    if country == 'US':
        personalization += "\n\n📏 MEASUREMENT SYSTEM: IMPERIAL (USA)\n"
        personalization += "- Provide weights in pounds (lb) and ounces (oz)\n"
        personalization += "- Provide temperatures in Fahrenheit (°F)\n"
        personalization += "- Provide distances/lengths in feet (ft) and inches (in)\n"
        personalization += "- Provide volumes in gallons (gal), quarts (qt), and fluid ounces (fl oz)\n"
        personalization += "- Example: 'The bird weighs 5.2 lb' or 'Set temperature to 95°F'\n"
        personalization += "- You may optionally include metric equivalents in parentheses for clarity\n"
    else:
        personalization += "\n\n📏 MEASUREMENT SYSTEM: METRIC\n"
        personalization += "- Provide weights in kilograms (kg) and grams (g)\n"
        personalization += "- Provide temperatures in Celsius (°C)\n"
        personalization += "- Provide distances/lengths in meters (m) and centimeters (cm)\n"
        personalization += "- Provide volumes in liters (L) and milliliters (mL)\n"
        personalization += "- Example: 'The bird weighs 2.4 kg' or 'Set temperature to 35°C'\n"
        personalization += "- DO NOT use Imperial units unless specifically requested by the user\n"

    # ===== 2. PRODUCTION TYPE ADAPTATIONS =====
    production_types = user_profile.get('production_type', [])

    if 'broiler' in production_types and 'layer' not in production_types:
        personalization += "\n\n🐔 USER CONTEXT: This user works ONLY with BROILERS (meat chickens).\n"
        personalization += "- Focus on broiler-specific metrics: FCR (Feed Conversion Ratio), ADG (Average Daily Gain), slaughter weight, meat yield\n"
        personalization += "- Emphasize growth performance, feed efficiency, and processing quality\n"
        personalization += "- When discussing diseases, prioritize conditions affecting broilers (ascites, sudden death syndrome, leg problems)\n"
        personalization += "- Prioritize broiler-relevant content in your responses\n"

    elif 'layer' in production_types and 'broiler' not in production_types:
        personalization += "\n\n🥚 USER CONTEXT: This user works ONLY with LAYERS (egg-laying hens).\n"
        personalization += "- Focus on layer-specific metrics: HD (Hen-Day production), egg mass, feed per dozen eggs, egg quality (shell strength, yolk color)\n"
        personalization += "- Emphasize egg production performance, shell quality, and laying persistency\n"
        personalization += "- When discussing diseases, prioritize conditions affecting layers (cage layer fatigue, egg peritonitis, fatty liver syndrome)\n"
        personalization += "- Prioritize layer-relevant content in your responses\n"

    elif 'broiler' in production_types and 'layer' in production_types:
        personalization += "\n\n🐔🥚 USER CONTEXT: This user works with BOTH broilers AND layers.\n"
        personalization += "- Provide balanced information for both production types\n"
        personalization += "- When answering, CLEARLY SPECIFY which production type the information applies to\n"
        personalization += "- If a topic applies to only one type, state this explicitly\n"

    # ===== 3. CATEGORY ADAPTATIONS (Expertise Level & Response Style) =====
    category = user_profile.get('category')

    if category == 'health_veterinary':
        personalization += "\n\n👨‍⚕️ EXPERTISE LEVEL: VETERINARY/HEALTH PROFESSIONAL\n"
        personalization += "Response Style:\n"
        personalization += "- Provide DETAILED technical explanations with scientific terminology\n"
        personalization += "- Include differential diagnoses and clinical reasoning\n"
        personalization += "- Reference relevant studies, veterinary protocols, or drug dosages when applicable\n"
        personalization += "- Discuss pathophysiology, treatment protocols, and therapeutic options\n"
        personalization += "- Use medical terminology (this user has veterinary training)\n"

    elif category == 'farm_operations':
        personalization += "\n\n👨‍🌾 EXPERTISE LEVEL: FARM OPERATOR/PRODUCER\n"
        personalization += "Response Style:\n"
        personalization += "- Provide PRACTICAL, actionable solutions that can be implemented on the farm\n"
        personalization += "- Focus on day-to-day farm management and real-world problem-solving\n"
        personalization += "- Use CLEAR LANGUAGE without excessive technical jargon\n"
        personalization += "- Include specific steps and 'what to look for' indicators\n"
        personalization += "- When discussing health issues, explain WHEN to call a veterinarian\n"
        personalization += "- Focus on prevention, early detection, and practical interventions\n"

    elif category == 'feed_nutrition':
        personalization += "\n\n🌾 EXPERTISE LEVEL: NUTRITION SPECIALIST\n"
        personalization += "Response Style:\n"
        personalization += "- Provide detailed nutritional analysis and formulation guidance\n"
        personalization += "- Include specific nutrient requirements and formulation strategies\n"
        personalization += "- Discuss feed ingredients, amino acid profiles, energy systems (ME, AME, NE)\n"
        personalization += "- Reference nutritional standards (NRC, breeder company nutrition guides)\n"
        personalization += "- Include cost-benefit considerations for feed formulation decisions\n"

    elif category == 'management_oversight':
        personalization += "\n\n📊 EXPERTISE LEVEL: MANAGEMENT/STRATEGIC LEVEL\n"
        personalization += "Response Style:\n"
        personalization += "- Provide strategic insights with performance data and KPIs\n"
        personalization += "- Include cost-benefit analysis and ROI considerations\n"
        personalization += "- Focus on decision-making support and performance optimization\n"
        personalization += "- Reference industry benchmarks and comparative data\n"
        personalization += "- Discuss impact on business outcomes and profitability\n"

    elif category == 'breeding_hatchery':
        personalization += "\n\n🐣 EXPERTISE LEVEL: BREEDING/HATCHERY SPECIALIST\n"
        personalization += "Response Style:\n"
        personalization += "- Focus on breeder management, egg quality, fertility, and hatchability\n"
        personalization += "- Include incubation parameters, embryo development, and hatch window optimization\n"
        personalization += "- Discuss genetic selection, flock management, and breeder nutrition\n"
        personalization += "- Reference breeder company guidelines and hatchery best practices\n"

    elif category == 'processing':
        personalization += "\n\n🏭 EXPERTISE LEVEL: PROCESSING SPECIALIST\n"
        personalization += "Response Style:\n"
        personalization += "- Focus on slaughter operations, meat quality, and food safety\n"
        personalization += "- Include processing yields, carcass quality, shelf life, and product quality\n"
        personalization += "- Discuss regulatory compliance, HACCP protocols, and quality control\n"
        personalization += "- Reference food safety standards and processing best practices\n"

    elif category == 'equipment_technology':
        personalization += "\n\n⚙️ EXPERTISE LEVEL: EQUIPMENT/TECHNOLOGY PROVIDER\n"
        personalization += "Response Style:\n"
        personalization += "- Focus on technical specifications, equipment performance, and system integration\n"
        personalization += "- Include automation, sensors, IoT, and data management systems\n"
        personalization += "- Discuss ROI, equipment selection criteria, and maintenance requirements\n"
        personalization += "- Reference technical standards and equipment performance metrics\n"

    else:
        # Generic fallback (no category or category='other')
        personalization += "\n\n👤 EXPERTISE LEVEL: GENERAL POULTRY PROFESSIONAL\n"
        personalization += "Response Style:\n"
        personalization += "- Provide balanced, accessible information suitable for various backgrounds\n"
        personalization += "- Explain technical concepts clearly with practical context\n"
        personalization += "- Offer both practical and theoretical insights\n"
        personalization += "- Define technical terms when first introduced\n"

    # Add instruction to respect the personalization
    personalization += "\n⚠️ IMPORTANT: Adapt your response according to the user context above. Respect the specified expertise level and focus areas.\n"

    # Combine base prompt with personalization
    final_prompt = base_prompt + personalization

    logger.info(f"✅ System prompt personalized (production_type={production_types}, category={category})")

    return final_prompt


def build_weaviate_filter(user_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Construit un filtre Weaviate basé sur le profil utilisateur

    Filtre les documents par production_type pour ne retourner que les documents pertinents.

    Args:
        user_profile: {production_type: [...], category: str}

    Returns:
        Filtre Weaviate compatible avec where clause, ou None si pas de filtre

    Example return:
        {
            "operator": "Or",
            "operands": [
                {
                    "path": ["production_type"],
                    "operator": "Equal",
                    "valueText": "broiler"
                },
                {
                    "path": ["production_type"],
                    "operator": "Equal",
                    "valueText": "general"
                }
            ]
        }
    """
    production_types = user_profile.get('production_type', [])

    if not production_types:
        # Pas de filtre si production_type non défini
        logger.info("ℹ️ No production_type filter applied (user has no production type set)")
        return None

    # Construire la liste des types à inclure
    # Toujours inclure 'general' (documents applicables à tous)
    types_to_include = list(production_types) + ['general']

    # Si l'utilisateur a broiler ET layer, inclure aussi 'both'
    if 'broiler' in production_types and 'layer' in production_types:
        types_to_include.append('both')

    # Construire le filtre Weaviate
    if len(types_to_include) == 1:
        # Un seul type: filtre simple
        weaviate_filter = {
            "path": ["production_type"],
            "operator": "Equal",
            "valueText": types_to_include[0]
        }
    else:
        # Plusieurs types: filtre OR
        operands = []
        for prod_type in types_to_include:
            operands.append({
                "path": ["production_type"],
                "operator": "Equal",
                "valueText": prod_type
            })

        weaviate_filter = {
            "operator": "Or",
            "operands": operands
        }

    logger.info(f"✅ Weaviate filter built: production_types={types_to_include}")

    return weaviate_filter
