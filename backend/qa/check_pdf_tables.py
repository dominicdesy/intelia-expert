import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rag.parser_router import ParserRouter
from collections import Counter
# remplace par un PDF qui a des tableaux
fp = r"C:\intelia_gpt\documents\public\species\broiler\breeds\ross_308_broiler\RossxRoss308-BroilerPerformanceObjectives2022-EN.pdf"
r = ParserRouter()
docs = r.parse_file(fp)
print("docs:", len(docs))
print("by_type:", Counter(d.metadata.get("chunk_type","?") for d in docs))
for d in docs:
    if d.metadata.get("chunk_type")=="table":
        print("\nTABLE META:", d.metadata)
        print(d.page_content[:400].replace("\n"," "))
        break
