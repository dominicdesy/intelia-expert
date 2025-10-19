# app/services/email_service.py
"""
Service d'envoi d'emails multilingues pour l'authentification Supabase
Version 1.0 - Support des webhooks Supabase Auth
"""

import os
import logging
from typing import Dict, Any, Optional
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.utils.gdpr_helpers import mask_email

logger = logging.getLogger(__name__)


class EmailType(Enum):
    """Types d'emails d'authentification"""
    SIGNUP_CONFIRMATION = "signup"
    PASSWORD_RESET = "recovery"
    EMAIL_CHANGE = "email_change"
    INVITE_USER = "invite"
    REAUTHENTICATION = "reauthentication"


class EmailLanguage(Enum):
    """Langues supportées"""
    FR = "fr"
    EN = "en"
    ES = "es"
    DE = "de"
    ZH = "zh"
    TH = "th"
    PT = "pt"
    RU = "ru"
    HI = "hi"
    ID = "id"
    IT = "it"
    NL = "nl"
    PL = "pl"


# Mapping des langues vers leur nom natif
LANGUAGE_NAMES = {
    EmailLanguage.FR: "Français",
    EmailLanguage.EN: "English",
    EmailLanguage.ES: "Español",
    EmailLanguage.DE: "Deutsch",
    EmailLanguage.ZH: "中文",
    EmailLanguage.TH: "ไทย",
    EmailLanguage.PT: "Português",
    EmailLanguage.RU: "Русский",
    EmailLanguage.HI: "हिन्दी",
    EmailLanguage.ID: "Bahasa Indonesia",
    EmailLanguage.IT: "Italiano",
    EmailLanguage.NL: "Nederlands",
    EmailLanguage.PL: "Polski",
}


