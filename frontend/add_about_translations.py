#!/usr/bin/env python3
"""
Add About page translations to all locale files
Version: 1.4.1
Last modified: 2025-10-26
"""
"""
Add About page translations to all locale files
"""

import json
from pathlib import Path

# Base directory
LOCALES_DIR = Path(__file__).parent / "public" / "locales"

# Translations for About page in all languages
ABOUT_TRANSLATIONS = {
    "de": {  # German
        "about.pageTitle": "Über Intelia Expert",
        "about.introduction": "Intelia Expert ist eine KI-gestützte Plattform, die intelligente Unterstützung und Expertenwissen in verschiedenen Bereichen bietet. Mit modernster Technologie streben wir danach, genaue, zuverlässige und hilfreiche Antworten auf Ihre Fragen zu liefern.",
        "about.companyInformation": "Unternehmensinformationen",
        "about.companyName": "Intelia Technologies Inc.",
        "about.location": "Joliette (Quebec) Kanada",
        "about.email": "E-Mail",
        "about.website": "Webseite",
        "about.thirdPartyNotices": "Hinweise Dritter",
        "about.thirdPartyIntro": "Dieses Produkt enthält Software-Komponenten von Drittanbietern, die unter verschiedenen Open-Source-Lizenzen lizenziert sind. Wir sind der Open-Source-Community für ihre Beiträge dankbar.",
        "about.openSourceLicenses": "Open-Source-Lizenzen",
        "about.licensesUsed": "Die folgenden Lizenzen werden in diesem Projekt verwendet:",
        "about.downloadFull": "Vollständige Hinweise Dritter herunterladen",
        "about.downloadDescription": "Das vollständige Dokument mit den Hinweisen Dritter enthält detaillierte Informationen über alle Software-Komponenten, ihre Lizenzen und Urheberrechtsinhaber.",
        "about.technologyStack": "Technologie-Stack",
        "about.frontend": "Frontend",
        "about.backend": "Backend",
        "about.aiml": "KI/ML",
        "about.infrastructure": "Infrastruktur",
        "about.versionInfo": "Versionsinformationen",
        "about.version": "Version",
        "about.lastUpdated": "Zuletzt aktualisiert",
        "about.license": "Lizenz",
        "about.backToHome": "Zurück zur Startseite"
    },
    "es": {  # Spanish
        "about.pageTitle": "Acerca de Intelia Expert",
        "about.introduction": "Intelia Expert es una plataforma impulsada por IA diseñada para proporcionar asistencia inteligente y conocimiento experto en varios dominios. Construida con tecnología de vanguardia, nos esforzamos por ofrecer respuestas precisas, confiables y útiles a sus preguntas.",
        "about.companyInformation": "Información de la empresa",
        "about.companyName": "Intelia Technologies Inc.",
        "about.location": "Joliette (Quebec) Canadá",
        "about.email": "Correo electrónico",
        "about.website": "Sitio web",
        "about.thirdPartyNotices": "Avisos de terceros",
        "about.thirdPartyIntro": "Este producto contiene componentes de software de terceros licenciados bajo varias licencias de código abierto. Estamos agradecidos a la comunidad de código abierto por sus contribuciones.",
        "about.openSourceLicenses": "Licencias de código abierto",
        "about.licensesUsed": "Las siguientes licencias se utilizan en este proyecto:",
        "about.downloadFull": "Descargar avisos completos de terceros",
        "about.downloadDescription": "El documento completo de avisos de terceros contiene información detallada sobre todos los componentes de software, sus licencias y titulares de derechos de autor.",
        "about.technologyStack": "Pila tecnológica",
        "about.frontend": "Frontend",
        "about.backend": "Backend",
        "about.aiml": "IA/ML",
        "about.infrastructure": "Infraestructura",
        "about.versionInfo": "Información de versión",
        "about.version": "Versión",
        "about.lastUpdated": "Última actualización",
        "about.license": "Licencia",
        "about.backToHome": "Volver al inicio"
    },
    "hi": {  # Hindi
        "about.pageTitle": "इंटेलिया एक्सपर्ट के बारे में",
        "about.introduction": "इंटेलिया एक्सपर्ट एक AI-संचालित प्लेटफ़ॉर्म है जो विभिन्न डोमेन में बुद्धिमान सहायता और विशेषज्ञ ज्ञान प्रदान करने के लिए डिज़ाइन किया गया है। अत्याधुनिक तकनीक के साथ निर्मित, हम आपके प्रश्नों के लिए सटीक, विश्वसनीय और सहायक उत्तर प्रदान करने का प्रयास करते हैं।",
        "about.companyInformation": "कंपनी की जानकारी",
        "about.companyName": "Intelia Technologies Inc.",
        "about.location": "Joliette (Quebec) Canada",
        "about.email": "ईमेल",
        "about.website": "वेबसाइट",
        "about.thirdPartyNotices": "तृतीय पक्ष सूचनाएं",
        "about.thirdPartyIntro": "इस उत्पाद में विभिन्न ओपन सोर्स लाइसेंस के तहत लाइसेंस प्राप्त तृतीय-पक्ष सॉफ़्टवेयर घटक शामिल हैं। हम उनके योगदान के लिए ओपन सोर्स समुदाय के आभारी हैं।",
        "about.openSourceLicenses": "ओपन सोर्स लाइसेंस",
        "about.licensesUsed": "इस परियोजना में निम्नलिखित लाइसेंस का उपयोग किया जाता है:",
        "about.downloadFull": "पूर्ण तृतीय पक्ष सूचनाएं डाउनलोड करें",
        "about.downloadDescription": "पूर्ण तृतीय पक्ष सूचना दस्तावेज़ में सभी सॉफ़्टवेयर घटकों, उनके लाइसेंस और कॉपीराइट धारकों के बारे में विस्तृत जानकारी शामिल है।",
        "about.technologyStack": "प्रौद्योगिकी स्टैक",
        "about.frontend": "फ्रंटएंड",
        "about.backend": "बैकएंड",
        "about.aiml": "AI/ML",
        "about.infrastructure": "इन्फ्रास्ट्रक्चर",
        "about.versionInfo": "संस्करण जानकारी",
        "about.version": "संस्करण",
        "about.lastUpdated": "अंतिम अपडेट",
        "about.license": "लाइसेंस",
        "about.backToHome": "होम पर वापस जाएं"
    },
    "id": {  # Indonesian
        "about.pageTitle": "Tentang Intelia Expert",
        "about.introduction": "Intelia Expert adalah platform bertenaga AI yang dirancang untuk memberikan bantuan cerdas dan pengetahuan ahli di berbagai domain. Dibangun dengan teknologi terdepan, kami berusaha memberikan jawaban yang akurat, andal, dan membantu untuk pertanyaan Anda.",
        "about.companyInformation": "Informasi Perusahaan",
        "about.companyName": "Intelia Technologies Inc.",
        "about.location": "Joliette (Quebec) Kanada",
        "about.email": "Email",
        "about.website": "Situs web",
        "about.thirdPartyNotices": "Pemberitahuan Pihak Ketiga",
        "about.thirdPartyIntro": "Produk ini berisi komponen perangkat lunak pihak ketiga yang dilisensikan di bawah berbagai lisensi sumber terbuka. Kami berterima kasih kepada komunitas sumber terbuka atas kontribusi mereka.",
        "about.openSourceLicenses": "Lisensi Sumber Terbuka",
        "about.licensesUsed": "Lisensi berikut digunakan dalam proyek ini:",
        "about.downloadFull": "Unduh Pemberitahuan Pihak Ketiga Lengkap",
        "about.downloadDescription": "Dokumen pemberitahuan pihak ketiga lengkap berisi informasi rinci tentang semua komponen perangkat lunak, lisensi mereka, dan pemegang hak cipta.",
        "about.technologyStack": "Tumpukan Teknologi",
        "about.frontend": "Frontend",
        "about.backend": "Backend",
        "about.aiml": "AI/ML",
        "about.infrastructure": "Infrastruktur",
        "about.versionInfo": "Informasi Versi",
        "about.version": "Versi",
        "about.lastUpdated": "Terakhir Diperbarui",
        "about.license": "Lisensi",
        "about.backToHome": "Kembali ke Beranda"
    },
    "it": {  # Italian
        "about.pageTitle": "Informazioni su Intelia Expert",
        "about.introduction": "Intelia Expert è una piattaforma basata su AI progettata per fornire assistenza intelligente e conoscenze esperte in vari domini. Costruita con tecnologia all'avanguardia, ci impegniamo a fornire risposte accurate, affidabili e utili alle tue domande.",
        "about.companyInformation": "Informazioni sull'azienda",
        "about.companyName": "Intelia Technologies Inc.",
        "about.location": "Joliette (Quebec) Canada",
        "about.email": "Email",
        "about.website": "Sito web",
        "about.thirdPartyNotices": "Avvisi di terze parti",
        "about.thirdPartyIntro": "Questo prodotto contiene componenti software di terze parti concessi in licenza con varie licenze open source. Siamo grati alla comunità open source per i loro contributi.",
        "about.openSourceLicenses": "Licenze Open Source",
        "about.licensesUsed": "Le seguenti licenze sono utilizzate in questo progetto:",
        "about.downloadFull": "Scarica gli avvisi completi di terze parti",
        "about.downloadDescription": "Il documento completo degli avvisi di terze parti contiene informazioni dettagliate su tutti i componenti software, le loro licenze e i titolari dei diritti d'autore.",
        "about.technologyStack": "Stack tecnologico",
        "about.frontend": "Frontend",
        "about.backend": "Backend",
        "about.aiml": "AI/ML",
        "about.infrastructure": "Infrastruttura",
        "about.versionInfo": "Informazioni sulla versione",
        "about.version": "Versione",
        "about.lastUpdated": "Ultimo aggiornamento",
        "about.license": "Licenza",
        "about.backToHome": "Torna alla home"
    },
    "nl": {  # Dutch
        "about.pageTitle": "Over Intelia Expert",
        "about.introduction": "Intelia Expert is een AI-aangedreven platform ontworpen om intelligente assistentie en expertkennis te bieden in verschillende domeinen. Gebouwd met geavanceerde technologie, streven we ernaar nauwkeurige, betrouwbare en nuttige antwoorden op uw vragen te geven.",
        "about.companyInformation": "Bedrijfsinformatie",
        "about.companyName": "Intelia Technologies Inc.",
        "about.location": "Joliette (Quebec) Canada",
        "about.email": "E-mail",
        "about.website": "Website",
        "about.thirdPartyNotices": "Kennisgevingen van derden",
        "about.thirdPartyIntro": "Dit product bevat softwarecomponenten van derden die onder verschillende open source-licenties zijn gelicentieerd. We zijn de open source-gemeenschap dankbaar voor hun bijdragen.",
        "about.openSourceLicenses": "Open Source-licenties",
        "about.licensesUsed": "De volgende licenties worden gebruikt in dit project:",
        "about.downloadFull": "Download volledige kennisgevingen van derden",
        "about.downloadDescription": "Het volledige document met kennisgevingen van derden bevat gedetailleerde informatie over alle softwarecomponenten, hun licenties en copyrighthouders.",
        "about.technologyStack": "Technologiestack",
        "about.frontend": "Frontend",
        "about.backend": "Backend",
        "about.aiml": "AI/ML",
        "about.infrastructure": "Infrastructuur",
        "about.versionInfo": "Versie-informatie",
        "about.version": "Versie",
        "about.lastUpdated": "Laatst bijgewerkt",
        "about.license": "Licentie",
        "about.backToHome": "Terug naar home"
    },
    "pl": {  # Polish
        "about.pageTitle": "O Intelia Expert",
        "about.introduction": "Intelia Expert to platforma oparta na sztucznej inteligencji, zaprojektowana w celu zapewnienia inteligentnej pomocy i wiedzy eksperckiej w różnych dziedzinach. Zbudowana z wykorzystaniem najnowszej technologii, dążymy do dostarczania dokładnych, wiarygodnych i pomocnych odpowiedzi na Twoje pytania.",
        "about.companyInformation": "Informacje o firmie",
        "about.companyName": "Intelia Technologies Inc.",
        "about.location": "Joliette (Quebec) Kanada",
        "about.email": "E-mail",
        "about.website": "Strona internetowa",
        "about.thirdPartyNotices": "Informacje o stronach trzecich",
        "about.thirdPartyIntro": "Ten produkt zawiera komponenty oprogramowania stron trzecich licencjonowane na podstawie różnych licencji open source. Jesteśmy wdzięczni społeczności open source za ich wkład.",
        "about.openSourceLicenses": "Licencje Open Source",
        "about.licensesUsed": "W tym projekcie używane są następujące licencje:",
        "about.downloadFull": "Pobierz pełne informacje o stronach trzecich",
        "about.downloadDescription": "Pełny dokument informacji o stronach trzecich zawiera szczegółowe informacje o wszystkich komponentach oprogramowania, ich licencjach i właścicielach praw autorskich.",
        "about.technologyStack": "Stos technologiczny",
        "about.frontend": "Frontend",
        "about.backend": "Backend",
        "about.aiml": "AI/ML",
        "about.infrastructure": "Infrastruktura",
        "about.versionInfo": "Informacje o wersji",
        "about.version": "Wersja",
        "about.lastUpdated": "Ostatnia aktualizacja",
        "about.license": "Licencja",
        "about.backToHome": "Powrót do strony głównej"
    },
    "pt": {  # Portuguese
        "about.pageTitle": "Sobre o Intelia Expert",
        "about.introduction": "Intelia Expert é uma plataforma alimentada por IA projetada para fornecer assistência inteligente e conhecimento especializado em vários domínios. Construída com tecnologia de ponta, nos esforçamos para fornecer respostas precisas, confiáveis e úteis às suas perguntas.",
        "about.companyInformation": "Informações da empresa",
        "about.companyName": "Intelia Technologies Inc.",
        "about.location": "Joliette (Quebec) Canadá",
        "about.email": "E-mail",
        "about.website": "Site",
        "about.thirdPartyNotices": "Avisos de terceiros",
        "about.thirdPartyIntro": "Este produto contém componentes de software de terceiros licenciados sob várias licenças de código aberto. Somos gratos à comunidade de código aberto por suas contribuições.",
        "about.openSourceLicenses": "Licenças de código aberto",
        "about.licensesUsed": "As seguintes licenças são usadas neste projeto:",
        "about.downloadFull": "Baixar avisos completos de terceiros",
        "about.downloadDescription": "O documento completo de avisos de terceiros contém informações detalhadas sobre todos os componentes de software, suas licenças e detentores de direitos autorais.",
        "about.technologyStack": "Pilha de tecnologia",
        "about.frontend": "Frontend",
        "about.backend": "Backend",
        "about.aiml": "IA/ML",
        "about.infrastructure": "Infraestrutura",
        "about.versionInfo": "Informações da versão",
        "about.version": "Versão",
        "about.lastUpdated": "Última atualização",
        "about.license": "Licença",
        "about.backToHome": "Voltar ao início"
    },
    "th": {  # Thai
        "about.pageTitle": "เกี่ยวกับ Intelia Expert",
        "about.introduction": "Intelia Expert เป็นแพลตฟอร์มที่ขับเคลื่อนด้วย AI ที่ออกแบบมาเพื่อให้ความช่วยเหลืออัจฉริยะและความรู้จากผู้เชี่ยวชาญในด้านต่างๆ สร้างขึ้นด้วยเทคโนโลยีล้ำสมัย เรามุ่งมั่นที่จะให้คำตอบที่ถูกต้อง เชื่อถือได้ และเป็นประโยชน์ต่อคำถามของคุณ",
        "about.companyInformation": "ข้อมูลบริษัท",
        "about.companyName": "Intelia Technologies Inc.",
        "about.location": "Joliette (Quebec) Canada",
        "about.email": "อีเมล",
        "about.website": "เว็บไซต์",
        "about.thirdPartyNotices": "ประกาศบุคคลที่สาม",
        "about.thirdPartyIntro": "ผลิตภัณฑ์นี้ประกอบด้วยส่วนประกอบซอฟต์แวร์ของบุคคลที่สามที่ได้รับอนุญาตภายใต้ใบอนุญาตโอเพนซอร์สต่างๆ เราขอขอบคุณชุมชนโอเพนซอร์สสำหรับการมีส่วนร่วมของพวกเขา",
        "about.openSourceLicenses": "ใบอนุญาตโอเพนซอร์ส",
        "about.licensesUsed": "ใบอนุญาตต่อไปนี้ใช้ในโครงการนี้:",
        "about.downloadFull": "ดาวน์โหลดประกาศบุคคลที่สามฉบับเต็ม",
        "about.downloadDescription": "เอกสารประกาศบุคคลที่สามฉบับเต็มประกอบด้วยข้อมูลโดยละเอียดเกี่ยวกับส่วนประกอบซอฟต์แวร์ทั้งหมด ใบอนุญาต และเจ้าของลิขสิทธิ์",
        "about.technologyStack": "สแต็กเทคโนโลยี",
        "about.frontend": "ฟรอนต์เอนด์",
        "about.backend": "แบ็กเอนด์",
        "about.aiml": "AI/ML",
        "about.infrastructure": "โครงสร้างพื้นฐาน",
        "about.versionInfo": "ข้อมูลเวอร์ชัน",
        "about.version": "เวอร์ชัน",
        "about.lastUpdated": "อัปเดตล่าสุด",
        "about.license": "ใบอนุญาต",
        "about.backToHome": "กลับสู่หน้าแรก"
    },
    "zh": {  # Chinese
        "about.pageTitle": "关于 Intelia Expert",
        "about.introduction": "Intelia Expert 是一个人工智能驱动的平台，旨在提供智能协助和各领域的专业知识。采用尖端技术构建，我们致力于为您的问题提供准确、可靠和有用的答案。",
        "about.companyInformation": "公司信息",
        "about.companyName": "Intelia Technologies Inc.",
        "about.location": "Joliette (Quebec) Canada",
        "about.email": "电子邮件",
        "about.website": "网站",
        "about.thirdPartyNotices": "第三方声明",
        "about.thirdPartyIntro": "本产品包含根据各种开源许可证许可的第三方软件组件。我们感谢开源社区的贡献。",
        "about.openSourceLicenses": "开源许可证",
        "about.licensesUsed": "本项目中使用了以下许可证：",
        "about.downloadFull": "下载完整的第三方声明",
        "about.downloadDescription": "完整的第三方声明文档包含有关所有软件组件、其许可证和版权持有者的详细信息。",
        "about.technologyStack": "技术栈",
        "about.frontend": "前端",
        "about.backend": "后端",
        "about.aiml": "AI/ML",
        "about.infrastructure": "基础设施",
        "about.versionInfo": "版本信息",
        "about.version": "版本",
        "about.lastUpdated": "最后更新",
        "about.license": "许可证",
        "about.backToHome": "返回首页"
    }
}


def add_translations_to_file(locale_file, translations):
    """Add About translations to a locale file"""
    print(f"Processing {locale_file.name}...")

    # Read existing translations
    with open(locale_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check if translations already exist
    if "about.pageTitle" in data:
        print(f"  Translations already exist, skipping...")
        return False

    # Add new translations
    data.update(translations)

    # Write back to file
    with open(locale_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  [OK] Translations added successfully")
    return True


def main():
    """Main function"""
    print("=" * 60)
    print("Adding About page translations to locale files")
    print("=" * 60)

    updated_count = 0

    # Process each language (skip en and fr as they're already done)
    for lang_code, translations in ABOUT_TRANSLATIONS.items():
        locale_file = LOCALES_DIR / f"{lang_code}.json"

        if not locale_file.exists():
            print(f"[WARNING] {locale_file.name} not found, skipping...")
            continue

        if add_translations_to_file(locale_file, translations):
            updated_count += 1

    print("\n" + "=" * 60)
    print(f"[OK] Updated {updated_count} locale files")
    print("=" * 60)


if __name__ == '__main__':
    main()
