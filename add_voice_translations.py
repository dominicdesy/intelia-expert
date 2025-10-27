#!/usr/bin/env python3
"""
Script pour ajouter les traductions voice settings à tous les fichiers de langue
"""

import json
import os
from pathlib import Path

# Traductions pour voice settings
VOICE_TRANSLATIONS = {
    "fr": {
        "voiceSettings": {
            "title": "Assistant vocal",
            "selectVoice": "Sélection de la voix",
            "speed": "Vitesse de parole",
            "listen": "Écouter",
            "slower": "Plus lent",
            "normal": "Normal",
            "faster": "Plus rapide",
            "upgradeRequired": "Mise à niveau requise",
            "upgradeMessage": "L'assistant vocal est disponible uniquement pour les plans Elite et Intelia. Mettez à niveau votre abonnement pour accéder à cette fonctionnalité.",
            "currentPlan": "Votre plan actuel"
        },
        "success": {
            "voiceSettingsSaved": "Préférences vocales sauvegardées avec succès !"
        },
        "error": {
            "loadVoiceSettings": "Erreur lors du chargement des préférences vocales",
            "saveVoiceSettings": "Erreur lors de la sauvegarde des préférences vocales"
        },
        "passkey": {
            "addedOn": "Ajouté le"
        },
        "profile": {
            "security": "Sécurité"
        }
    },
    "en": {
        "voiceSettings": {
            "title": "Voice Assistant",
            "selectVoice": "Voice Selection",
            "speed": "Speech Speed",
            "listen": "Listen",
            "slower": "Slower",
            "normal": "Normal",
            "faster": "Faster",
            "upgradeRequired": "Upgrade Required",
            "upgradeMessage": "Voice assistant is only available for Elite and Intelia plans. Upgrade your plan to access this feature.",
            "currentPlan": "Your current plan"
        },
        "success": {
            "voiceSettingsSaved": "Voice settings saved successfully!"
        },
        "error": {
            "loadVoiceSettings": "Error loading voice settings",
            "saveVoiceSettings": "Error saving voice settings"
        },
        "passkey": {
            "addedOn": "Added on"
        },
        "profile": {
            "security": "Security"
        }
    },
    "es": {
        "voiceSettings": {
            "title": "Asistente de voz",
            "selectVoice": "Selección de voz",
            "speed": "Velocidad del habla",
            "listen": "Escuchar",
            "slower": "Más lento",
            "normal": "Normal",
            "faster": "Más rápido",
            "upgradeRequired": "Actualización requerida",
            "upgradeMessage": "El asistente de voz solo está disponible para los planes Elite e Intelia. Actualice su plan para acceder a esta función.",
            "currentPlan": "Su plan actual"
        },
        "success": {
            "voiceSettingsSaved": "¡Configuración de voz guardada con éxito!"
        },
        "error": {
            "loadVoiceSettings": "Error al cargar la configuración de voz",
            "saveVoiceSettings": "Error al guardar la configuración de voz"
        },
        "passkey": {
            "addedOn": "Agregado el"
        },
        "profile": {
            "security": "Seguridad"
        }
    },
    "de": {
        "voiceSettings": {
            "title": "Sprachassistent",
            "selectVoice": "Sprachauswahl",
            "speed": "Sprechgeschwindigkeit",
            "listen": "Anhören",
            "slower": "Langsamer",
            "normal": "Normal",
            "faster": "Schneller",
            "upgradeRequired": "Upgrade erforderlich",
            "upgradeMessage": "Der Sprachassistent ist nur für Elite- und Intelia-Pläne verfügbar. Aktualisieren Sie Ihren Plan, um auf diese Funktion zuzugreifen.",
            "currentPlan": "Ihr aktueller Plan"
        },
        "success": {
            "voiceSettingsSaved": "Spracheinstellungen erfolgreich gespeichert!"
        },
        "error": {
            "loadVoiceSettings": "Fehler beim Laden der Spracheinstellungen",
            "saveVoiceSettings": "Fehler beim Speichern der Spracheinstellungen"
        },
        "passkey": {
            "addedOn": "Hinzugefügt am"
        },
        "profile": {
            "security": "Sicherheit"
        }
    },
    "pt": {
        "voiceSettings": {
            "title": "Assistente de voz",
            "selectVoice": "Seleção de voz",
            "speed": "Velocidade da fala",
            "listen": "Ouvir",
            "slower": "Mais lento",
            "normal": "Normal",
            "faster": "Mais rápido",
            "upgradeRequired": "Atualização necessária",
            "upgradeMessage": "O assistente de voz está disponível apenas para planos Elite e Intelia. Atualize seu plano para acessar este recurso.",
            "currentPlan": "Seu plano atual"
        },
        "success": {
            "voiceSettingsSaved": "Configurações de voz salvas com sucesso!"
        },
        "error": {
            "loadVoiceSettings": "Erro ao carregar configurações de voz",
            "saveVoiceSettings": "Erro ao salvar configurações de voz"
        },
        "passkey": {
            "addedOn": "Adicionado em"
        },
        "profile": {
            "security": "Segurança"
        }
    },
    "it": {
        "voiceSettings": {
            "title": "Assistente vocale",
            "selectVoice": "Selezione voce",
            "speed": "Velocità del parlato",
            "listen": "Ascolta",
            "slower": "Più lento",
            "normal": "Normale",
            "faster": "Più veloce",
            "upgradeRequired": "Aggiornamento richiesto",
            "upgradeMessage": "L'assistente vocale è disponibile solo per i piani Elite e Intelia. Aggiorna il tuo piano per accedere a questa funzione.",
            "currentPlan": "Il tuo piano attuale"
        },
        "success": {
            "voiceSettingsSaved": "Impostazioni vocali salvate con successo!"
        },
        "error": {
            "loadVoiceSettings": "Errore nel caricamento delle impostazioni vocali",
            "saveVoiceSettings": "Errore nel salvataggio delle impostazioni vocali"
        },
        "passkey": {
            "addedOn": "Aggiunto il"
        },
        "profile": {
            "security": "Sicurezza"
        }
    },
    "nl": {
        "voiceSettings": {
            "title": "Spraakassistent",
            "selectVoice": "Stem selectie",
            "speed": "Spreeksnelheid",
            "listen": "Luisteren",
            "slower": "Langzamer",
            "normal": "Normaal",
            "faster": "Sneller",
            "upgradeRequired": "Upgrade vereist",
            "upgradeMessage": "Spraakassistent is alleen beschikbaar voor Elite en Intelia abonnementen. Upgrade uw abonnement om toegang te krijgen tot deze functie.",
            "currentPlan": "Uw huidige abonnement"
        },
        "success": {
            "voiceSettingsSaved": "Spraak instellingen succesvol opgeslagen!"
        },
        "error": {
            "loadVoiceSettings": "Fout bij het laden van spraak instellingen",
            "saveVoiceSettings": "Fout bij het opslaan van spraak instellingen"
        },
        "passkey": {
            "addedOn": "Toegevoegd op"
        },
        "profile": {
            "security": "Beveiliging"
        }
    },
    "pl": {
        "voiceSettings": {
            "title": "Asystent głosowy",
            "selectVoice": "Wybór głosu",
            "speed": "Prędkość mowy",
            "listen": "Słuchaj",
            "slower": "Wolniej",
            "normal": "Normalny",
            "faster": "Szybciej",
            "upgradeRequired": "Wymagana aktualizacja",
            "upgradeMessage": "Asystent głosowy jest dostępny tylko dla planów Elite i Intelia. Zaktualizuj swój plan, aby uzyskać dostęp do tej funkcji.",
            "currentPlan": "Twój obecny plan"
        },
        "success": {
            "voiceSettingsSaved": "Ustawienia głosu zapisane pomyślnie!"
        },
        "error": {
            "loadVoiceSettings": "Błąd ładowania ustawień głosu",
            "saveVoiceSettings": "Błąd zapisu ustawień głosu"
        },
        "passkey": {
            "addedOn": "Dodano"
        },
        "profile": {
            "security": "Bezpieczeństwo"
        }
    },
    "zh": {
        "voiceSettings": {
            "title": "语音助手",
            "selectVoice": "选择声音",
            "speed": "语速",
            "listen": "试听",
            "slower": "较慢",
            "normal": "正常",
            "faster": "较快",
            "upgradeRequired": "需要升级",
            "upgradeMessage": "语音助手仅适用于Elite和Intelia计划。升级您的计划以访问此功能。",
            "currentPlan": "您当前的计划"
        },
        "success": {
            "voiceSettingsSaved": "语音设置保存成功！"
        },
        "error": {
            "loadVoiceSettings": "加载语音设置时出错",
            "saveVoiceSettings": "保存语音设置时出错"
        },
        "passkey": {
            "addedOn": "添加于"
        },
        "profile": {
            "security": "安全"
        }
    },
    "ja": {
        "voiceSettings": {
            "title": "音声アシスタント",
            "selectVoice": "音声の選択",
            "speed": "話す速度",
            "listen": "聴く",
            "slower": "遅く",
            "normal": "通常",
            "faster": "速く",
            "upgradeRequired": "アップグレードが必要です",
            "upgradeMessage": "音声アシスタントはEliteとInteliaプランでのみ利用可能です。この機能にアクセスするにはプランをアップグレードしてください。",
            "currentPlan": "現在のプラン"
        },
        "success": {
            "voiceSettingsSaved": "音声設定が正常に保存されました！"
        },
        "error": {
            "loadVoiceSettings": "音声設定の読み込みエラー",
            "saveVoiceSettings": "音声設定の保存エラー"
        },
        "passkey": {
            "addedOn": "追加日"
        },
        "profile": {
            "security": "セキュリティ"
        }
    },
    "hi": {
        "voiceSettings": {
            "title": "आवाज सहायक",
            "selectVoice": "आवाज चयन",
            "speed": "बोलने की गति",
            "listen": "सुनें",
            "slower": "धीमा",
            "normal": "सामान्य",
            "faster": "तेज",
            "upgradeRequired": "अपग्रेड आवश्यक",
            "upgradeMessage": "आवाज सहायक केवल Elite और Intelia योजनाओं के लिए उपलब्ध है। इस सुविधा तक पहुंचने के लिए अपनी योजना अपग्रेड करें।",
            "currentPlan": "आपकी वर्तमान योजना"
        },
        "success": {
            "voiceSettingsSaved": "आवाज सेटिंग्स सफलतापूर्वक सहेजी गईं!"
        },
        "error": {
            "loadVoiceSettings": "आवाज सेटिंग्स लोड करने में त्रुटि",
            "saveVoiceSettings": "आवाज सेटिंग्स सहेजने में त्रुटि"
        },
        "passkey": {
            "addedOn": "जोड़ा गया"
        },
        "profile": {
            "security": "सुरक्षा"
        }
    },
    "ar": {
        "voiceSettings": {
            "title": "مساعد صوتي",
            "selectVoice": "اختيار الصوت",
            "speed": "سرعة الكلام",
            "listen": "استمع",
            "slower": "أبطأ",
            "normal": "عادي",
            "faster": "أسرع",
            "upgradeRequired": "الترقية مطلوبة",
            "upgradeMessage": "المساعد الصوتي متاح فقط لخطط Elite و Intelia. قم بترقية خطتك للوصول إلى هذه الميزة.",
            "currentPlan": "خطتك الحالية"
        },
        "success": {
            "voiceSettingsSaved": "تم حفظ إعدادات الصوت بنجاح!"
        },
        "error": {
            "loadVoiceSettings": "خطأ في تحميل إعدادات الصوت",
            "saveVoiceSettings": "خطأ في حفظ إعدادات الصوت"
        },
        "passkey": {
            "addedOn": "أضيف في"
        },
        "profile": {
            "security": "الأمان"
        }
    },
    "th": {
        "voiceSettings": {
            "title": "ผู้ช่วยเสียง",
            "selectVoice": "การเลือกเสียง",
            "speed": "ความเร็วในการพูด",
            "listen": "ฟัง",
            "slower": "ช้าลง",
            "normal": "ปกติ",
            "faster": "เร็วขึ้น",
            "upgradeRequired": "ต้องอัปเกรด",
            "upgradeMessage": "ผู้ช่วยเสียงใช้ได้เฉพาะแผน Elite และ Intelia เท่านั้น อัปเกรดแผนของคุณเพื่อเข้าถึงฟีเจอร์นี้",
            "currentPlan": "แผนปัจจุบันของคุณ"
        },
        "success": {
            "voiceSettingsSaved": "บันทึกการตั้งค่าเสียงสำเร็จ!"
        },
        "error": {
            "loadVoiceSettings": "เกิดข้อผิดพลาดในการโหลดการตั้งค่าเสียง",
            "saveVoiceSettings": "เกิดข้อผิดพลาดในการบันทึกการตั้งค่าเสียง"
        },
        "passkey": {
            "addedOn": "เพิ่มเมื่อ"
        },
        "profile": {
            "security": "ความปลอดภัย"
        }
    },
    "tr": {
        "voiceSettings": {
            "title": "Sesli asistan",
            "selectVoice": "Ses seçimi",
            "speed": "Konuşma hızı",
            "listen": "Dinle",
            "slower": "Daha yavaş",
            "normal": "Normal",
            "faster": "Daha hızlı",
            "upgradeRequired": "Yükseltme gerekli",
            "upgradeMessage": "Sesli asistan yalnızca Elite ve Intelia planları için kullanılabilir. Bu özelliğe erişmek için planınızı yükseltin.",
            "currentPlan": "Mevcut planınız"
        },
        "success": {
            "voiceSettingsSaved": "Ses ayarları başarıyla kaydedildi!"
        },
        "error": {
            "loadVoiceSettings": "Ses ayarları yüklenirken hata oluştu",
            "saveVoiceSettings": "Ses ayarları kaydedilirken hata oluştu"
        },
        "passkey": {
            "addedOn": "Eklenme tarihi"
        },
        "profile": {
            "security": "Güvenlik"
        }
    },
    "vi": {
        "voiceSettings": {
            "title": "Trợ lý giọng nói",
            "selectVoice": "Chọn giọng nói",
            "speed": "Tốc độ nói",
            "listen": "Nghe",
            "slower": "Chậm hơn",
            "normal": "Bình thường",
            "faster": "Nhanh hơn",
            "upgradeRequired": "Cần nâng cấp",
            "upgradeMessage": "Trợ lý giọng nói chỉ khả dụng cho gói Elite và Intelia. Nâng cấp gói của bạn để truy cập tính năng này.",
            "currentPlan": "Gói hiện tại của bạn"
        },
        "success": {
            "voiceSettingsSaved": "Lưu cài đặt giọng nói thành công!"
        },
        "error": {
            "loadVoiceSettings": "Lỗi tải cài đặt giọng nói",
            "saveVoiceSettings": "Lỗi lưu cài đặt giọng nói"
        },
        "passkey": {
            "addedOn": "Đã thêm vào"
        },
        "profile": {
            "security": "Bảo mật"
        }
    },
    "id": {
        "voiceSettings": {
            "title": "Asisten suara",
            "selectVoice": "Pemilihan suara",
            "speed": "Kecepatan bicara",
            "listen": "Dengarkan",
            "slower": "Lebih lambat",
            "normal": "Normal",
            "faster": "Lebih cepat",
            "upgradeRequired": "Upgrade diperlukan",
            "upgradeMessage": "Asisten suara hanya tersedia untuk paket Elite dan Intelia. Tingkatkan paket Anda untuk mengakses fitur ini.",
            "currentPlan": "Paket Anda saat ini"
        },
        "success": {
            "voiceSettingsSaved": "Pengaturan suara berhasil disimpan!"
        },
        "error": {
            "loadVoiceSettings": "Kesalahan memuat pengaturan suara",
            "saveVoiceSettings": "Kesalahan menyimpan pengaturan suara"
        },
        "passkey": {
            "addedOn": "Ditambahkan pada"
        },
        "profile": {
            "security": "Keamanan"
        }
    }
}

