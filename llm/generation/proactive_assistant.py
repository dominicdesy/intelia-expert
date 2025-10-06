# -*- coding: utf-8 -*-
"""
proactive_assistant.py - Proactive Follow-up Questions Generator

Transforms the system from a passive data provider to an active assistant
that offers help and guidance after answering queries.

Features:
- Context-aware follow-up questions based on query intent
- Domain-specific assistance offers (production, health, nutrition, etc.)
- Multilingual support (12 languages: FR, EN, ES, DE, IT, PT, PL, NL, ID, HI, ZH, TH)
- Configurable tone (helpful, professional, friendly)

Version: 2.0 (Multilingual Release)
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class AssistanceContext(Enum):
    """Types of assistance contexts for follow-up questions"""

    PERFORMANCE_ISSUE = "performance_issue"  # Low weight, high FCR, etc.
    HEALTH_CONCERN = "health_concern"  # Mortality, disease symptoms
    OPTIMIZATION = "optimization"  # How to improve metrics
    COMPARISON = "comparison"  # Comparing breeds/strategies
    PLANNING = "planning"  # Future planning questions
    GENERAL_INFO = "general_info"  # Simple data lookup


class ProactiveAssistant:
    """
    Generates contextual follow-up questions to help users

    The assistant analyzes the query and response to offer relevant help,
    transforming a simple Q&A into an interactive conversation.

    Example:
        User: "Quel poids pour Ross 308 à 35 jours ?"
        System: "Le poids cible est 2.2-2.4 kg."
        Assistant: "Avez-vous un problème avec le poids de vos oiseaux ? Comment puis-je vous aider ?"
    """

    def __init__(self, default_language: str = "fr"):
        """
        Initialize proactive assistant

        Args:
            default_language: Default language for follow-up questions (fr/en/es)
        """
        self.default_language = default_language
        self.follow_up_templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Load follow-up question templates by context and language

        Returns:
            {
                "performance_issue": {
                    "fr": ["Question en français", ...],
                    "en": ["Question in English", ...],
                    "es": ["Pregunta en español", ...]
                },
                ...
            }
        """
        return {
            AssistanceContext.PERFORMANCE_ISSUE.value: {
                "fr": [
                    "Puis-je vous aider à optimiser le {metric} de vos oiseaux ?",
                    "Souhaitez-vous des conseils pour améliorer ces résultats ?",
                    "Avez-vous besoin d'aide pour analyser ces données de performance ?",
                ],
                "en": [
                    "Can I help you optimize your bird {metric}?",
                    "Would you like advice to improve these results?",
                    "Do you need help analyzing these performance data?",
                ],
                "es": [
                    "¿Puedo ayudarlo a optimizar el {metric} de sus aves?",
                    "¿Quisiera consejos para mejorar estos resultados?",
                    "¿Necesita ayuda para analizar estos datos de rendimiento?",
                ],
                "de": [
                    "Kann ich Ihnen helfen, den {metric} Ihrer Vögel zu optimieren?",
                    "Möchten Sie Ratschläge zur Verbesserung dieser Ergebnisse?",
                    "Benötigen Sie Hilfe bei der Analyse dieser Leistungsdaten?",
                ],
                "it": [
                    "Posso aiutarla a ottimizzare il {metric} dei suoi uccelli?",
                    "Desidera consigli per migliorare questi risultati?",
                    "Ha bisogno di aiuto per analizzare questi dati di prestazione?",
                ],
                "pt": [
                    "Posso ajudá-lo a otimizar o {metric} de suas aves?",
                    "Gostaria de conselhos para melhorar estes resultados?",
                    "Precisa de ajuda para analisar esses dados de desempenho?",
                ],
                "pl": [
                    "Czy mogę pomóc w optymalizacji {metric} Pana/Pani ptaków?",
                    "Czy chciałby Pan/Pani porady dotyczące poprawy tych wyników?",
                    "Czy potrzebuje Pan/Pani pomocy w analizie tych danych wydajnościowych?",
                ],
                "nl": [
                    "Kan ik u helpen de {metric} van uw vogels te optimaliseren?",
                    "Wilt u advies om deze resultaten te verbeteren?",
                    "Heeft u hulp nodig bij het analyseren van deze prestatiegegevens?",
                ],
                "id": [
                    "Dapatkah saya membantu Anda mengoptimalkan {metric} burung Anda?",
                    "Apakah Anda ingin saran untuk meningkatkan hasil ini?",
                    "Apakah Anda memerlukan bantuan untuk menganalisis data kinerja ini?",
                ],
                "hi": [
                    "क्या मैं आपके पक्षियों की {metric} को अनुकूलित करने में मदद कर सकता हूं?",
                    "क्या आप इन परिणामों को बेहतर बनाने के लिए सलाह चाहेंगे?",
                    "क्या आपको इन प्रदर्शन डेटा का विश्लेषण करने में सहायता की आवश्यकता है?",
                ],
                "zh": [
                    "我可以帮您优化禽类的{metric}吗？",
                    "您想要改善这些结果的建议吗？",
                    "您需要帮助分析这些性能数据吗？",
                ],
                "th": [
                    "ฉันสามารถช่วยคุณเพิ่มประสิทธิภาพ{metric}ของสัตว์ปีกได้หรือไม่?",
                    "คุณต้องการคำแนะนำเพื่อปรับปรุงผลลัพธ์เหล่านี้หรือไม่?",
                    "คุณต้องการความช่วยเหลือในการวิเคราะห์ข้อมูลประสิทธิภาพเหล่านี้หรือไม่?",
                ],
            },
            AssistanceContext.HEALTH_CONCERN.value: {
                "fr": [
                    "Observez-vous des symptômes de {disease} dans votre élevage ? Je peux vous aider avec le diagnostic.",
                    "Avez-vous besoin de conseils sur la prévention ou le traitement ? Je suis là pour vous aider.",
                    "Voulez-vous en savoir plus sur les protocoles de vaccination et biosécurité ?",
                ],
                "en": [
                    "Are you observing {disease} symptoms in your flock? I can help with diagnosis.",
                    "Do you need advice on prevention or treatment? I'm here to help.",
                    "Would you like to know more about vaccination protocols and biosecurity?",
                ],
                "es": [
                    "¿Observa síntomas de {disease} en su lote? Puedo ayudarlo con el diagnóstico.",
                    "¿Necesita consejos sobre prevención o tratamiento? Estoy aquí para ayudar.",
                    "¿Le gustaría saber más sobre protocolos de vacunación y bioseguridad?",
                ],
                "de": [
                    "Beobachten Sie {disease}-Symptome in Ihrer Herde? Ich kann bei der Diagnose helfen.",
                    "Benötigen Sie Ratschläge zur Vorbeugung oder Behandlung? Ich bin hier um zu helfen.",
                    "Möchten Sie mehr über Impfprotokolle und Biosicherheit erfahren?",
                ],
                "it": [
                    "Sta osservando sintomi di {disease} nel suo allevamento? Posso aiutare con la diagnosi.",
                    "Ha bisogno di consigli sulla prevenzione o il trattamento? Sono qui per aiutare.",
                    "Vuole saperne di più sui protocolli di vaccinazione e biosicurezza?",
                ],
                "pt": [
                    "Está observando sintomas de {disease} em seu lote? Posso ajudar com o diagnóstico.",
                    "Precisa de conselhos sobre prevenção ou tratamento? Estou aqui para ajudar.",
                    "Gostaria de saber mais sobre protocolos de vacinação e biossegurança?",
                ],
                "pl": [
                    "Czy obserwuje Pan/Pani objawy {disease} w stadzie? Mogę pomóc w diagnozie.",
                    "Czy potrzebuje Pan/Pani porady dotyczącej profilaktyki lub leczenia? Jestem tu aby pomóc.",
                    "Czy chciałby Pan/Pani dowiedzieć się więcej o protokołach szczepień i biosekuryzacji?",
                ],
                "nl": [
                    "Observeert u {disease}-symptomen in uw koppel? Ik kan helpen met de diagnose.",
                    "Heeft u advies nodig over preventie of behandeling? Ik ben hier om te helpen.",
                    "Wilt u meer weten over vaccinatieprotocollen en bioveiligheid?",
                ],
                "id": [
                    "Apakah Anda mengamati gejala {disease} di kawanan Anda? Saya dapat membantu dengan diagnosis.",
                    "Apakah Anda memerlukan saran tentang pencegahan atau pengobatan? Saya di sini untuk membantu.",
                    "Apakah Anda ingin tahu lebih banyak tentang protokol vaksinasi dan biosekuriti?",
                ],
                "hi": [
                    "क्या आप अपने झुंड में {disease} के लक्षण देख रहे हैं? मैं निदान में मदद कर सकता हूं।",
                    "क्या आपको रोकथाम या उपचार पर सलाह चाहिए? मैं मदद के लिए यहाँ हूँ।",
                    "क्या आप टीकाकरण प्रोटोकॉल और जैव सुरक्षा के बारे में अधिक जानना चाहेंगे?",
                ],
                "zh": [
                    "您在禽群中观察到{disease}症状了吗？我可以帮助诊断。",
                    "您需要预防或治疗方面的建议吗？我在这里提供帮助。",
                    "您想了解更多关于疫苗接种方案和生物安全的信息吗？",
                ],
                "th": [
                    "คุณสังเกตอาการ{disease}ในฝูงของคุณหรือไม่? ฉันสามารถช่วยในการวินิจฉัย",
                    "คุณต้องการคำแนะนำเกี่ยวกับการป้องกันหรือการรักษาหรือไม่? ฉันอยู่ที่นี่เพื่อช่วยเหลือ",
                    "คุณต้องการทราบข้อมูลเพิ่มเติมเกี่ยวกับโปรโตคอลการฉีดวัคซีนและความปลอดภัยทางชีวภาพหรือไม่?",
                ],
            },
            AssistanceContext.OPTIMIZATION.value: {
                "fr": ["Voulez-vous optimiser le {metric} de vos oiseaux ? Je peux vous suggérer des stratégies.", "Souhaitez-vous des recommandations pour améliorer les performances de votre élevage ?", "Puis-je vous aider à identifier les facteurs clés pour améliorer vos résultats ?"],
                "en": ["Would you like to optimize your bird {metric}? I can suggest strategies.", "Would you like recommendations to improve your flock performance?", "Can I help you identify key factors to improve your results?"],
                "es": ["¿Le gustaría optimizar el {metric} de sus aves? Puedo sugerir estrategias.", "¿Quisiera recomendaciones para mejorar el rendimiento de su lote?", "¿Puedo ayudarlo a identificar factores clave para mejorar sus resultados?"],
                "de": ["Möchten Sie den {metric} Ihrer Vögel optimieren? Ich kann Strategien vorschlagen.", "Möchten Sie Empfehlungen zur Verbesserung der Leistung Ihrer Herde?", "Kann ich Ihnen helfen, Schlüsselfaktoren zur Verbesserung Ihrer Ergebnisse zu identifizieren?"],
                "it": ["Vuole ottimizzare il {metric} dei suoi uccelli? Posso suggerire strategie.", "Desidera raccomandazioni per migliorare le prestazioni del suo allevamento?", "Posso aiutarla a identificare i fattori chiave per migliorare i suoi risultati?"],
                "pt": ["Gostaria de otimizar o {metric} de suas aves? Posso sugerir estratégias.", "Gostaria de recomendações para melhorar o desempenho de seu lote?", "Posso ajudá-lo a identificar fatores-chave para melhorar seus resultados?"],
                "pl": ["Czy chciałby Pan/Pani zoptymalizować {metric} swoich ptaków? Mogę zasugerować strategie.", "Czy chciałby Pan/Pani rekomendacje w celu poprawy wyników stada?", "Czy mogę pomóc zidentyfikować kluczowe czynniki poprawy wyników?"],
                "nl": ["Wilt u de {metric} van uw vogels optimaliseren? Ik kan strategieën voorstellen.", "Wilt u aanbevelingen om de prestaties van uw koppel te verbeteren?", "Kan ik u helpen belangrijke factoren te identificeren om uw resultaten te verbeteren?"],
                "id": ["Apakah Anda ingin mengoptimalkan {metric} burung Anda? Saya dapat menyarankan strategi.", "Apakah Anda ingin rekomendasi untuk meningkatkan kinerja kawanan Anda?", "Dapatkah saya membantu Anda mengidentifikasi faktor kunci untuk meningkatkan hasil Anda?"],
                "hi": ["क्या आप अपने पक्षियों की {metric} को अनुकूलित करना चाहेंगे? मैं रणनीतियाँ सुझा सकता हूं।", "क्या आप अपने झुंड के प्रदर्शन को बेहतर बनाने के लिए सिफारिशें चाहेंगे?", "क्या मैं आपके परिणामों को बेहतर बनाने के लिए प्रमुख कारकों की पहचान करने में मदद कर सकता हूं?"],
                "zh": ["您想优化禽类的{metric}吗？我可以建议策略。", "您想要改善禽群表现的建议吗？", "我能帮您识别改善结果的关键因素吗？"],
                "th": ["คุณต้องการเพิ่มประสิทธิภาพ{metric}ของสัตว์ปีกหรือไม่? ฉันสามารถแนะนำกลยุทธ์", "คุณต้องการคำแนะนำเพื่อปรับปรุงประสิทธิภาพฝูงของคุณหรือไม่?", "ฉันสามารถช่วยคุณระบุปัจจัยสำคัญในการปรับปรุงผลลัพธ์ได้หรือไม่?"],
            },
            AssistanceContext.COMPARISON.value: {
                "fr": ["Voulez-vous comparer ces résultats avec une autre race ou période ?", "Souhaitez-vous analyser les différences en détail ? Je peux vous aider.", "Puis-je vous recommander la meilleure option pour votre situation ?"],
                "en": ["Would you like to compare these results with another breed or period?", "Would you like to analyze the differences in detail? I can help.", "Can I recommend the best option for your situation?"],
                "es": ["¿Le gustaría comparar estos resultados con otra raza o período?", "¿Quisiera analizar las diferencias en detalle? Puedo ayudar.", "¿Puedo recomendar la mejor opción para su situación?"],
                "de": ["Möchten Sie diese Ergebnisse mit einer anderen Rasse oder Periode vergleichen?", "Möchten Sie die Unterschiede im Detail analysieren? Ich kann helfen.", "Kann ich die beste Option für Ihre Situation empfehlen?"],
                "it": ["Vuole confrontare questi risultati con un'altra razza o periodo?", "Desidera analizzare le differenze in dettaglio? Posso aiutare.", "Posso raccomandare la migliore opzione per la sua situazione?"],
                "pt": ["Gostaria de comparar estes resultados com outra raça ou período?", "Gostaria de analisar as diferenças em detalhe? Posso ajudar.", "Posso recomendar a melhor opção para sua situação?"],
                "pl": ["Czy chciałby Pan/Pani porównać te wyniki z inną rasą lub okresem?", "Czy chciałby Pan/Pani szczegółowo przeanalizować różnice? Mogę pomóc.", "Czy mogę polecić najlepszą opcję dla Pana/Pani sytuacji?"],
                "nl": ["Wilt u deze resultaten vergelijken met een ander ras of periode?", "Wilt u de verschillen in detail analyseren? Ik kan helpen.", "Kan ik de beste optie voor uw situatie aanbevelen?"],
                "id": ["Apakah Anda ingin membandingkan hasil ini dengan breed atau periode lain?", "Apakah Anda ingin menganalisis perbedaan secara detail? Saya dapat membantu.", "Dapatkah saya merekomendasikan opsi terbaik untuk situasi Anda?"],
                "hi": ["क्या आप इन परिणामों की तुलना किसी अन्य नस्ल या अवधि से करना चाहेंगे?", "क्या आप अंतर का विस्तार से विश्लेषण करना चाहेंगे? मैं मदद कर सकता हूं।", "क्या मैं आपकी स्थिति के लिए सर्वोत्तम विकल्प सुझा सकता हूं?"],
                "zh": ["您想将这些结果与另一个品种或时期进行比较吗？", "您想详细分析差异吗？我可以帮忙。", "我能为您的情况推荐最佳选择吗？"],
                "th": ["คุณต้องการเปรียบเทียบผลลัพธ์เหล่านี้กับสายพันธุ์หรือช่วงเวลาอื่นหรือไม่?", "คุณต้องการวิเคราะห์ความแตกต่างโดยละเอียดหรือไม่? ฉันสามารถช่วยได้", "ฉันสามารถแนะนำตัวเลือกที่ดีที่สุดสำหรับสถานการณ์ของคุณได้หรือไม่?"],
            },
            AssistanceContext.PLANNING.value: {
                "fr": ["Avez-vous besoin d'aide pour planifier votre prochaine bande ?", "Voulez-vous des prévisions de performance pour votre élevage ?", "Puis-je vous aider à établir un calendrier de gestion optimal ?"],
                "en": ["Do you need help planning your next flock?", "Would you like performance forecasts for your farm?", "Can I help you establish an optimal management schedule?"],
                "es": ["¿Necesita ayuda para planificar su próximo lote?", "¿Quisiera pronósticos de rendimiento para su granja?", "¿Puedo ayudarlo a establecer un calendario de gestión óptimo?"],
                "de": ["Benötigen Sie Hilfe bei der Planung Ihrer nächsten Herde?", "Möchten Sie Leistungsprognosen für Ihren Betrieb?", "Kann ich Ihnen helfen, einen optimalen Verwaltungsplan zu erstellen?"],
                "it": ["Ha bisogno di aiuto per pianificare il suo prossimo lotto?", "Vuole previsioni di prestazioni per il suo allevamento?", "Posso aiutarla a stabilire un programma di gestione ottimale?"],
                "pt": ["Precisa de ajuda para planejar seu próximo lote?", "Gostaria de previsões de desempenho para sua fazenda?", "Posso ajudá-lo a estabelecer um cronograma de gestão ideal?"],
                "pl": ["Czy potrzebuje Pan/Pani pomocy w planowaniu następnego stada?", "Czy chciałby Pan/Pani prognozy wydajności dla swojego gospodarstwa?", "Czy mogę pomóc ustalić optymalny harmonogram zarządzania?"],
                "nl": ["Heeft u hulp nodig bij het plannen van uw volgende koppel?", "Wilt u prestatievoorspellingen voor uw bedrijf?", "Kan ik u helpen een optimaal beheerplan op te stellen?"],
                "id": ["Apakah Anda memerlukan bantuan merencanakan kawanan berikutnya?", "Apakah Anda ingin perkiraan kinerja untuk peternakan Anda?", "Dapatkah saya membantu Anda membuat jadwal manajemen yang optimal?"],
                "hi": ["क्या आपको अपने अगले झुंड की योजना बनाने में सहायता चाहिए?", "क्या आप अपने फार्म के लिए प्रदर्शन पूर्वानुमान चाहेंगे?", "क्या मैं आपको एक इष्टतम प्रबंधन कार्यक्रम स्थापित करने में मदद कर सकता हूं?"],
                "zh": ["您需要帮助规划下一批禽群吗？", "您想要您农场的性能预测吗？", "我能帮您建立最佳管理计划吗？"],
                "th": ["คุณต้องการความช่วยเหลือในการวางแผนฝูงถัดไปหรือไม่?", "คุณต้องการการคาดการณ์ประสิทธิภาพสำหรับฟาร์มของคุณหรือไม่?", "ฉันสามารถช่วยคุณสร้างตารางการจัดการที่เหมาะสมได้หรือไม่?"],
            },
            AssistanceContext.GENERAL_INFO.value: {
                "fr": ["Avez-vous d'autres questions sur cette race ou ces données ?", "Puis-je vous aider avec d'autres informations ?", "Voulez-vous en savoir plus sur un aspect spécifique ?"],
                "en": ["Do you have other questions about this breed or data?", "Can I help you with additional information?", "Would you like to know more about a specific aspect?"],
                "es": ["¿Tiene otras preguntas sobre esta raza o estos datos?", "¿Puedo ayudarlo con información adicional?", "¿Le gustaría saber más sobre un aspecto específico?"],
                "de": ["Haben Sie weitere Fragen zu dieser Rasse oder diesen Daten?", "Kann ich Ihnen mit weiteren Informationen helfen?", "Möchten Sie mehr über einen bestimmten Aspekt erfahren?"],
                "it": ["Ha altre domande su questa razza o questi dati?", "Posso aiutarla con informazioni aggiuntive?", "Vuole saperne di più su un aspetto specifico?"],
                "pt": ["Você tem outras perguntas sobre esta raça ou estes dados?", "Posso ajudá-lo com informações adicionais?", "Gostaria de saber mais sobre um aspecto específico?"],
                "pl": ["Czy ma Pan/Pani inne pytania dotyczące tej rasy lub tych danych?", "Czy mogę pomóc z dodatkowymi informacjami?", "Czy chciałby Pan/Pani dowiedzieć się więcej o konkretnym aspekcie?"],
                "nl": ["Heeft u andere vragen over dit ras of deze gegevens?", "Kan ik u helpen met aanvullende informatie?", "Wilt u meer weten over een specifiek aspect?"],
                "id": ["Apakah Anda memiliki pertanyaan lain tentang breed atau data ini?", "Dapatkah saya membantu Anda dengan informasi tambahan?", "Apakah Anda ingin tahu lebih banyak tentang aspek tertentu?"],
                "hi": ["क्या आपके पास इस नस्ल या डेटा के बारे में अन्य प्रश्न हैं?", "क्या मैं अतिरिक्त जानकारी से आपकी सहायता कर सकता हूं?", "क्या आप किसी विशिष्ट पहलू के बारे में अधिक जानना चाहेंगे?"],
                "zh": ["您对这个品种或数据有其他问题吗？", "我能为您提供更多信息吗？", "您想了解更多关于特定方面的信息吗？"],
                "th": ["คุณมีคำถามอื่นเกี่ยวกับสายพันธุ์หรือข้อมูลนี้หรือไม่?", "ฉันสามารถช่วยคุณด้วยข้อมูลเพิ่มเติมได้หรือไม่?", "คุณต้องการทราบข้อมูลเพิ่มเติมเกี่ยวกับด้านใดด้านหนึ่งหรือไม่?"],
            },
        }

    def generate_follow_up(
        self,
        query: str,
        response: str,
        intent_result: Optional[Dict[str, Any]] = None,
        entities: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
    ) -> str:
        """
        Generate contextual follow-up question based on query and response

        Args:
            query: Original user query
            response: Generated response
            intent_result: Intent classification result (query_type, domain, etc.)
            entities: Extracted entities (breed, age, metric_type, etc.)
            language: Target language (fr/en/es/de/it/pt/pl/nl/id/hi/zh/th)

        Returns:
            Follow-up question string, or empty string if no follow-up needed

        Example:
            >>> assistant = ProactiveAssistant()
            >>> follow_up = assistant.generate_follow_up(
            ...     query="Quel poids pour Ross 308 à 35 jours ?",
            ...     response="Le poids cible est 2.2-2.4 kg.",
            ...     entities={"metric_type": "body_weight"},
            ...     language="fr"
            ... )
            >>> print(follow_up)
            "Avez-vous un problème avec le poids de vos oiseaux ? Comment puis-je vous aider ?"
        """
        lang = language or self.default_language

        # Validate language - support 12 languages
        supported_languages = ["fr", "en", "es", "de", "it", "pt", "pl", "nl", "id", "hi", "zh", "th"]
        if lang not in supported_languages:
            lang = "fr"  # Fallback to French

        # Determine assistance context
        context = self._identify_context(query, response, intent_result, entities)

        # 🆕 ONLY generate follow-ups for specific contexts (not for simple data lookup)
        enabled_contexts = [
            AssistanceContext.PERFORMANCE_ISSUE,
            AssistanceContext.HEALTH_CONCERN,
            AssistanceContext.OPTIMIZATION,
        ]

        if context not in enabled_contexts:
            logger.debug(
                f"Follow-up disabled for context={context.value} "
                f"(only enabled for: {[c.value for c in enabled_contexts]})"
            )
            return ""

        # Get appropriate template
        templates = self.follow_up_templates.get(context.value, {}).get(lang, [])

        if not templates:
            logger.debug(f"No follow-up template for context={context}, lang={lang}")
            return ""

        # Select first template (could be randomized later)
        template = templates[0]

        # Fill template with context variables
        follow_up = self._fill_template(template, entities, lang)

        logger.info(f"Generated follow-up (context={context.value}): {follow_up}")
        return follow_up

    def _identify_context(
        self,
        query: str,
        response: str,
        intent_result: Optional[Dict[str, Any]],
        entities: Optional[Dict[str, Any]],
    ) -> AssistanceContext:
        """
        Identify the appropriate assistance context from query analysis

        Args:
            query: User query
            response: Generated response
            intent_result: Intent classification
            entities: Extracted entities

        Returns:
            AssistanceContext enum value
        """
        query_lower = query.lower()
        entities = entities or {}

        # Health-related queries
        if intent_result and intent_result.get("domain") == "health":
            return AssistanceContext.HEALTH_CONCERN

        health_keywords = [
            "mortalité",
            "mortality",
            "mortalidad",
            "maladie",
            "disease",
            "enfermedad",
            "symptôme",
            "symptom",
            "síntoma",
            "traitement",
            "treatment",
            "tratamiento",
        ]
        if any(keyword in query_lower for keyword in health_keywords):
            return AssistanceContext.HEALTH_CONCERN

        # Comparison queries
        if intent_result and intent_result.get("query_type") in [
            "comparative",
            "comparison",
        ]:
            return AssistanceContext.COMPARISON

        comparison_keywords = ["compare", "comparer", "comparar", "vs", "versus"]
        if any(keyword in query_lower for keyword in comparison_keywords):
            return AssistanceContext.COMPARISON

        # Optimization/improvement queries
        optimization_keywords = [
            "optimiser",
            "optimize",
            "optimizar",
            "améliorer",
            "improve",
            "mejorar",
            "augmenter",
            "increase",
            "aumentar",
            "comment",
            "how",
            "cómo",
        ]
        if any(keyword in query_lower for keyword in optimization_keywords):
            return AssistanceContext.OPTIMIZATION

        # Planning queries
        planning_keywords = [
            "planifier",
            "planning",
            "planificar",
            "prochaine",
            "next",
            "próximo",
            "prévision",
            "forecast",
            "pronóstico",
        ]
        if any(keyword in query_lower for keyword in planning_keywords):
            return AssistanceContext.PLANNING

        # Performance metrics = likely performance issue
        metric_keywords = ["poids", "weight", "peso", "fcr", "gain", "conversion"]
        if any(keyword in query_lower for keyword in metric_keywords):
            return AssistanceContext.PERFORMANCE_ISSUE

        # Default: general info
        return AssistanceContext.GENERAL_INFO

    def _fill_template(
        self, template: str, entities: Optional[Dict[str, Any]], language: str
    ) -> str:
        """
        Fill template placeholders with actual values

        Args:
            template: Template string with {placeholders}
            entities: Extracted entities
            language: Target language

        Returns:
            Filled template string

        🆕 VALIDATION: Check that all placeholders have values before filling
        If a placeholder is missing, use generic template without placeholders
        """
        entities = entities or {}

        # 🆕 DETECT PLACEHOLDERS in template
        import re
        placeholders = re.findall(r'\{(\w+)\}', template)

        # 🆕 VALIDATE all placeholders have values
        missing_placeholders = []
        for placeholder in placeholders:
            if placeholder == "metric":
                if not entities.get("metric_type"):
                    missing_placeholders.append(placeholder)
            elif placeholder == "disease":
                if not entities.get("disease_name"):
                    missing_placeholders.append(placeholder)

        # 🆕 If ANY placeholder is missing, use generic template
        if missing_placeholders:
            logger.warning(
                f"Template placeholders missing: {missing_placeholders} - using generic template"
            )
            generic_templates = {
                "fr": "Puis-je vous aider avec autre chose ?",
                "en": "Can I help you with anything else?",
                "es": "¿Puedo ayudarlo con algo más?",
                "de": "Kann ich Ihnen sonst noch weiterhelfen?",
                "it": "Posso aiutarla con qualcos'altro?",
                "pt": "Posso ajudá-lo com mais alguma coisa?",
                "pl": "Czy mogę Panu/Pani pomóc w czymś innym?",
                "nl": "Kan ik u nog ergens anders mee helpen?",
                "id": "Dapatkah saya membantu Anda dengan hal lain?",
                "hi": "क्या मैं आपकी किसी और चीज़ में मदद कर सकता हूं?",
                "zh": "我还能帮您什么吗？",
                "th": "ฉันสามารถช่วยคุณในเรื่องอื่นได้หรือไม่?",
            }
            return generic_templates.get(language, generic_templates["fr"])

        # Metric name mapping by language
        metric_names = {
            "fr": {
                "body_weight": "poids",
                "feed_conversion_ratio": "FCR",
                "daily_gain": "gain quotidien",
                "mortality": "mortalité",
                "livability": "viabilité",
            },
            "en": {
                "body_weight": "weight",
                "feed_conversion_ratio": "FCR",
                "daily_gain": "daily gain",
                "mortality": "mortality",
                "livability": "livability",
            },
            "es": {
                "body_weight": "peso",
                "feed_conversion_ratio": "FCR",
                "daily_gain": "ganancia diaria",
                "mortality": "mortalidad",
                "livability": "viabilidad",
            },
        }

        # Get metric name in target language
        metric_type = entities.get("metric_type", "")
        metric_name = metric_names.get(language, {}).get(metric_type, metric_type)

        # Replace placeholders
        filled = template.replace("{metric}", metric_name)
        filled = filled.replace("{disease}", entities.get("disease_name", ""))

        return filled


def get_proactive_assistant(language: str = "fr") -> ProactiveAssistant:
    """
    Get or create singleton ProactiveAssistant instance

    Args:
        language: Default language

    Returns:
        ProactiveAssistant instance
    """
    return ProactiveAssistant(default_language=language)


__all__ = ["ProactiveAssistant", "AssistanceContext", "get_proactive_assistant"]
