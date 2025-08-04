import sys
import os
sys.path.insert(0, '.')

try:
    from rag.embedder import FastRAGEmbedder
    print('✅ Import FastRAGEmbedder: OK')
except ImportError as e:
    print(f'❌ Import FastRAGEmbedder: {e}')

try:
    from dotenv import load_dotenv
    load_dotenv()
    print('✅ dotenv: OK')
except ImportError:
    print('⚠️ dotenv: Non disponible')

# Test API Key
api_key = os.getenv('OPENAI_API_KEY')
if api_key and api_key.startswith('sk-'):
    print('✅ OpenAI API Key: Format valide')
elif api_key:
    print('❌ OpenAI API Key: Format invalide')
else:
    print('❌ OpenAI API Key: Non configurée')
