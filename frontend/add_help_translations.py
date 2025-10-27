#!/usr/bin/env python3
"""
Add Help Translations
Version: 1.4.1
Last modified: 2025-10-26
"""
"""Add help tour translations to all locale files"""

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "public" / "locales"

# Traductions pour chaque langue
translations_by_lang = {
    "fr": {
        "help.buttonTitle": "Aide - Comment utiliser la plateforme",
        "help.close": "Fermer l'aide",
        "help.previous": "Précédent",
        "help.next": "Suivant",
        "help.finish": "Terminer",
        "help.inputTitle": "Zone de saisie",
        "help.inputDesc": "Posez votre question ici. Soyez précis pour obtenir des réponses pertinentes.",
        "help.sendTitle": "Bouton d'envoi",
        "help.sendDesc": "Cliquez ici ou appuyez sur Entrée pour envoyer votre question.",
        "help.newChatTitle": "Nouvelle conversation",
        "help.newChatDesc": "Créez une nouvelle conversation pour poser des questions sur un autre sujet.",
        "help.historyTitle": "Historique",
        "help.historyDesc": "Retrouvez toutes vos conversations précédentes organisées par date.",
        "help.profileTitle": "Menu utilisateur",
        "help.profileDesc": "Accédez à votre profil, paramètres, et options de compte.",
    },
    "en": {
        "help.buttonTitle": "Help - How to use the platform",
        "help.close": "Close help",
        "help.previous": "Previous",
        "help.next": "Next",
        "help.finish": "Finish",
        "help.inputTitle": "Input Field",
        "help.inputDesc": "Ask your question here. Be specific to get relevant answers.",
        "help.sendTitle": "Send Button",
        "help.sendDesc": "Click here or press Enter to send your question.",
        "help.newChatTitle": "New Conversation",
        "help.newChatDesc": "Create a new conversation to ask questions about another topic.",
        "help.historyTitle": "History",
        "help.historyDesc": "Find all your previous conversations organized by date.",
        "help.profileTitle": "User Menu",
        "help.profileDesc": "Access your profile, settings, and account options.",
    },
    "es": {
        "help.buttonTitle": "Ayuda - Cómo usar la plataforma",
        "help.close": "Cerrar ayuda",
        "help.previous": "Anterior",
        "help.next": "Siguiente",
        "help.finish": "Finalizar",
        "help.inputTitle": "Campo de entrada",
        "help.inputDesc": "Haga su pregunta aquí. Sea específico para obtener respuestas relevantes.",
        "help.sendTitle": "Botón de envío",
        "help.sendDesc": "Haga clic aquí o presione Enter para enviar su pregunta.",
        "help.newChatTitle": "Nueva conversación",
        "help.newChatDesc": "Cree una nueva conversación para hacer preguntas sobre otro tema.",
        "help.historyTitle": "Historial",
        "help.historyDesc": "Encuentre todas sus conversaciones anteriores organizadas por fecha.",
        "help.profileTitle": "Menú de usuario",
        "help.profileDesc": "Acceda a su perfil, configuración y opciones de cuenta.",
    },
    "de": {
        "help.buttonTitle": "Hilfe - So verwenden Sie die Plattform",
        "help.close": "Hilfe schließen",
        "help.previous": "Zurück",
        "help.next": "Weiter",
        "help.finish": "Beenden",
        "help.inputTitle": "Eingabefeld",
        "help.inputDesc": "Stellen Sie hier Ihre Frage. Seien Sie spezifisch, um relevante Antworten zu erhalten.",
        "help.sendTitle": "Senden-Schaltfläche",
        "help.sendDesc": "Klicken Sie hier oder drücken Sie Enter, um Ihre Frage zu senden.",
        "help.newChatTitle": "Neues Gespräch",
        "help.newChatDesc": "Erstellen Sie ein neues Gespräch, um Fragen zu einem anderen Thema zu stellen.",
        "help.historyTitle": "Verlauf",
        "help.historyDesc": "Finden Sie alle Ihre früheren Gespräche nach Datum sortiert.",
        "help.profileTitle": "Benutzermenü",
        "help.profileDesc": "Greifen Sie auf Ihr Profil, Einstellungen und Kontooptionen zu.",
    },
    "it": {
        "help.buttonTitle": "Aiuto - Come utilizzare la piattaforma",
        "help.close": "Chiudi aiuto",
        "help.previous": "Precedente",
        "help.next": "Successivo",
        "help.finish": "Fine",
        "help.inputTitle": "Campo di input",
        "help.inputDesc": "Fai la tua domanda qui. Sii specifico per ottenere risposte pertinenti.",
        "help.sendTitle": "Pulsante di invio",
        "help.sendDesc": "Clicca qui o premi Invio per inviare la tua domanda.",
        "help.newChatTitle": "Nuova conversazione",
        "help.newChatDesc": "Crea una nuova conversazione per fare domande su un altro argomento.",
        "help.historyTitle": "Cronologia",
        "help.historyDesc": "Trova tutte le tue conversazioni precedenti organizzate per data.",
        "help.profileTitle": "Menu utente",
        "help.profileDesc": "Accedi al tuo profilo, impostazioni e opzioni dell'account.",
    },
    "pt": {
        "help.buttonTitle": "Ajuda - Como usar a plataforma",
        "help.close": "Fechar ajuda",
        "help.previous": "Anterior",
        "help.next": "Próximo",
        "help.finish": "Concluir",
        "help.inputTitle": "Campo de entrada",
        "help.inputDesc": "Faça sua pergunta aqui. Seja específico para obter respostas relevantes.",
        "help.sendTitle": "Botão de envio",
        "help.sendDesc": "Clique aqui ou pressione Enter para enviar sua pergunta.",
        "help.newChatTitle": "Nova conversa",
        "help.newChatDesc": "Crie uma nova conversa para fazer perguntas sobre outro assunto.",
        "help.historyTitle": "Histórico",
        "help.historyDesc": "Encontre todas as suas conversas anteriores organizadas por data.",
        "help.profileTitle": "Menu do usuário",
        "help.profileDesc": "Acesse seu perfil, configurações e opções de conta.",
    },
    "nl": {
        "help.buttonTitle": "Help - Hoe de platform te gebruiken",
        "help.close": "Help sluiten",
        "help.previous": "Vorige",
        "help.next": "Volgende",
        "help.finish": "Voltooien",
        "help.inputTitle": "Invoerveld",
        "help.inputDesc": "Stel hier uw vraag. Wees specifiek om relevante antwoorden te krijgen.",
        "help.sendTitle": "Verstuur knop",
        "help.sendDesc": "Klik hier of druk op Enter om uw vraag te versturen.",
        "help.newChatTitle": "Nieuw gesprek",
        "help.newChatDesc": "Maak een nieuw gesprek aan om vragen te stellen over een ander onderwerp.",
        "help.historyTitle": "Geschiedenis",
        "help.historyDesc": "Vind al uw eerdere gesprekken georganiseerd op datum.",
        "help.profileTitle": "Gebruikersmenu",
        "help.profileDesc": "Toegang tot uw profiel, instellingen en account opties.",
    },
    "pl": {
        "help.buttonTitle": "Pomoc - Jak korzystać z platformy",
        "help.close": "Zamknij pomoc",
        "help.previous": "Poprzedni",
        "help.next": "Następny",
        "help.finish": "Zakończ",
        "help.inputTitle": "Pole wejściowe",
        "help.inputDesc": "Zadaj tutaj swoje pytanie. Bądź konkretny, aby uzyskać odpowiednie odpowiedzi.",
        "help.sendTitle": "Przycisk wysyłania",
        "help.sendDesc": "Kliknij tutaj lub naciśnij Enter, aby wysłać swoje pytanie.",
        "help.newChatTitle": "Nowa rozmowa",
        "help.newChatDesc": "Utwórz nową rozmowę, aby zadać pytania na inny temat.",
        "help.historyTitle": "Historia",
        "help.historyDesc": "Znajdź wszystkie swoje poprzednie rozmowy uporządkowane według daty.",
        "help.profileTitle": "Menu użytkownika",
        "help.profileDesc": "Uzyskaj dostęp do swojego profilu, ustawień i opcji konta.",
    },
    "zh": {
        "help.buttonTitle": "帮助 - 如何使用平台",
        "help.close": "关闭帮助",
        "help.previous": "上一步",
        "help.next": "下一步",
        "help.finish": "完成",
        "help.inputTitle": "输入框",
        "help.inputDesc": "在这里提出您的问题。具体一点以获得相关答案。",
        "help.sendTitle": "发送按钮",
        "help.sendDesc": "点击这里或按Enter键发送您的问题。",
        "help.newChatTitle": "新对话",
        "help.newChatDesc": "创建新对话以提问其他主题的问题。",
        "help.historyTitle": "历史记录",
        "help.historyDesc": "查找按日期组织的所有以前的对话。",
        "help.profileTitle": "用户菜单",
        "help.profileDesc": "访问您的个人资料、设置和账户选项。",
    },
    "hi": {
        "help.buttonTitle": "सहायता - प्लेटफ़ॉर्म का उपयोग कैसे करें",
        "help.close": "सहायता बंद करें",
        "help.previous": "पिछला",
        "help.next": "अगला",
        "help.finish": "समाप्त करें",
        "help.inputTitle": "इनपुट फ़ील्ड",
        "help.inputDesc": "यहाँ अपना प्रश्न पूछें। प्रासंगिक उत्तर प्राप्त करने के लिए विशिष्ट रहें।",
        "help.sendTitle": "भेजें बटन",
        "help.sendDesc": "अपना प्रश्न भेजने के लिए यहाँ क्लिक करें या Enter दबाएं।",
        "help.newChatTitle": "नई बातचीत",
        "help.newChatDesc": "किसी अन्य विषय पर प्रश्न पूछने के लिए एक नई बातचीत बनाएं।",
        "help.historyTitle": "इतिहास",
        "help.historyDesc": "दिनांक के अनुसार व्यवस्थित अपनी सभी पिछली बातचीत ढूंढें।",
        "help.profileTitle": "उपयोगकर्ता मेनू",
        "help.profileDesc": "अपनी प्रोफ़ाइल, सेटिंग्स और खाता विकल्पों तक पहुंचें।",
    },
    "id": {
        "help.buttonTitle": "Bantuan - Cara menggunakan platform",
        "help.close": "Tutup bantuan",
        "help.previous": "Sebelumnya",
        "help.next": "Berikutnya",
        "help.finish": "Selesai",
        "help.inputTitle": "Bidang input",
        "help.inputDesc": "Ajukan pertanyaan Anda di sini. Jadilah spesifik untuk mendapatkan jawaban yang relevan.",
        "help.sendTitle": "Tombol kirim",
        "help.sendDesc": "Klik di sini atau tekan Enter untuk mengirim pertanyaan Anda.",
        "help.newChatTitle": "Percakapan baru",
        "help.newChatDesc": "Buat percakapan baru untuk mengajukan pertanyaan tentang topik lain.",
        "help.historyTitle": "Riwayat",
        "help.historyDesc": "Temukan semua percakapan sebelumnya Anda yang diorganisir berdasarkan tanggal.",
        "help.profileTitle": "Menu pengguna",
        "help.profileDesc": "Akses profil, pengaturan, dan opsi akun Anda.",
    },
    "th": {
        "help.buttonTitle": "ความช่วยเหลือ - วิธีใช้แพลตฟอร์ม",
        "help.close": "ปิดความช่วยเหลือ",
        "help.previous": "ก่อนหน้า",
        "help.next": "ถัดไป",
        "help.finish": "เสร็จสิ้น",
        "help.inputTitle": "ช่องป้อนข้อมูล",
        "help.inputDesc": "ถามคำถามของคุณที่นี่ ระบุให้ชัดเจนเพื่อรับคำตอบที่เกี่ยวข้อง",
        "help.sendTitle": "ปุ่มส่ง",
        "help.sendDesc": "คลิกที่นี่หรือกด Enter เพื่อส่งคำถามของคุณ",
        "help.newChatTitle": "การสนทนาใหม่",
        "help.newChatDesc": "สร้างการสนทนาใหม่เพื่อถามคำถามเกี่ยวกับหัวข้ออื่น",
        "help.historyTitle": "ประวัติ",
        "help.historyDesc": "ค้นหาการสนทนาก่อนหน้านี้ทั้งหมดของคุณที่จัดระเบียบตามวันที่",
        "help.profileTitle": "เมนูผู้ใช้",
        "help.profileDesc": "เข้าถึงโปรไฟล์ การตั้งค่า และตัวเลือกบัญชีของคุณ",
    },
}

def add_translations():
    for lang_code, translations in translations_by_lang.items():
        locale_file = LOCALES_DIR / f"{lang_code}.json"

        if not locale_file.exists():
            print(f"[SKIP] {lang_code}.json not found")
            continue

        # Lire le fichier existant
        with open(locale_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Ajouter les nouvelles traductions
        added_count = 0
        for key, value in translations.items():
            if key not in data:
                data[key] = value
                added_count += 1
                print(f"  [ADD] {key}")

        if added_count > 0:
            # Sauvegarder avec les nouvelles traductions
            with open(locale_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[OK] {locale_file.name}: {added_count} translations added\n")
        else:
            print(f"[SKIP] {locale_file.name}: all translations already present\n")

if __name__ == "__main__":
    print("=" * 70)
    print("Adding Help Tour translations to all locales")
    print("=" * 70)
    print()

    add_translations()

    print("=" * 70)
    print("DONE")
    print("=" * 70)
