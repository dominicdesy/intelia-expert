#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))


async def main():
    # Modification rapide du knowledge_extractor
    extractor_path = Path("knowledge_extractor.py")
    if extractor_path.exists():
        content = extractor_path.read_text(encoding="utf-8")

        # Augmenter le délai d'attente d'indexation
        if "wait_time = min(20, max(10," in content:
            new_content = content.replace(
                "wait_time = min(20, max(10,",
                "wait_time = min(40, max(20,",  # Doubler le délai
            )
            extractor_path.write_text(new_content, encoding="utf-8")
            print("Délais d'indexation augmentés dans knowledge_extractor.py")

    print("Corrections appliquées. Relancez l'extraction.")


if __name__ == "__main__":
    asyncio.run(main())