class EmailTemplates:
    """Templates HTML pour les emails multilingues"""

    @staticmethod
    def get_base_template(
        primary_content: str,
        fallback_content: str,
        primary_lang: EmailLanguage,
    ) -> str:
        """Template de base bilingue (langue principale + anglais)"""
        primary_lang_name = LANGUAGE_NAMES.get(primary_lang, "")

        return f"""<!doctype html>
<html lang="{primary_lang.value}" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="x-apple-disable-message-reformatting" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Intelia Expert</title>
</head>
<body style="margin:0;padding:0;background:#f6f7f9;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f7f9;">
    <tr>
      <td align="center" style="padding:24px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid #e6e8eb;">
          <tr>
            <td style="padding:24px 24px 0 24px;">
              <div style="font-family:Segoe UI,Arial,Helvetica,sans-serif;font-size:14px;color:#111827;line-height:1.45;">
                <div style="font-size:18px;font-weight:700;margin-bottom:8px;">Intelia Technologies</div>
                <div style="font-size:12px;color:#6b7280;">Intelia Expert</div>
              </div>
            </td>
          </tr>

          <!-- Contenu principal (langue préférée) -->
          <tr>
            <td style="padding:24px;">
              {primary_content}
            </td>
          </tr>

          <!-- Divider -->
          <tr>
            <td style="padding:0 24px;">
              <hr style="border:none;border-top:1px solid #e6e8eb;margin:0;" />
            </td>
          </tr>

          <!-- Contenu en anglais (fallback) -->
          <tr>
            <td style="padding:16px 24px 24px 24px;">
              <div style="font-family:Segoe UI,Arial,Helvetica,sans-serif;color:#111827;line-height:1.6;">
                <h3 style="margin:0 0 8px 0;font-size:14px;color:#374151;">English version</h3>
                {fallback_content}
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:16px 24px 24px 24px;background:#f9fafb;border-top:1px solid #e6e8eb;">
              <div style="font-family:Segoe UI,Arial,Helvetica,sans-serif;color:#6b7280;font-size:12px;line-height:1.5;">
                Cordialement / Best regards,<br/>
                <strong>Intelia Technologies</strong><br/>
                <a href="https://expert.intelia.com/" style="color:#6b7280;text-decoration:none;">expert.intelia.com</a>
              </div>
            </td>
          </tr>
        </table>

        <div style="font-family:Segoe UI,Arial,Helvetica,sans-serif;font-size:11px;color:#9ca3af;margin-top:12px;">
          {primary_lang_name} | English
        </div>
      </td>
    </tr>
  </table>
</body>
</html>"""

    @staticmethod
    def get_translations() -> Dict[EmailLanguage, Dict[str, str]]:
        """Dictionnaire de traductions pour tous les textes"""
        return {
            EmailLanguage.FR: {
                "signup_title": "Confirmez votre inscription",
                "signup_greeting": "Bonjour",
                "signup_body": "Merci d'avoir créé un compte. Pour sécuriser votre accès, veuillez confirmer votre adresse courriel.",
                "signup_button": "Confirmer mon adresse",
                "signup_otp_intro": "Ou entrez ce code à usage unique (OTP) :",
                "signup_security": "Pour votre sécurité, ce lien/code n'est valide que pendant une courte période.",
                "signup_ignore": "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message.",
                "reset_title": "Réinitialisez votre mot de passe",
                "reset_body": "Nous avons reçu une demande de réinitialisation du mot de passe de votre compte Intelia Expert.",
                "reset_button": "Réinitialiser mon mot de passe",
                "invite_title": "Vous avez été invité(e)",
                "invite_body": "Vous avez été invité(e) à créer un compte sur Intelia Expert",
                "invite_by": "par",
                "invite_button": "Accepter l'invitation",
                "email_change_title": "Confirmez le changement d'adresse",
                "email_change_body": "Vous avez demandé de mettre à jour votre adresse courriel pour votre compte Intelia Expert.",
                "email_change_button": "Confirmer le changement",
                "reauth_title": "Confirmez votre identité",
                "reauth_body": "Pour continuer, veuillez entrer le code de vérification ci-dessous.",
                "link_fallback": "Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :",
            },
            EmailLanguage.EN: {
                "signup_title": "Confirm your signup",
                "signup_greeting": "Hello",
                "signup_body": "Thank you for creating an account. To secure your access, please confirm your email address.",
                "signup_button": "Confirm my email",
                "signup_otp_intro": "Or enter this one-time code (OTP):",
                "signup_security": "For your security, this link/code is only valid for a short period.",
                "signup_ignore": "If you did not request this, please ignore this message.",
                "reset_title": "Reset your password",
                "reset_body": "We received a request to reset the password for your Intelia Expert account.",
                "reset_button": "Reset my password",
                "invite_title": "You've been invited",
                "invite_body": "You've been invited to create an account at Intelia Expert",
                "invite_by": "by",
                "invite_button": "Accept the invitation",
                "email_change_title": "Confirm email change",
                "email_change_body": "You requested to update the email address for your Intelia Expert account.",
                "email_change_button": "Confirm the change",
                "reauth_title": "Confirm your identity",
                "reauth_body": "To continue, please enter the verification code below.",
                "link_fallback": "If the button doesn't work, copy this link to your browser:",
            },
            EmailLanguage.TH: {
                "signup_title": "ยืนยันการสมัครของคุณ",
                "signup_greeting": "สวัสดี",
                "signup_body": "ขอบคุณที่สร้างบัญชี เพื่อความปลอดภัย โปรดยืนยันที่อยู่อีเมลของคุณ",
                "signup_button": "ยืนยันอีเมลของฉัน",
                "signup_otp_intro": "หรือป้อนรหัสใช้ครั้งเดียว (OTP) นี้:",
                "signup_security": "เพื่อความปลอดภัยของคุณ ลิงก์/รหัสนี้มีผลเพียงระยะเวลาสั้นๆ",
                "signup_ignore": "หากคุณไม่ได้ร้องขอสิ่งนี้ โปรดเพิกเฉยข้อความนี้",
                "reset_title": "รีเซ็ตรหัสผ่านของคุณ",
                "reset_body": "เราได้รับคำขอรีเซ็ตรหัสผ่านสำหรับบัญชี Intelia Expert ของคุณ",
                "reset_button": "รีเซ็ตรหัสผ่านของฉัน",
                "invite_title": "คุณได้รับเชิญ",
                "invite_body": "คุณได้รับเชิญให้สร้างบัญชีที่ Intelia Expert",
                "invite_by": "โดย",
                "invite_button": "ยอมรับคำเชิญ",
                "email_change_title": "ยืนยันการเปลี่ยนอีเมล",
                "email_change_body": "คุณขอเปลี่ยนที่อยู่อีเมลสำหรับบัญชี Intelia Expert ของคุณ",
                "email_change_button": "ยืนยันการเปลี่ยนแปลง",
                "reauth_title": "ยืนยันตัวตนของคุณ",
                "reauth_body": "เพื่อดำเนินการต่อ โปรดป้อนรหัสยืนยันด้านล่าง",
                "link_fallback": "หากปุ่มไม่ทำงาน ให้คัดลอกลิงก์นี้ไปยังเบราว์เซอร์ของคุณ:",
            },
            EmailLanguage.ES: {
                "signup_title": "Confirma tu registro",
                "signup_greeting": "Hola",
                "signup_body": "Gracias por crear una cuenta. Para asegurar tu acceso, por favor confirma tu dirección de correo electrónico.",
                "signup_button": "Confirmar mi correo",
                "signup_otp_intro": "O ingresa este código de un solo uso (OTP):",
                "signup_security": "Por tu seguridad, este enlace/código solo es válido por un corto período.",
                "signup_ignore": "Si no solicitaste esto, por favor ignora este mensaje.",
                "reset_title": "Restablece tu contraseña",
                "reset_body": "Recibimos una solicitud para restablecer la contraseña de tu cuenta de Intelia Expert.",
                "reset_button": "Restablecer mi contraseña",
                "invite_title": "Has sido invitado",
                "invite_body": "Has sido invitado a crear una cuenta en Intelia Expert",
                "invite_by": "por",
                "invite_button": "Aceptar la invitación",
                "email_change_title": "Confirmar cambio de correo",
                "email_change_body": "Solicitaste actualizar la dirección de correo electrónico de tu cuenta de Intelia Expert.",
                "email_change_button": "Confirmar el cambio",
                "reauth_title": "Confirma tu identidad",
                "reauth_body": "Para continuar, por favor ingresa el código de verificación a continuación.",
                "link_fallback": "Si el botón no funciona, copia este enlace en tu navegador:",
            },
            EmailLanguage.DE: {
                "signup_title": "Bestätigen Sie Ihre Anmeldung",
                "signup_greeting": "Hallo",
                "signup_body": "Vielen Dank für die Erstellung eines Kontos. Um Ihren Zugang zu sichern, bestätigen Sie bitte Ihre E-Mail-Adresse.",
                "signup_button": "Meine E-Mail bestätigen",
                "signup_otp_intro": "Oder geben Sie diesen Einmalcode (OTP) ein:",
                "signup_security": "Zu Ihrer Sicherheit ist dieser Link/Code nur für kurze Zeit gültig.",
                "signup_ignore": "Wenn Sie dies nicht angefordert haben, ignorieren Sie bitte diese Nachricht.",
                "reset_title": "Setzen Sie Ihr Passwort zurück",
                "reset_body": "Wir haben eine Anfrage zum Zurücksetzen des Passworts für Ihr Intelia Expert-Konto erhalten.",
                "reset_button": "Mein Passwort zurücksetzen",
                "invite_title": "Sie wurden eingeladen",
                "invite_body": "Sie wurden eingeladen, ein Konto bei Intelia Expert zu erstellen",
                "invite_by": "von",
                "invite_button": "Einladung annehmen",
                "email_change_title": "E-Mail-Änderung bestätigen",
                "email_change_body": "Sie haben beantragt, die E-Mail-Adresse für Ihr Intelia Expert-Konto zu aktualisieren.",
                "email_change_button": "Änderung bestätigen",
                "reauth_title": "Bestätigen Sie Ihre Identität",
                "reauth_body": "Um fortzufahren, geben Sie bitte den unten stehenden Bestätigungscode ein.",
                "link_fallback": "Wenn die Schaltfläche nicht funktioniert, kopieren Sie diesen Link in Ihren Browser:",
            },
            EmailLanguage.ZH: {
                "signup_title": "确认您的注册",
                "signup_greeting": "您好",
                "signup_body": "感谢您创建帐户。为了保护您的访问权限，请确认您的电子邮件地址。",
                "signup_button": "确认我的电子邮件",
                "signup_otp_intro": "或输入此一次性代码（OTP）：",
                "signup_security": "为了您的安全，此链接/代码仅在短时间内有效。",
                "signup_ignore": "如果您未请求此操作，请忽略此消息。",
                "reset_title": "重置您的密码",
                "reset_body": "我们收到了重置您的 Intelia Expert 帐户密码的请求。",
                "reset_button": "重置我的密码",
                "invite_title": "您已被邀请",
                "invite_body": "您已被邀请在 Intelia Expert 创建帐户",
                "invite_by": "由",
                "invite_button": "接受邀请",
                "email_change_title": "确认电子邮件更改",
                "email_change_body": "您请求更新您的 Intelia Expert 帐户的电子邮件地址。",
                "email_change_button": "确认更改",
                "reauth_title": "确认您的身份",
                "reauth_body": "要继续，请在下方输入验证码。",
                "link_fallback": "如果按钮不起作用，请将此链接复制到您的浏览器：",
            },
            EmailLanguage.PT: {
                "signup_title": "Confirme seu cadastro",
                "signup_greeting": "Olá",
                "signup_body": "Obrigado por criar uma conta. Para proteger seu acesso, confirme seu endereço de e-mail.",
                "signup_button": "Confirmar meu e-mail",
                "signup_otp_intro": "Ou insira este código de uso único (OTP):",
                "signup_security": "Para sua segurança, este link/código é válido apenas por um curto período.",
                "signup_ignore": "Se você não solicitou isso, ignore esta mensagem.",
                "reset_title": "Redefina sua senha",
                "reset_body": "Recebemos uma solicitação para redefinir a senha da sua conta Intelia Expert.",
                "reset_button": "Redefinir minha senha",
                "invite_title": "Você foi convidado",
                "invite_body": "Você foi convidado para criar uma conta no Intelia Expert",
                "invite_by": "por",
                "invite_button": "Aceitar o convite",
                "email_change_title": "Confirmar mudança de e-mail",
                "email_change_body": "Você solicitou atualizar o endereço de e-mail da sua conta Intelia Expert.",
                "email_change_button": "Confirmar a mudança",
                "reauth_title": "Confirme sua identidade",
                "reauth_body": "Para continuar, insira o código de verificação abaixo.",
                "link_fallback": "Se o botão não funcionar, copie este link para o seu navegador:",
            },
            EmailLanguage.RU: {
                "signup_title": "Подтвердите регистрацию",
                "signup_greeting": "Здравствуйте",
                "signup_body": "Спасибо за создание учетной записи. Чтобы защитить доступ, подтвердите свой адрес электронной почты.",
                "signup_button": "Подтвердить мой адрес",
                "signup_otp_intro": "Или введите этот одноразовый код (OTP):",
                "signup_security": "В целях безопасности эта ссылка/код действителен только в течение короткого периода.",
                "signup_ignore": "Если вы не запрашивали это, проигнорируйте это сообщение.",
                "reset_title": "Сбросьте пароль",
                "reset_body": "Мы получили запрос на сброс пароля для вашей учетной записи Intelia Expert.",
                "reset_button": "Сбросить мой пароль",
                "invite_title": "Вы приглашены",
                "invite_body": "Вас пригласили создать учетную запись в Intelia Expert",
                "invite_by": "от",
                "invite_button": "Принять приглашение",
                "email_change_title": "Подтвердить изменение адреса",
                "email_change_body": "Вы запросили обновление адреса электронной почты для вашей учетной записи Intelia Expert.",
                "email_change_button": "Подтвердить изменение",
                "reauth_title": "Подтвердите свою личность",
                "reauth_body": "Чтобы продолжить, введите проверочный код ниже.",
                "link_fallback": "Если кнопка не работает, скопируйте эту ссылку в браузер:",
            },
            EmailLanguage.HI: {
                "signup_title": "अपने साइनअप की पुष्टि करें",
                "signup_greeting": "नमस्ते",
                "signup_body": "खाता बनाने के लिए धन्यवाद। अपनी पहुंच सुरक्षित करने के लिए, कृपया अपना ईमेल पता पुष्टि करें।",
                "signup_button": "मेरा ईमेल पुष्टि करें",
                "signup_otp_intro": "या यह वन-टाइम कोड (OTP) दर्ज करें:",
                "signup_security": "आपकी सुरक्षा के लिए, यह लिंक/कोड केवल थोड़े समय के लिए मान्य है।",
                "signup_ignore": "यदि आपने इसका अनुरोध नहीं किया है, तो कृपया इस संदेश को अनदेखा करें।",
                "reset_title": "अपना पासवर्ड रीसेट करें",
                "reset_body": "हमें आपके Intelia Expert खाते के लिए पासवर्ड रीसेट करने का अनुरोध प्राप्त हुआ है।",
                "reset_button": "मेरा पासवर्ड रीसेट करें",
                "invite_title": "आपको आमंत्रित किया गया है",
                "invite_body": "आपको Intelia Expert पर खाता बनाने के लिए आमंत्रित किया गया है",
                "invite_by": "द्वारा",
                "invite_button": "निमंत्रण स्वीकार करें",
                "email_change_title": "ईमेल परिवर्तन की पुष्टि करें",
                "email_change_body": "आपने अपने Intelia Expert खाते के लिए ईमेल पता अपडेट करने का अनुरोध किया है।",
                "email_change_button": "परिवर्तन की पुष्टि करें",
                "reauth_title": "अपनी पहचान की पुष्टि करें",
                "reauth_body": "जारी रखने के लिए, कृपया नीचे सत्यापन कोड दर्ज करें।",
                "link_fallback": "यदि बटन काम नहीं करता है, तो इस लिंक को अपने ब्राउज़र में कॉपी करें:",
            },
            EmailLanguage.ID: {
                "signup_title": "Konfirmasi pendaftaran Anda",
                "signup_greeting": "Halo",
                "signup_body": "Terima kasih telah membuat akun. Untuk mengamankan akses Anda, silakan konfirmasi alamat email Anda.",
                "signup_button": "Konfirmasi email saya",
                "signup_otp_intro": "Atau masukkan kode satu kali (OTP) ini:",
                "signup_security": "Untuk keamanan Anda, tautan/kode ini hanya berlaku untuk waktu singkat.",
                "signup_ignore": "Jika Anda tidak meminta ini, silakan abaikan pesan ini.",
                "reset_title": "Setel ulang kata sandi Anda",
                "reset_body": "Kami menerima permintaan untuk mengatur ulang kata sandi untuk akun Intelia Expert Anda.",
                "reset_button": "Setel ulang kata sandi saya",
                "invite_title": "Anda telah diundang",
                "invite_body": "Anda telah diundang untuk membuat akun di Intelia Expert",
                "invite_by": "oleh",
                "invite_button": "Terima undangan",
                "email_change_title": "Konfirmasi perubahan email",
                "email_change_body": "Anda meminta untuk memperbarui alamat email untuk akun Intelia Expert Anda.",
                "email_change_button": "Konfirmasi perubahan",
                "reauth_title": "Konfirmasi identitas Anda",
                "reauth_body": "Untuk melanjutkan, silakan masukkan kode verifikasi di bawah ini.",
                "link_fallback": "Jika tombol tidak berfungsi, salin tautan ini ke browser Anda:",
            },
            EmailLanguage.IT: {
                "signup_title": "Conferma la tua iscrizione",
                "signup_greeting": "Ciao",
                "signup_body": "Grazie per aver creato un account. Per proteggere il tuo accesso, conferma il tuo indirizzo email.",
                "signup_button": "Conferma la mia email",
                "signup_otp_intro": "Oppure inserisci questo codice monouso (OTP):",
                "signup_security": "Per la tua sicurezza, questo link/codice è valido solo per un breve periodo.",
                "signup_ignore": "Se non hai richiesto ciò, ignora questo messaggio.",
                "reset_title": "Reimposta la tua password",
                "reset_body": "Abbiamo ricevuto una richiesta per reimpostare la password del tuo account Intelia Expert.",
                "reset_button": "Reimposta la mia password",
                "invite_title": "Sei stato invitato",
                "invite_body": "Sei stato invitato a creare un account su Intelia Expert",
                "invite_by": "da",
                "invite_button": "Accetta l'invito",
                "email_change_title": "Conferma modifica email",
                "email_change_body": "Hai richiesto di aggiornare l'indirizzo email per il tuo account Intelia Expert.",
                "email_change_button": "Conferma la modifica",
                "reauth_title": "Conferma la tua identità",
                "reauth_body": "Per continuare, inserisci il codice di verifica qui sotto.",
                "link_fallback": "Se il pulsante non funziona, copia questo link nel tuo browser:",
            },
            EmailLanguage.NL: {
                "signup_title": "Bevestig je aanmelding",
                "signup_greeting": "Hallo",
                "signup_body": "Bedankt voor het aanmaken van een account. Om je toegang te beveiligen, bevestig je e-mailadres.",
                "signup_button": "Bevestig mijn e-mail",
                "signup_otp_intro": "Of voer deze eenmalige code (OTP) in:",
                "signup_security": "Voor je veiligheid is deze link/code slechts voor korte tijd geldig.",
                "signup_ignore": "Als je dit niet hebt aangevraagd, negeer dan dit bericht.",
                "reset_title": "Stel je wachtwoord opnieuw in",
                "reset_body": "We hebben een verzoek ontvangen om het wachtwoord voor je Intelia Expert account opnieuw in te stellen.",
                "reset_button": "Mijn wachtwoord opnieuw instellen",
                "invite_title": "Je bent uitgenodigd",
                "invite_body": "Je bent uitgenodigd om een account aan te maken bij Intelia Expert",
                "invite_by": "door",
                "invite_button": "Accepteer de uitnodiging",
                "email_change_title": "Bevestig e-mailwijziging",
                "email_change_body": "Je hebt verzocht om het e-mailadres voor je Intelia Expert account bij te werken.",
                "email_change_button": "Bevestig de wijziging",
                "reauth_title": "Bevestig je identiteit",
                "reauth_body": "Om door te gaan, voer hieronder de verificatiecode in.",
                "link_fallback": "Als de knop niet werkt, kopieer deze link naar je browser:",
            },
            EmailLanguage.PL: {
                "signup_title": "Potwierdź swoją rejestrację",
                "signup_greeting": "Cześć",
                "signup_body": "Dziękujemy za utworzenie konta. Aby zabezpieczyć dostęp, potwierdź swój adres e-mail.",
                "signup_button": "Potwierdź mój e-mail",
                "signup_otp_intro": "Lub wprowadź ten jednorazowy kod (OTP):",
                "signup_security": "Dla twojego bezpieczeństwa ten link/kod jest ważny tylko przez krótki czas.",
                "signup_ignore": "Jeśli nie prosiłeś o to, zignoruj tę wiadomość.",
                "reset_title": "Zresetuj swoje hasło",
                "reset_body": "Otrzymaliśmy prośbę o zresetowanie hasła dla twojego konta Intelia Expert.",
                "reset_button": "Zresetuj moje hasło",
                "invite_title": "Zostałeś zaproszony",
                "invite_body": "Zostałeś zaproszony do utworzenia konta w Intelia Expert",
                "invite_by": "przez",
                "invite_button": "Zaakceptuj zaproszenie",
                "email_change_title": "Potwierdź zmianę e-maila",
                "email_change_body": "Poprosiłeś o aktualizację adresu e-mail dla twojego konta Intelia Expert.",
                "email_change_button": "Potwierdź zmianę",
                "reauth_title": "Potwierdź swoją tożsamość",
                "reauth_body": "Aby kontynuować, wprowadź poniżej kod weryfikacyjny.",
                "link_fallback": "Jeśli przycisk nie działa, skopiuj ten link do przeglądarki:",
            },
        }

    @staticmethod
    def generate_signup_email(
        lang: EmailLanguage,
        user_email: str,
        first_name: Optional[str],
        confirmation_url: str,
        otp_token: str,
    ) -> tuple[str, str]:
        """Génère le HTML pour l'email de confirmation d'inscription"""
        translations = EmailTemplates.get_translations()
        t = translations.get(lang, translations[EmailLanguage.EN])
        t_en = translations[EmailLanguage.EN]

        greeting = f"{t['signup_greeting']}{' ' + first_name if first_name else ''}"

        # Contenu principal (langue préférée)
        primary_content = f"""
        <div style="font-family:Segoe UI,Arial,Helvetica,sans-serif;color:#111827;line-height:1.6;">
          <h2 style="margin:0 0 12px 0;font-size:20px;">{t['signup_title']}</h2>
          <p style="margin:0 0 12px 0;font-size:14px;">{greeting},</p>
          <p style="margin:0 0 16px 0;font-size:14px;">{t['signup_body']}</p>

          <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 16px 0;">
            <tr>
              <td align="center" bgcolor="#0ea5e9" style="border-radius:8px;">
                <a href="{confirmation_url}"
                   style="display:inline-block;padding:12px 18px;font-family:Segoe UI,Arial,Helvetica,sans-serif;
                          font-size:14px;font-weight:600;color:#ffffff;text-decoration:none;">
                  {t['signup_button']}
                </a>
              </td>
            </tr>
          </table>

          <p style="margin:0 0 8px 0;font-size:13px;color:#374151;">{t['link_fallback']}</p>
          <p style="margin:0 0 12px 0;word-break:break-all;font-size:12px;color:#6b7280;">{confirmation_url}</p>

          <p style="margin:0 0 8px 0;font-size:13px;color:#374151;">{t['signup_otp_intro']}</p>
          <p style="margin:0 0 16px 0;font-family:Consolas,Menlo,Monaco,monospace;font-size:16px;font-weight:700;letter-spacing:2px;">{otp_token}</p>

          <p style="margin:0 0 8px 0;font-size:12px;color:#6b7280;">{t['signup_security']}</p>
          <p style="margin:0 0 0 0;font-size:12px;color:#6b7280;">{t['signup_ignore']}</p>
        </div>
        """

        # Contenu en anglais (fallback)
        fallback_content = f"""
        <p style="margin:0 0 12px 0;font-size:13px;">{t_en['signup_body']}</p>
        <p style="margin:0 0 8px 0;font-size:13px;">
          <a href="{confirmation_url}" style="color:#0ea5e9;text-decoration:underline;">{t_en['signup_button']}</a>
        </p>
        <p style="margin:0 0 8px 0;font-size:12px;color:#6b7280;">{t_en['signup_otp_intro']}</p>
        <p style="margin:0 0 0 0;font-family:Consolas,Menlo,Monaco,monospace;font-size:15px;font-weight:700;letter-spacing:2px;">{otp_token}</p>
        """

        html = EmailTemplates.get_base_template(
            primary_content, fallback_content, lang
        )
        subject = t["signup_title"]

        return subject, html

    @staticmethod
    def generate_password_reset_email(
        lang: EmailLanguage,
        user_email: str,
        first_name: Optional[str],
        confirmation_url: str,
        otp_token: str,
    ) -> tuple[str, str]:
        """Génère le HTML pour l'email de reset password"""
        translations = EmailTemplates.get_translations()
        t = translations.get(lang, translations[EmailLanguage.EN])
        t_en = translations[EmailLanguage.EN]

        greeting = f"{t['signup_greeting']}{' ' + first_name if first_name else ''}"

        primary_content = f"""
        <div style="font-family:Segoe UI,Arial,Helvetica,sans-serif;color:#111827;line-height:1.6;">
          <h2 style="margin:0 0 12px 0;font-size:20px;">{t['reset_title']}</h2>
          <p style="margin:0 0 12px 0;font-size:14px;">{greeting},</p>
          <p style="margin:0 0 16px 0;font-size:14px;">{t['reset_body']}</p>

          <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 16px 0;">
            <tr>
              <td align="center" bgcolor="#0ea5e9" style="border-radius:8px;">
                <a href="{confirmation_url}"
                   style="display:inline-block;padding:12px 18px;font-family:Segoe UI,Arial,Helvetica,sans-serif;
                          font-size:14px;font-weight:600;color:#ffffff;text-decoration:none;">
                  {t['reset_button']}
                </a>
              </td>
            </tr>
          </table>

          <p style="margin:0 0 8px 0;font-size:13px;color:#374151;">{t['link_fallback']}</p>
          <p style="margin:0 0 12px 0;word-break:break-all;font-size:12px;color:#6b7280;">{confirmation_url}</p>

          <p style="margin:0 0 8px 0;font-size:13px;color:#374151;">{t['signup_otp_intro']}</p>
          <p style="margin:0 0 16px 0;font-family:Consolas,Menlo,Monaco,monospace;font-size:16px;font-weight:700;letter-spacing:2px;">{otp_token}</p>

          <p style="margin:0 0 0 0;font-size:12px;color:#6b7280;">{t['signup_security']}</p>
        </div>
        """

        fallback_content = f"""
        <p style="margin:0 0 12px 0;font-size:13px;">{t_en['reset_body']}</p>
        <p style="margin:0 0 8px 0;font-size:13px;">
          <a href="{confirmation_url}" style="color:#0ea5e9;text-decoration:underline;">{t_en['reset_button']}</a>
        </p>
        <p style="margin:0 0 8px 0;font-size:12px;color:#6b7280;">{t_en['signup_otp_intro']}</p>
        <p style="margin:0 0 0 0;font-family:Consolas,Menlo,Monaco,monospace;font-size:15px;font-weight:700;letter-spacing:2px;">{otp_token}</p>
        """

        html = EmailTemplates.get_base_template(
            primary_content, fallback_content, lang
        )
        subject = t["reset_title"]

        return subject, html


