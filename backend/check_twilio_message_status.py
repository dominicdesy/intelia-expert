"""
Script pour vérifier le statut des messages WhatsApp dans Twilio
"""
import os
from twilio.rest import Client

# Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

def check_message_status(message_sid: str):
    """Vérifie le statut d'un message Twilio"""
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    try:
        message = client.messages(message_sid).fetch()

        print(f"\n{'='*60}")
        print(f"📱 Message SID: {message.sid}")
        print(f"{'='*60}")
        print(f"From: {message.from_}")
        print(f"To: {message.to}")
        print(f"Status: {message.status}")
        print(f"Date Created: {message.date_created}")
        print(f"Date Updated: {message.date_updated}")
        print(f"Date Sent: {message.date_sent}")
        print(f"Direction: {message.direction}")
        print(f"Price: {message.price} {message.price_unit}")
        print(f"Error Code: {message.error_code}")
        print(f"Error Message: {message.error_message}")
        print(f"\n📝 Body (first 200 chars):")
        print(f"{message.body[:200]}...")
        print(f"{'='*60}\n")

        # Interpréter le statut
        if message.status == "delivered":
            print("✅ Message livré avec succès!")
        elif message.status == "sent":
            print("📤 Message envoyé, en attente de confirmation de livraison")
        elif message.status == "failed":
            print("❌ ÉCHEC - Message non envoyé")
        elif message.status == "undelivered":
            print("⚠️ Message envoyé mais non livré au destinataire")
        else:
            print(f"ℹ️ Statut: {message.status}")

        return message

    except Exception as e:
        print(f"❌ Erreur lors de la récupération du message {message_sid}: {e}")
        return None


def check_recent_messages(limit=10):
    """Liste les derniers messages WhatsApp"""
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    print(f"\n{'='*60}")
    print(f"📱 Derniers {limit} messages WhatsApp")
    print(f"{'='*60}\n")

    messages = client.messages.list(limit=limit)

    for msg in messages:
        if "whatsapp:" in msg.from_ or "whatsapp:" in msg.to:
            status_icon = {
                "delivered": "✅",
                "sent": "📤",
                "failed": "❌",
                "undelivered": "⚠️",
                "queued": "⏳",
                "sending": "📨"
            }.get(msg.status, "❓")

            print(f"{status_icon} {msg.sid}")
            print(f"   {msg.from_} → {msg.to}")
            print(f"   Status: {msg.status}")
            print(f"   Date: {msg.date_created}")
            print(f"   Body: {msg.body[:100]}...")
            print()


if __name__ == "__main__":
    print("🔍 Vérification des messages WhatsApp Twilio\n")

    # Vérifier les messages spécifiques des logs
    message_sids = [
        "SMf1e60463e27a3c5516b59f4b22d2cfe1",  # Part 1/2
        "SM19e7af9325dc61d3fc74a7a70d7fdeb9",  # Part 2/2
    ]

    print("📋 Vérification des messages spécifiques:\n")
    for sid in message_sids:
        check_message_status(sid)

    # Lister les messages récents
    print("\n" + "="*60)
    check_recent_messages(limit=5)