def deep_merge(dict1, dict2):
    """Merge dict2 into dict1 recursively"""
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            deep_merge(dict1[key], value)
        else:
            dict1[key] = value
    return dict1

def update_translation_file(file_path, lang_code):
    """Update a single translation file"""
    try:
        # Load existing translations
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Merge new translations
        translations = VOICE_TRANSLATIONS.get(lang_code, VOICE_TRANSLATIONS['en'])
        data = deep_merge(data, translations)

        # Save updated translations
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] Updated {file_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Error updating {file_path}: {e}")
        return False

def main():
    # Frontend translations
    frontend_dir = Path("frontend/public/locales")

    if frontend_dir.exists():
        print(f"\n[INFO] Updating frontend translations in {frontend_dir}")
        for lang_code in VOICE_TRANSLATIONS.keys():
            file_path = frontend_dir / f"{lang_code}.json"
            if file_path.exists():
                update_translation_file(file_path, lang_code)
            else:
                print(f"[WARN] Skipping {file_path} (does not exist)")

    print("\n[SUCCESS] All translation files updated!")
    print("\n[SUMMARY]")
    print(f"   - Languages: {len(VOICE_TRANSLATIONS)}")
    print(f"   - Keys per language: ~15")
    print(f"   - Categories: voiceSettings, success, error, passkey, profile")

if __name__ == "__main__":
    main()
