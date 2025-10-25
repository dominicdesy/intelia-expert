"""
Script pour générer les previews audio des voix OpenAI
Génère 6 fichiers MP3 (une fois) pour les sélecteurs de voix
"""

import os
import sys
from pathlib import Path
from openai import OpenAI

# Ajouter le chemin parent pour imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration
VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

# Texte de preview multilingue (court pour être rapide)
PREVIEW_TEXT = {
    "fr": "Bonjour, je suis votre assistant avicole Intelia Expert. Je peux vous aider avec vos questions sur l'élevage de volailles.",
    "en": "Hello, I'm your Intelia Expert poultry assistant. I can help you with your poultry farming questions.",
    "es": "Hola, soy tu asistente avícola Intelia Expert. Puedo ayudarte con tus preguntas sobre avicultura.",
    "pt": "Olá, sou o seu assistente avícola Intelia Expert. Posso ajudá-lo com suas perguntas sobre avicultura.",
    "de": "Hallo, ich bin Ihr Geflügel-Assistent Intelia Expert. Ich kann Ihnen bei Fragen zur Geflügelzucht helfen.",
}


def generate_previews():
    """Génère les fichiers audio de preview pour toutes les voix"""

    # Vérifier la clé API
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not defined in environment")
        print("   Set it with: export OPENAI_API_KEY='your-key'")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # Créer le dossier de sortie
    output_dir = Path(__file__).parent.parent.parent / "frontend" / "public" / "audio" / "voice-previews"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Output directory: {output_dir}")
    print(f"[INFO] Generating {len(VOICES)} voices x {len(PREVIEW_TEXT)} languages = {len(VOICES) * len(PREVIEW_TEXT)} files\n")

    total_generated = 0
    total_errors = 0

    # Générer pour chaque voix
    for voice in VOICES:
        print(f"[VOICE] {voice.upper()}")

        for lang_code, text in PREVIEW_TEXT.items():
            try:
                # Appel API OpenAI TTS
                response = client.audio.speech.create(
                    model="tts-1-hd",  # Haute qualité
                    voice=voice,
                    input=text,
                    speed=1.0
                )

                # Sauvegarder le fichier
                output_path = output_dir / f"{voice}_{lang_code}.mp3"
                response.stream_to_file(str(output_path))

                file_size = output_path.stat().st_size / 1024  # KB
                print(f"   [OK] {lang_code}: {output_path.name} ({file_size:.1f} KB)")
                total_generated += 1

            except Exception as e:
                print(f"   [ERROR] {lang_code}: {str(e)}")
                total_errors += 1

        print()  # Ligne vide entre les voix

    # Résumé
    print("=" * 60)
    print(f"[DONE] Generation completed:")
    print(f"   - Files created: {total_generated}")
    print(f"   - Errors: {total_errors}")
    print(f"   - Directory: {output_dir}")
    print("=" * 60)

    # Générer aussi un fichier par défaut (français uniquement pour UI simple)
    print("\n[INFO] Generating default files (FR only)...")
    for voice in VOICES:
        try:
            response = client.audio.speech.create(
                model="tts-1-hd",
                voice=voice,
                input=PREVIEW_TEXT["fr"],
                speed=1.0
            )

            output_path = output_dir / f"{voice}.mp3"
            response.stream_to_file(str(output_path))
            file_size = output_path.stat().st_size / 1024
            print(f"   [OK] {voice}.mp3 ({file_size:.1f} KB)")

        except Exception as e:
            print(f"   [ERROR] {voice}.mp3: {str(e)}")

    print("\n[SUCCESS] All preview files generated successfully!")
    print(f"[INFO] Estimated cost: ~$0.10 (one-time)")


if __name__ == "__main__":
    generate_previews()
