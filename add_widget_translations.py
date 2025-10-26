#!/usr/bin/env python3
"""
Script pour ajouter les traductions du widget dans tous les fichiers i18n
"""

import json
import os

# Définir les traductions pour chaque langue
WIDGET_TRANSLATIONS = {
    'en': {
        'widget.placeholder': 'Ask your question...',
        'widget.welcomeMessage': 'Hello! How can I help you?',
        'widget.buttonLabel': 'Need help?',
        'widget.sendButton': 'Send',
        'widget.errorNetwork': 'Connection error. Please try again.',
        'widget.errorToken': 'Authentication error.',
        'widget.errorQuota': 'Usage limit reached.'
    },
    'fr': {
        'widget.placeholder': 'Posez votre question...',
        'widget.welcomeMessage': 'Bonjour ! Comment puis-je vous aider ?',
        'widget.buttonLabel': 'Besoin d\'aide ?',
        'widget.sendButton': 'Envoyer',
        'widget.errorNetwork': 'Erreur de connexion. Veuillez réessayer.',
        'widget.errorToken': 'Erreur d\'authentification.',
        'widget.errorQuota': 'Limite d\'utilisation atteinte.'
    },
    'es': {
        'widget.placeholder': 'Haga su pregunta...',
        'widget.welcomeMessage': '¡Hola! ¿Cómo puedo ayudarle?',
        'widget.buttonLabel': '¿Necesita ayuda?',
        'widget.sendButton': 'Enviar',
        'widget.errorNetwork': 'Error de conexión. Por favor, inténtelo de nuevo.',
        'widget.errorToken': 'Error de autenticación.',
        'widget.errorQuota': 'Límite de uso alcanzado.'
    },
    'de': {
        'widget.placeholder': 'Stellen Sie Ihre Frage...',
        'widget.welcomeMessage': 'Hallo! Wie kann ich Ihnen helfen?',
        'widget.buttonLabel': 'Brauchen Sie Hilfe?',
        'widget.sendButton': 'Senden',
        'widget.errorNetwork': 'Verbindungsfehler. Bitte versuchen Sie es erneut.',
        'widget.errorToken': 'Authentifizierungsfehler.',
        'widget.errorQuota': 'Nutzungslimit erreicht.'
    },
    'it': {
        'widget.placeholder': 'Fai la tua domanda...',
        'widget.welcomeMessage': 'Ciao! Come posso aiutarti?',
        'widget.buttonLabel': 'Hai bisogno di aiuto?',
        'widget.sendButton': 'Invia',
        'widget.errorNetwork': 'Errore di connessione. Riprova.',
        'widget.errorToken': 'Errore di autenticazione.',
        'widget.errorQuota': 'Limite di utilizzo raggiunto.'
    },
    'pt': {
        'widget.placeholder': 'Faça sua pergunta...',
        'widget.welcomeMessage': 'Olá! Como posso ajudá-lo?',
        'widget.buttonLabel': 'Precisa de ajuda?',
        'widget.sendButton': 'Enviar',
        'widget.errorNetwork': 'Erro de conexão. Por favor, tente novamente.',
        'widget.errorToken': 'Erro de autenticação.',
        'widget.errorQuota': 'Limite de uso atingido.'
    },
    'nl': {
        'widget.placeholder': 'Stel uw vraag...',
        'widget.welcomeMessage': 'Hallo! Hoe kan ik u helpen?',
        'widget.buttonLabel': 'Hulp nodig?',
        'widget.sendButton': 'Verzenden',
        'widget.errorNetwork': 'Verbindingsfout. Probeer het opnieuw.',
        'widget.errorToken': 'Authenticatiefout.',
        'widget.errorQuota': 'Gebruikslimiet bereikt.'
    },
    'pl': {
        'widget.placeholder': 'Zadaj pytanie...',
        'widget.welcomeMessage': 'Cześć! Jak mogę Ci pomóc?',
        'widget.buttonLabel': 'Potrzebujesz pomocy?',
        'widget.sendButton': 'Wyślij',
        'widget.errorNetwork': 'Błąd połączenia. Spróbuj ponownie.',
        'widget.errorToken': 'Błąd uwierzytelniania.',
        'widget.errorQuota': 'Osiągnięto limit użycia.'
    },
    'ja': {
        'widget.placeholder': '質問を入力してください...',
        'widget.welcomeMessage': 'こんにちは！どのようにお手伝いできますか？',
        'widget.buttonLabel': 'お困りですか？',
        'widget.sendButton': '送信',
        'widget.errorNetwork': '接続エラー。もう一度お試しください。',
        'widget.errorToken': '認証エラー。',
        'widget.errorQuota': '使用制限に達しました。'
    },
    'zh': {
        'widget.placeholder': '请提问...',
        'widget.welcomeMessage': '您好！我能帮您什么？',
        'widget.buttonLabel': '需要帮助吗？',
        'widget.sendButton': '发送',
        'widget.errorNetwork': '连接错误。请重试。',
        'widget.errorToken': '认证错误。',
        'widget.errorQuota': '已达到使用限制。'
    },
    'ar': {
        'widget.placeholder': 'اطرح سؤالك...',
        'widget.welcomeMessage': 'مرحبا! كيف يمكنني مساعدتك؟',
        'widget.buttonLabel': 'هل تحتاج إلى مساعدة؟',
        'widget.sendButton': 'إرسال',
        'widget.errorNetwork': 'خطأ في الاتصال. يرجى المحاولة مرة أخرى.',
        'widget.errorToken': 'خطأ في المصادقة.',
        'widget.errorQuota': 'تم الوصول إلى حد الاستخدام.'
    },
    'hi': {
        'widget.placeholder': 'अपना प्रश्न पूछें...',
        'widget.welcomeMessage': 'नमस्ते! मैं आपकी कैसे मदद कर सकता हूं?',
        'widget.buttonLabel': 'मदद चाहिए?',
        'widget.sendButton': 'भेजें',
        'widget.errorNetwork': 'कनेक्शन त्रुटि। कृपया पुनः प्रयास करें।',
        'widget.errorToken': 'प्रमाणीकरण त्रुटि।',
        'widget.errorQuota': 'उपयोग सीमा पहुंच गई।'
    },
    'id': {
        'widget.placeholder': 'Ajukan pertanyaan Anda...',
        'widget.welcomeMessage': 'Halo! Bagaimana saya bisa membantu Anda?',
        'widget.buttonLabel': 'Butuh bantuan?',
        'widget.sendButton': 'Kirim',
        'widget.errorNetwork': 'Kesalahan koneksi. Silakan coba lagi.',
        'widget.errorToken': 'Kesalahan autentikasi.',
        'widget.errorQuota': 'Batas penggunaan tercapai.'
    },
    'th': {
        'widget.placeholder': 'ถามคำถามของคุณ...',
        'widget.welcomeMessage': 'สวัสดี! ฉันจะช่วยคุณได้อย่างไร?',
        'widget.buttonLabel': 'ต้องการความช่วยเหลือ?',
        'widget.sendButton': 'ส่ง',
        'widget.errorNetwork': 'ข้อผิดพลาดในการเชื่อมต่อ กรุณาลองอีกครั้ง',
        'widget.errorToken': 'ข้อผิดพลาดในการตรวจสอบสิทธิ์',
        'widget.errorQuota': 'ถึงขีดจำกัดการใช้งานแล้ว'
    },
    'tr': {
        'widget.placeholder': 'Sorunuzu sorun...',
        'widget.welcomeMessage': 'Merhaba! Size nasıl yardımcı olabilirim?',
        'widget.buttonLabel': 'Yardıma mı ihtiyacınız var?',
        'widget.sendButton': 'Gönder',
        'widget.errorNetwork': 'Bağlantı hatası. Lütfen tekrar deneyin.',
        'widget.errorToken': 'Kimlik doğrulama hatası.',
        'widget.errorQuota': 'Kullanım sınırına ulaşıldı.'
    },
    'vi': {
        'widget.placeholder': 'Đặt câu hỏi của bạn...',
        'widget.welcomeMessage': 'Xin chào! Tôi có thể giúp gì cho bạn?',
        'widget.buttonLabel': 'Cần giúp đỡ?',
        'widget.sendButton': 'Gửi',
        'widget.errorNetwork': 'Lỗi kết nối. Vui lòng thử lại.',
        'widget.errorToken': 'Lỗi xác thực.',
        'widget.errorQuota': 'Đã đạt giới hạn sử dụng.'
    }
}

def add_widget_translations():
    """Ajoute les traductions du widget à tous les fichiers de langue"""
    locales_dir = 'frontend/public/locales'

    for lang_code, translations in WIDGET_TRANSLATIONS.items():
        file_path = os.path.join(locales_dir, f'{lang_code}.json')

        if not os.path.exists(file_path):
            print(f"[!] Fichier non trouve: {file_path}")
            continue

        # Lire le fichier existant
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Ajouter les traductions du widget
        updated = False
        for key, value in translations.items():
            if key not in data:
                data[key] = value
                updated = True

        # Sauvegarder le fichier
        if updated:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[OK] Mis a jour: {lang_code}.json")
        else:
            print(f"[--] Deja a jour: {lang_code}.json")

if __name__ == '__main__':
    print("Ajout des traductions du widget...\n")
    add_widget_translations()
    print("\nTermine!")
