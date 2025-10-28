"""
Script pour ajouter les descriptions de voix dans les fichiers i18n du backend
"""
import json
import os
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Traductions pour les 6 voix OpenAI
VOICE_DESCRIPTIONS = {
    "fr": {
        "voice.alloy.description": "Neutre et équilibré",
        "voice.echo.description": "Voix masculine claire",
        "voice.fable.description": "Accent britannique chaleureux",
        "voice.onyx.description": "Voix grave et masculine",
        "voice.nova.description": "Voix féminine énergique",
        "voice.shimmer.description": "Voix féminine douce"
    },
    "en": {
        "voice.alloy.description": "Neutral and balanced",
        "voice.echo.description": "Clear male voice",
        "voice.fable.description": "Warm British accent",
        "voice.onyx.description": "Deep male voice",
        "voice.nova.description": "Energetic female voice",
        "voice.shimmer.description": "Soft female voice"
    },
    "es": {
        "voice.alloy.description": "Neutral y equilibrado",
        "voice.echo.description": "Voz masculina clara",
        "voice.fable.description": "Acento británico cálido",
        "voice.onyx.description": "Voz masculina profunda",
        "voice.nova.description": "Voz femenina enérgica",
        "voice.shimmer.description": "Voz femenina suave"
    },
    "de": {
        "voice.alloy.description": "Neutral und ausgewogen",
        "voice.echo.description": "Klare männliche Stimme",
        "voice.fable.description": "Warmer britischer Akzent",
        "voice.onyx.description": "Tiefe männliche Stimme",
        "voice.nova.description": "Energische weibliche Stimme",
        "voice.shimmer.description": "Sanfte weibliche Stimme"
    },
    "pt": {
        "voice.alloy.description": "Neutro e equilibrado",
        "voice.echo.description": "Voz masculina clara",
        "voice.fable.description": "Sotaque britânico caloroso",
        "voice.onyx.description": "Voz masculina grave",
        "voice.nova.description": "Voz feminina enérgica",
        "voice.shimmer.description": "Voz feminina suave"
    },
    "it": {
        "voice.alloy.description": "Neutro ed equilibrato",
        "voice.echo.description": "Voce maschile chiara",
        "voice.fable.description": "Accento britannico caloroso",
        "voice.onyx.description": "Voce maschile profonda",
        "voice.nova.description": "Voce femminile energica",
        "voice.shimmer.description": "Voce femminile dolce"
    },
    "nl": {
        "voice.alloy.description": "Neutraal en evenwichtig",
        "voice.echo.description": "Heldere mannelijke stem",
        "voice.fable.description": "Warm Brits accent",
        "voice.onyx.description": "Diepe mannelijke stem",
        "voice.nova.description": "Energieke vrouwelijke stem",
        "voice.shimmer.description": "Zachte vrouwelijke stem"
    },
    "pl": {
        "voice.alloy.description": "Neutralny i zrównoważony",
        "voice.echo.description": "Wyraźny męski głos",
        "voice.fable.description": "Ciepły brytyjski akcent",
        "voice.onyx.description": "Głęboki męski głos",
        "voice.nova.description": "Energiczny kobiecy głos",
        "voice.shimmer.description": "Miękki kobiecy głos"
    },
    "zh": {
        "voice.alloy.description": "中性且平衡",
        "voice.echo.description": "清晰的男声",
        "voice.fable.description": "温暖的英国口音",
        "voice.onyx.description": "深沉的男声",
        "voice.nova.description": "充满活力的女声",
        "voice.shimmer.description": "柔和的女声"
    },
    "ja": {
        "voice.alloy.description": "ニュートラルでバランスが良い",
        "voice.echo.description": "明瞭な男性の声",
        "voice.fable.description": "温かいイギリス訛り",
        "voice.onyx.description": "深い男性の声",
        "voice.nova.description": "エネルギッシュな女性の声",
        "voice.shimmer.description": "柔らかい女性の声"
    },
    "hi": {
        "voice.alloy.description": "तटस्थ और संतुलित",
        "voice.echo.description": "स्पष्ट पुरुष आवाज",
        "voice.fable.description": "गर्म ब्रिटिश उच्चारण",
        "voice.onyx.description": "गहरी पुरुष आवाज",
        "voice.nova.description": "ऊर्जावान महिला आवाज",
        "voice.shimmer.description": "कोमल महिला आवाज"
    },
    "ar": {
        "voice.alloy.description": "محايد ومتوازن",
        "voice.echo.description": "صوت ذكوري واضح",
        "voice.fable.description": "لهجة بريطانية دافئة",
        "voice.onyx.description": "صوت ذكوري عميق",
        "voice.nova.description": "صوت أنثوي نشيط",
        "voice.shimmer.description": "صوت أنثوي ناعم"
    },
    "th": {
        "voice.alloy.description": "กลางและสมดุล",
        "voice.echo.description": "เสียงผู้ชายที่ชัดเจน",
        "voice.fable.description": "สำเนียงอังกฤษที่อบอุ่น",
        "voice.onyx.description": "เสียงผู้ชายที่ต่ำ",
        "voice.nova.description": "เสียงผู้หญิงที่มีพลัง",
        "voice.shimmer.description": "เสียงผู้หญิงที่นุ่มนวล"
    },
    "tr": {
        "voice.alloy.description": "Nötr ve dengeli",
        "voice.echo.description": "Net erkek sesi",
        "voice.fable.description": "Sıcak İngiliz aksanı",
        "voice.onyx.description": "Derin erkek sesi",
        "voice.nova.description": "Enerjik kadın sesi",
        "voice.shimmer.description": "Yumuşak kadın sesi"
    },
    "vi": {
        "voice.alloy.description": "Trung lập và cân bằng",
        "voice.echo.description": "Giọng nam rõ ràng",
        "voice.fable.description": "Giọng Anh ấm áp",
        "voice.onyx.description": "Giọng nam trầm",
        "voice.nova.description": "Giọng nữ năng động",
        "voice.shimmer.description": "Giọng nữ nhẹ nhàng"
    },
    "id": {
        "voice.alloy.description": "Netral dan seimbang",
        "voice.echo.description": "Suara pria yang jelas",
        "voice.fable.description": "Aksen Inggris yang hangat",
        "voice.onyx.description": "Suara pria yang dalam",
        "voice.nova.description": "Suara wanita yang energik",
        "voice.shimmer.description": "Suara wanita yang lembut"
    }
}

def add_voice_descriptions(file_path, lang_code):
    """Ajouter les descriptions de voix au fichier JSON"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Ajouter les traductions
    for key, value in VOICE_DESCRIPTIONS[lang_code].items():
        data[key] = value

    # Sauvegarder
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"OK {lang_code}.json: {len(VOICE_DESCRIPTIONS[lang_code])} descriptions ajoutees")

if __name__ == "__main__":
    backend_locales_dir = "backend/app/locales"

    for lang_code in VOICE_DESCRIPTIONS.keys():
        file_path = os.path.join(backend_locales_dir, f"{lang_code}.json")
        if os.path.exists(file_path):
            add_voice_descriptions(file_path, lang_code)
        else:
            print(f"ERROR {lang_code}.json non trouve")

    print(f"\nTermine! {len(VOICE_DESCRIPTIONS)} fichiers mis a jour avec 6 descriptions chacun")
