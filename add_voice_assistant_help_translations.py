#!/usr/bin/env python3
"""
Script to add voice assistant help tour translations to all language files
"""

import json
from pathlib import Path

# Translation map for all languages
translations = {
    "de": {
        "help.voiceAssistantTitle": "Echtzeit-Sprachassistent",
        "help.voiceAssistantDesc": "Interaktive Sprachkonversation in Echtzeit. Sprechen Sie natürlich und erhalten Sie sofortige Sprachantworten."
    },
    "es": {
        "help.voiceAssistantTitle": "Asistente de voz en tiempo real",
        "help.voiceAssistantDesc": "Conversación de voz interactiva en tiempo real. Hable naturalmente y reciba respuestas de voz instantáneas."
    },
    "ar": {
        "help.voiceAssistantTitle": "المساعد الصوتي في الوقت الفعلي",
        "help.voiceAssistantDesc": "محادثة صوتية تفاعلية في الوقت الفعلي. تحدث بشكل طبيعي واحصل على ردود صوتية فورية."
    },
    "hi": {
        "help.voiceAssistantTitle": "रीयल-टाइम वॉयस असिस्टेंट",
        "help.voiceAssistantDesc": "रीयल-टाइम में इंटरैक्टिव वॉयस वार्तालाप। स्वाभाविक रूप से बोलें और तत्काल वॉयस प्रतिक्रियाएं प्राप्त करें।"
    },
    "id": {
        "help.voiceAssistantTitle": "Asisten suara waktu nyata",
        "help.voiceAssistantDesc": "Percakapan suara interaktif secara real-time. Bicaralah secara alami dan terima respons suara instan."
    },
    "it": {
        "help.voiceAssistantTitle": "Assistente vocale in tempo reale",
        "help.voiceAssistantDesc": "Conversazione vocale interattiva in tempo reale. Parla naturalmente e ricevi risposte vocali istantanee."
    },
    "ja": {
        "help.voiceAssistantTitle": "リアルタイム音声アシスタント",
        "help.voiceAssistantDesc": "リアルタイムでインタラクティブな音声会話。自然に話すと即座に音声で返答が得られます。"
    },
    "nl": {
        "help.voiceAssistantTitle": "Real-time spraakassistent",
        "help.voiceAssistantDesc": "Interactief spraakgesprek in real-time. Spreek natuurlijk en ontvang directe spraakrespons."
    },
    "pl": {
        "help.voiceAssistantTitle": "Asystent głosowy w czasie rzeczywistym",
        "help.voiceAssistantDesc": "Interaktywna rozmowa głosowa w czasie rzeczywistym. Mów naturalnie i otrzymuj natychmiastowe odpowiedzi głosowe."
    },
    "pt": {
        "help.voiceAssistantTitle": "Assistente de voz em tempo real",
        "help.voiceAssistantDesc": "Conversa de voz interativa em tempo real. Fale naturalmente e receba respostas de voz instantâneas."
    },
    "th": {
        "help.voiceAssistantTitle": "ผู้ช่วยเสียงแบบเรียลไทม์",
        "help.voiceAssistantDesc": "การสนทนาด้วยเสียงแบบโต้ตอบแบบเรียลไทม์ พูดอย่างเป็นธรรมชาติและรับการตอบกลับด้วยเสียงทันที"
    },
    "tr": {
        "help.voiceAssistantTitle": "Gerçek zamanlı sesli asistan",
        "help.voiceAssistantDesc": "Gerçek zamanlı etkileşimli sesli konuşma. Doğal şekilde konuşun ve anında sesli yanıtlar alın."
    },
    "vi": {
        "help.voiceAssistantTitle": "Trợ lý giọng nói thời gian thực",
        "help.voiceAssistantDesc": "Cuộc trò chuyện tương tác bằng giọng nói theo thời gian thực. Nói tự nhiên và nhận phản hồi giọng nói ngay lập tức."
    },
    "zh": {
        "help.voiceAssistantTitle": "实时语音助手",
        "help.voiceAssistantDesc": "实时互动语音对话。自然说话，即时获得语音回复。"
    }
}

def add_translations():
    """Add voice assistant help translations to all language files"""
    locales_dir = Path("frontend/public/locales")

    for lang_code, trans in translations.items():
        lang_file = locales_dir / f"{lang_code}.json"

        if not lang_file.exists():
            print(f"WARNING: Skipping {lang_code}.json (file not found)")
            continue

        # Read existing translations
        with open(lang_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Add new keys
        data["help.voiceAssistantTitle"] = trans["help.voiceAssistantTitle"]
        data["help.voiceAssistantDesc"] = trans["help.voiceAssistantDesc"]

        # Write back
        with open(lang_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] Updated {lang_code}.json")

if __name__ == "__main__":
    print("Adding voice assistant help tour translations...")
    add_translations()
    print("\n[OK] All translations added successfully!")
