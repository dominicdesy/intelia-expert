#!/bin/bash
# evaluate.sh - Script simplifié pour évaluation RAGAS manuelle
#
# Usage:
#   ./scripts/evaluate.sh quick   # 5 questions (~1 min, ~$0.05)
#   ./scripts/evaluate.sh full    # 28 questions (~5 min, ~$0.50)
#   ./scripts/evaluate.sh test    # 3 questions pour tester (~30s, ~$0.01)

set -e

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'aide
show_help() {
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  RAGAS Evaluation - Intelia Expert LLM${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Usage: $0 [MODE]"
    echo ""
    echo "Modes disponibles:"
    echo -e "  ${GREEN}test${NC}   - Test rapide (3 questions, ~30s, ~\$0.01)"
    echo -e "  ${GREEN}quick${NC}  - Évaluation rapide (5 questions, ~1 min, ~\$0.05)"
    echo -e "  ${GREEN}full${NC}   - Évaluation complète (28 questions, ~5 min, ~\$0.50)"
    echo ""
    echo "Exemples:"
    echo "  $0 test    # Pour tester que tout fonctionne"
    echo "  $0 quick   # Pour vérification rapide après changements"
    echo "  $0 full    # Pour évaluation complète avant déploiement"
    echo ""
}

# Vérifier que le script est exécuté depuis /app/llm
if [ ! -f "scripts/run_ragas_evaluation.py" ]; then
    echo -e "${RED}❌ Erreur: Ce script doit être exécuté depuis /app/llm${NC}"
    echo -e "${YELLOW}   Utilisez: cd /app/llm && ./scripts/evaluate.sh${NC}"
    exit 1
fi

# Vérifier variable d'environnement
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}❌ Erreur: OPENAI_API_KEY non définie${NC}"
    echo -e "${YELLOW}   Configurez avec: export OPENAI_API_KEY='sk-...'${NC}"
    exit 1
fi

# Parser le mode
MODE=${1:-quick}

case $MODE in
    test)
        echo -e "${BLUE}🧪 Test rapide (3 questions)${NC}"
        echo -e "${YELLOW}   Durée: ~30 secondes${NC}"
        echo -e "${YELLOW}   Coût estimé: ~\$0.01${NC}"
        echo ""
        python3 scripts/run_ragas_evaluation.py \
            --test-cases 3 \
            --llm gpt-4o-mini
        ;;

    quick)
        echo -e "${BLUE}🚀 Évaluation rapide (5 questions)${NC}"
        echo -e "${YELLOW}   Durée: ~1 minute${NC}"
        echo -e "${YELLOW}   Coût estimé: ~\$0.05${NC}"
        echo ""
        python3 scripts/run_ragas_evaluation.py \
            --test-cases 5 \
            --llm gpt-4o-mini
        ;;

    full)
        echo -e "${BLUE}📊 Évaluation complète (28 questions)${NC}"
        echo -e "${YELLOW}   Durée: ~5 minutes${NC}"
        echo -e "${YELLOW}   Coût estimé: ~\$0.50${NC}"
        echo ""
        read -p "Continuer? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Annulé${NC}"
            exit 0
        fi

        python3 scripts/run_ragas_evaluation.py \
            --llm gpt-4o-mini
        ;;

    help|--help|-h)
        show_help
        exit 0
        ;;

    *)
        echo -e "${RED}❌ Mode invalide: $MODE${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

# Résumé final
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Évaluation terminée${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📁 Résultats sauvegardés dans: ${BLUE}logs/ragas_evaluation_*.json${NC}"
echo -e "📄 Logs disponibles dans: ${BLUE}logs/ragas_evaluation_*.log${NC}"
echo ""
echo -e "Pour voir les résultats:"
echo -e "  ${YELLOW}ls -lht logs/ragas_evaluation_* | head -5${NC}"
echo ""