class EmailService:
    """Service d'envoi d'emails via SMTP"""

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("SMTP_FROM_EMAIL", self.smtp_user)
        self.from_name = os.getenv("SMTP_FROM_NAME", "Intelia Expert")

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """Envoie un email HTML via SMTP"""
        try:
            if not self.smtp_user or not self.smtp_password:
                logger.error("SMTP credentials not configured")
                return False

            logger.info(f"[EmailService] Tentative envoi email à {mask_email(to_email)}")
            logger.info(f"[EmailService] SMTP: {self.smtp_host}:{self.smtp_port}")

            # Créer le message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            # Ajouter le contenu HTML
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            # Envoyer via SMTP - utiliser SMTP_SSL pour port 465, SMTP+STARTTLS pour port 587
            if self.smtp_port == 465:
                # SSL direct (Resend, Gmail avec App Password)
                logger.info("[EmailService] Utilisation SMTP_SSL (port 465)")
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30) as server:
                    logger.info("[EmailService] Connexion SSL établie, login...")
                    server.login(self.smtp_user, self.smtp_password)
                    logger.info("[EmailService] Login réussi, envoi du message...")
                    server.send_message(msg)
                    logger.info("[EmailService] Message envoyé avec succès")
            else:
                # STARTTLS (port 587)
                logger.info("[EmailService] Utilisation SMTP+STARTTLS (port 587)")
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    logger.info("[EmailService] Connexion établie, STARTTLS...")
                    server.starttls()
                    logger.info("[EmailService] STARTTLS OK, login...")
                    server.login(self.smtp_user, self.smtp_password)
                    logger.info("[EmailService] Login réussi, envoi du message...")
                    server.send_message(msg)
                    logger.info("[EmailService] Message envoyé avec succès")

            logger.info(f"✅ Email sent successfully to {mask_email(to_email)}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to send email to {mask_email(to_email)}: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def send_auth_email(
        self,
        email_type: EmailType,
        to_email: str,
        language: str,
        confirmation_url: str,
        otp_token: str,
        first_name: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Envoie un email d'authentification dans la langue de l'utilisateur"""
        try:
            # Convertir la langue en EmailLanguage
            try:
                lang = EmailLanguage(language.lower())
            except ValueError:
                lang = EmailLanguage.EN
                logger.warning(
                    f"Unsupported language '{language}', falling back to English"
                )

            # Générer le contenu selon le type d'email
            if email_type == EmailType.SIGNUP_CONFIRMATION:
                subject, html = EmailTemplates.generate_signup_email(
                    lang, to_email, first_name, confirmation_url, otp_token
                )
            elif email_type == EmailType.PASSWORD_RESET:
                subject, html = EmailTemplates.generate_password_reset_email(
                    lang, to_email, first_name, confirmation_url, otp_token
                )
            else:
                logger.error(f"Unsupported email type: {email_type}")
                return False

            # Envoyer l'email
            return self.send_email(to_email, subject, html)

        except Exception as e:
            logger.error(f"Failed to send auth email: {e}")
            return False


# Singleton instance
_email_service = None


def get_email_service() -> EmailService:
    """Récupère l'instance singleton du service d'email"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
