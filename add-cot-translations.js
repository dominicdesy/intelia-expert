const fs = require('fs');
const path = require('path');

// Traductions CoT pour chaque langue
const cotTranslations = {
  en: {
    "chat.cot.showReasoning": "Show detailed reasoning",
    "chat.cot.hideReasoning": "Hide reasoning",
    "chat.cot.thinking": "Thinking",
    "chat.cot.analysis": "Analysis",
    "chat.cot.answer": "Answer"
  },
  es: {
    "chat.cot.showReasoning": "Ver razonamiento detallado",
    "chat.cot.hideReasoning": "Ocultar razonamiento",
    "chat.cot.thinking": "Pensamiento",
    "chat.cot.analysis": "Análisis",
    "chat.cot.answer": "Respuesta"
  },
  de: {
    "chat.cot.showReasoning": "Detaillierte Überlegung anzeigen",
    "chat.cot.hideReasoning": "Überlegung ausblenden",
    "chat.cot.thinking": "Denken",
    "chat.cot.analysis": "Analyse",
    "chat.cot.answer": "Antwort"
  },
  it: {
    "chat.cot.showReasoning": "Mostra ragionamento dettagliato",
    "chat.cot.hideReasoning": "Nascondi ragionamento",
    "chat.cot.thinking": "Pensiero",
    "chat.cot.analysis": "Analisi",
    "chat.cot.answer": "Risposta"
  },
  pt: {
    "chat.cot.showReasoning": "Mostrar raciocínio detalhado",
    "chat.cot.hideReasoning": "Ocultar raciocínio",
    "chat.cot.thinking": "Pensamento",
    "chat.cot.analysis": "Análise",
    "chat.cot.answer": "Resposta"
  },
  nl: {
    "chat.cot.showReasoning": "Gedetailleerde redenering tonen",
    "chat.cot.hideReasoning": "Redenering verbergen",
    "chat.cot.thinking": "Denken",
    "chat.cot.analysis": "Analyse",
    "chat.cot.answer": "Antwoord"
  },
  pl: {
    "chat.cot.showReasoning": "Pokaż szczegółowe rozumowanie",
    "chat.cot.hideReasoning": "Ukryj rozumowanie",
    "chat.cot.thinking": "Myślenie",
    "chat.cot.analysis": "Analiza",
    "chat.cot.answer": "Odpowiedź"
  },
  ar: {
    "chat.cot.showReasoning": "عرض التفكير التفصيلي",
    "chat.cot.hideReasoning": "إخفاء التفكير",
    "chat.cot.thinking": "التفكير",
    "chat.cot.analysis": "التحليل",
    "chat.cot.answer": "الإجابة"
  },
  zh: {
    "chat.cot.showReasoning": "显示详细推理",
    "chat.cot.hideReasoning": "隐藏推理",
    "chat.cot.thinking": "思考",
    "chat.cot.analysis": "分析",
    "chat.cot.answer": "答案"
  },
  ja: {
    "chat.cot.showReasoning": "詳細な推論を表示",
    "chat.cot.hideReasoning": "推論を非表示",
    "chat.cot.thinking": "思考",
    "chat.cot.analysis": "分析",
    "chat.cot.answer": "回答"
  },
  vi: {
    "chat.cot.showReasoning": "Hiển thị lý luận chi tiết",
    "chat.cot.hideReasoning": "Ẩn lý luận",
    "chat.cot.thinking": "Suy nghĩ",
    "chat.cot.analysis": "Phân tích",
    "chat.cot.answer": "Câu trả lời"
  },
  tr: {
    "chat.cot.showReasoning": "Detaylı akıl yürütmeyi göster",
    "chat.cot.hideReasoning": "Akıl yürütmeyi gizle",
    "chat.cot.thinking": "Düşünme",
    "chat.cot.analysis": "Analiz",
    "chat.cot.answer": "Cevap"
  },
  th: {
    "chat.cot.showReasoning": "แสดงการให้เหตุผลโดยละเอียด",
    "chat.cot.hideReasoning": "ซ่อนการให้เหตุผล",
    "chat.cot.thinking": "การคิด",
    "chat.cot.analysis": "การวิเคราะห์",
    "chat.cot.answer": "คำตอบ"
  },
  hi: {
    "chat.cot.showReasoning": "विस्तृत तर्क दिखाएं",
    "chat.cot.hideReasoning": "तर्क छुपाएं",
    "chat.cot.thinking": "सोच",
    "chat.cot.analysis": "विश्लेषण",
    "chat.cot.answer": "उत्तर"
  },
  id: {
    "chat.cot.showReasoning": "Tampilkan penalaran detail",
    "chat.cot.hideReasoning": "Sembunyikan penalaran",
    "chat.cot.thinking": "Pemikiran",
    "chat.cot.analysis": "Analisis",
    "chat.cot.answer": "Jawaban"
  }
};

const localesDir = path.join(__dirname, 'frontend', 'public', 'locales');

// Ajouter les traductions CoT à chaque fichier de langue
Object.keys(cotTranslations).forEach(lang => {
  const filePath = path.join(localesDir, `${lang}.json`);

  try {
    // Lire le fichier JSON existant
    const content = fs.readFileSync(filePath, 'utf8');
    const translations = JSON.parse(content);

    // Vérifier si les clés existent déjà
    if (translations['chat.cot.showReasoning']) {
      console.log(`✓ ${lang}.json - Clés CoT déjà présentes, skip`);
      return;
    }

    // Ajouter les nouvelles clés CoT
    Object.assign(translations, cotTranslations[lang]);

    // Écrire le fichier mis à jour avec indentation
    fs.writeFileSync(filePath, JSON.stringify(translations, null, 2), 'utf8');
    console.log(`✓ ${lang}.json - Clés CoT ajoutées`);

  } catch (error) {
    console.error(`✗ ${lang}.json - Erreur: ${error.message}`);
  }
});

console.log('\n✅ Traductions CoT ajoutées avec succès!');
