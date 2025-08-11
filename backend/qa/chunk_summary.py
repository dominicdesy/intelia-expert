New-Item -ItemType Directory -Path .\qa -Force | Out-Null
@'
from pathlib import Path
import pickle, json, collections, sys
root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("public/global")
items = pickle.load(open(root/"index.pkl","rb"))
meta  = json.load(open(root/"meta.json","r",encoding="utf-8"))
by_type   = collections.Counter(i["metadata"].get("chunk_type","?")     for i in items)
by_ext    = collections.Counter(i["metadata"].get("file_extension","?") for i in items)
by_parser = collections.Counter(i["metadata"].get("parser_name","?")    for i in items)
print("species:", meta.get("species"))
print("chunks:", len(items))
print("chunk_type:", dict(by_type))
print("ext:", dict(by_ext))
print("top parsers:", by_parser.most_common(8))
'@ | Set-Content -Path .\qa\chunk_summary.py -Encoding UTF8

python .\qa\chunk_summary.py public\broiler
python .\qa\chunk_summary.py public\global
python .\qa\chunk_summary.py public\layer
