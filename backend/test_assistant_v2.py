# test_assistant_v2.py
# Usage:
#   python test_assistant_v2.py --assistant-id asst_xxx --question "..."

import argparse, os, sys, time
from openai import OpenAI, BadRequestError
from dotenv import load_dotenv

load_dotenv()  # besoin de OPENAI_API_KEY dans .env ou env vars

DATA_ONLY_REMINDER = (
    "Rappelle-toi: Réponds UNIQUEMENT depuis les documents du vector store. "
    "Si l'info n'est pas présente, réponds exactement: "
    "\"Hors base: information absente de la connaissance Intelia.\" "
    "Inclue des citations (doc_id, page/page_span)."
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assistant-id", required=True)
    ap.add_argument("--question", required=True)
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set.")
        sys.exit(1)

    client = OpenAI()

    try:
        # 1) Thread
        thread = client.beta.threads.create()

        # 2) Message user
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"{args.question}\n\n{DATA_ONLY_REMINDER}"
        )

        # 3) Lancer le run
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=args.assistant_id
        )

        # 4) Poll jusqu'à complétion
        while True:
            r = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if r.status in ("completed", "failed", "cancelled", "expired"):
                break
            time.sleep(0.8)

        if r.status != "completed":
            print(f"❌ Run status: {r.status}")
            return

        # 5) Lire la réponse + citations
        msgs = client.beta.threads.messages.list(thread_id=thread.id)
        for m in msgs.data:
            if m.role == "assistant":
                print("----- ANSWER -----")
                for c in m.content:
                    if getattr(c, "type", "") == "text":
                        print(c.text.value)

                cits = []
                for c in m.content:
                    if getattr(c, "type", "") == "text" and c.text.annotations:
                        for ann in c.text.annotations:
                            if hasattr(ann, "file_citation") and ann.file_citation:
                                cits.append({
                                    "file_id": ann.file_citation.file_id,
                                    # certains SDK incluent "quote" / "page", selon le parseur
                                })
                print("\n----- CITATIONS -----")
                if cits:
                    import json
                    print(json.dumps(cits, indent=2, ensure_ascii=False))
                else:
                    print("(Aucune citation structurée; le modèle peut les inclure dans le texte.)")
                break

    except BadRequestError as e:
        print("BadRequestError:", e)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
