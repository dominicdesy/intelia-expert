#!/usr/bin/env python3
"""
Script pour ajouter les traductions de recherche dans les 16 langues
"""

import json
import os
from pathlib import Path

# Traductions pour les 7 nouvelles clés
TRANSLATIONS = {
    "en": {
        "history.searchPlaceholder": "Search conversations...",
        "history.searching": "Searching...",
        "history.searchError": "Search failed. Please try again.",
        "history.noSearchResults": "No results found",
        "history.tryDifferentSearch": "Try searching for something else",
        "history.resultsFound": "results found",
    },
    "fr": {
        "history.searchPlaceholder": "Rechercher dans les conversations...",
        "history.searching": "Recherche en cours...",
        "history.searchError": "La recherche a échoué. Veuillez réessayer.",
        "history.noSearchResults": "Aucun résultat trouvé",
        "history.tryDifferentSearch": "Essayez de rechercher autre chose",
        "history.resultsFound": "résultats trouvés",
    },
    "es": {
        "history.searchPlaceholder": "Buscar conversaciones...",
        "history.searching": "Buscando...",
        "history.searchError": "La búsqueda falló. Por favor, inténtelo de nuevo.",
        "history.noSearchResults": "No se encontraron resultados",
        "history.tryDifferentSearch": "Intente buscar algo diferente",
        "history.resultsFound": "resultados encontrados",
    },
    "pt": {
        "history.searchPlaceholder": "Pesquisar conversas...",
        "history.searching": "Pesquisando...",
        "history.searchError": "A pesquisa falhou. Por favor, tente novamente.",
        "history.noSearchResults": "Nenhum resultado encontrado",
        "history.tryDifferentSearch": "Tente pesquisar algo diferente",
        "history.resultsFound": "resultados encontrados",
    },
    "de": {
        "history.searchPlaceholder": "Gespräche durchsuchen...",
        "history.searching": "Suche läuft...",
        "history.searchError": "Die Suche ist fehlgeschlagen. Bitte versuchen Sie es erneut.",
        "history.noSearchResults": "Keine Ergebnisse gefunden",
        "history.tryDifferentSearch": "Versuchen Sie, nach etwas anderem zu suchen",
        "history.resultsFound": "Ergebnisse gefunden",
    },
    "it": {
        "history.searchPlaceholder": "Cerca conversazioni...",
        "history.searching": "Ricerca in corso...",
        "history.searchError": "La ricerca è fallita. Riprova.",
        "history.noSearchResults": "Nessun risultato trovato",
        "history.tryDifferentSearch": "Prova a cercare qualcos'altro",
        "history.resultsFound": "risultati trovati",
    },
    "zh": {
        "history.searchPlaceholder": "搜索对话...",
        "history.searching": "搜索中...",
        "history.searchError": "搜索失败。请重试。",
        "history.noSearchResults": "未找到结果",
        "history.tryDifferentSearch": "尝试搜索其他内容",
        "history.resultsFound": "个结果",
    },
    "ja": {
        "history.searchPlaceholder": "会話を検索...",
        "history.searching": "検索中...",
        "history.searchError": "検索に失敗しました。もう一度お試しください。",
        "history.noSearchResults": "結果が見つかりません",
        "history.tryDifferentSearch": "別のキーワードで検索してみてください",
        "history.resultsFound": "件の結果",
    },
    "nl": {
        "history.searchPlaceholder": "Zoek gesprekken...",
        "history.searching": "Zoeken...",
        "history.searchError": "Zoeken mislukt. Probeer het opnieuw.",
        "history.noSearchResults": "Geen resultaten gevonden",
        "history.tryDifferentSearch": "Probeer iets anders te zoeken",
        "history.resultsFound": "resultaten gevonden",
    },
    "pl": {
        "history.searchPlaceholder": "Szukaj rozmów...",
        "history.searching": "Wyszukiwanie...",
        "history.searchError": "Wyszukiwanie nie powiodło się. Spróbuj ponownie.",
        "history.noSearchResults": "Nie znaleziono wyników",
        "history.tryDifferentSearch": "Spróbuj wyszukać coś innego",
        "history.resultsFound": "znalezionych wyników",
    },
    "ar": {
        "history.searchPlaceholder": "البحث في المحادثات...",
        "history.searching": "جاري البحث...",
        "history.searchError": "فشل البحث. يرجى المحاولة مرة أخرى.",
        "history.noSearchResults": "لم يتم العثور على نتائج",
        "history.tryDifferentSearch": "حاول البحث عن شيء آخر",
        "history.resultsFound": "نتائج موجودة",
    },
    "hi": {
        "history.searchPlaceholder": "बातचीत खोजें...",
        "history.searching": "खोज रहा है...",
        "history.searchError": "खोज विफल रही। कृपया पुनः प्रयास करें।",
        "history.noSearchResults": "कोई परिणाम नहीं मिला",
        "history.tryDifferentSearch": "कुछ और खोजने का प्रयास करें",
        "history.resultsFound": "परिणाम मिले",
    },
    "th": {
        "history.searchPlaceholder": "ค้นหาการสนทนา...",
        "history.searching": "กำลังค้นหา...",
        "history.searchError": "การค้นหาล้มเหลว โปรดลองอีกครั้ง",
        "history.noSearchResults": "ไม่พบผลลัพธ์",
        "history.tryDifferentSearch": "ลองค้นหาสิ่งอื่น",
        "history.resultsFound": "ผลลัพธ์ที่พบ",
    },
    "vi": {
        "history.searchPlaceholder": "Tìm kiếm cuộc trò chuyện...",
        "history.searching": "Đang tìm kiếm...",
        "history.searchError": "Tìm kiếm thất bại. Vui lòng thử lại.",
        "history.noSearchResults": "Không tìm thấy kết quả",
        "history.tryDifferentSearch": "Thử tìm kiếm điều gì đó khác",
        "history.resultsFound": "kết quả tìm thấy",
    },
    "tr": {
        "history.searchPlaceholder": "Sohbetleri ara...",
        "history.searching": "Aranıyor...",
        "history.searchError": "Arama başarısız oldu. Lütfen tekrar deneyin.",
        "history.noSearchResults": "Sonuç bulunamadı",
        "history.tryDifferentSearch": "Başka bir şey aramayı deneyin",
        "history.resultsFound": "sonuç bulundu",
    },
    "id": {
        "history.searchPlaceholder": "Cari percakapan...",
        "history.searching": "Mencari...",
        "history.searchError": "Pencarian gagal. Silakan coba lagi.",
        "history.noSearchResults": "Tidak ada hasil yang ditemukan",
        "history.tryDifferentSearch": "Coba cari sesuatu yang lain",
        "history.resultsFound": "hasil ditemukan",
    },
}

def main():
    locales_dir = Path("frontend/public/locales")

    for lang_code, translations in TRANSLATIONS.items():
        json_file = locales_dir / f"{lang_code}.json"

        print(f"Updating {json_file}...")

        # Lire le fichier JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Ajouter les nouvelles traductions après "history.search"
        # Trouver l'index de "history.search"
        keys = list(data.keys())
        search_index = keys.index("history.search") if "history.search" in keys else -1

        if search_index >= 0:
            # Insérer les nouvelles clés après "history.search"
            new_data = {}
            for i, key in enumerate(keys):
                new_data[key] = data[key]
                if key == "history.search":
                    # Ajouter les nouvelles traductions
                    for new_key, new_value in translations.items():
                        new_data[new_key] = new_value

            # Sauvegarder
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)

            print(f"[OK] {lang_code}.json updated with {len(translations)} new keys")
        else:
            print(f"[WARN] Could not find 'history.search' in {lang_code}.json")

if __name__ == "__main__":
    main()
