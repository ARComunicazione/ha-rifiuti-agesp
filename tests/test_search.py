"""Prove del motore di ricerca, senza Home Assistant.

Uso:  python3 tests/test_search.py
"""
import importlib.util
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "rifiuti_agesp"
spec = importlib.util.spec_from_file_location("search", BASE / "search.py")
search = importlib.util.module_from_spec(spec)
spec.loader.exec_module(search)

motore = search.MotoreRicerca.da_file(BASE / "data" / "dizionario_agesp.json", BASE / "data" / "sinonimi.json")

# (ricerca, voce attesa tra i primi N risultati, N)
CASI = [
    ("polistirolo", "Polistirolo", 1),
    ("bottiglia", "Bottiglie in plastica", 2),
    ("bottiglia", "Bottiglie in vetro", 2),
    ("pila", "Pile esaurite - esauste", 1),
    ("pile", "Pile esaurite - esauste", 1),
    ("batteria", "Pile esaurite - esauste", 3),
    ("scottex", "Carta assorbente", 1),
    ("tetrapak", "Tetra Pak (cartone del latte, panna, succhi, etc.)", 2),
    ("cartone della pizza", "Scatole pizza da asporto", 1),
    ("cartone pizza", "Scatole pizza da asporto", 1),
    ("dove butto il polistirolo?", "Polistirolo", 1),
    ("lattina", "Lattine in alluminio per bevande (aranciata, gassosa, birra)", 1),
    ("attaccapanni", "Attaccapanni in plastica", 4),
    ("polisterolo", "Polistirolo", 1),          # errore di battitura
    ("bottilia", "Bottiglie", 2),               # errore di battitura
    ("polist", "Polistirolo", 1),               # parola a metà
    ("olio fritto", "Olio alimentare (ad es. olio patate fritte, etc.)", 1),
    ("capsule caffè", "Cialde (capsule) per macchine da caffè", 1),
    ("gusci d'uovo", "Gusci d'uovo", 1),
    ("uova", "Uova", 1),
    ("pannolino", "Pannolini, pannoloni,traverse assorbenti", 1),
    ("frigo", "Frigorifero di provenienza domestica", 1),
    ("ceneri legno non verniciato", "Ceneri spente di legno NON verniciato", 1),
    ("acetone", "Acetone, flacone vuoto, di provenienza domestica", 2),
    ("medicine", "Medicinali scaduti", 2),
    ("cicca", "Mozziconi spenti di sigarette", 1),
    ("vasetto yogurt", "Vasetto yogurt", 1),
    ("sacchi", "Sacchetto", 3),
    ("cotton fioc", "Cotton fioc", 1),
    ("lampadina", "Lampadine", 3),
]

errori = 0
for testo, attesa, n in CASI:
    r = motore.cerca(testo)
    primi = [x["voce"] for x in r["risultati"][:n]]
    ok = any(v.startswith(attesa) for v in primi)
    if not ok:
        errori += 1
    print(f"{'OK ' if ok else 'ERR'} {testo!r:32} -> {primi}")

# casi di esito unico / non trovato
r = motore.cerca("pile")
assert r["esito_unico"] and [d["id"] for d in r["esito_unico"]] == ["cmr", "territorio"], r["esito_unico"]
r = motore.cerca("bottiglia")
assert r["esito_unico"] is None
r = motore.cerca("astronave")
assert not r["trovato"], r
r = motore.cerca("")
assert r["risultati"] == []

# tempo per tasto premuto
t = time.perf_counter()
for q in ["p", "po", "pol", "poli", "polis", "polist", "polisti", "polistir", "polistiro", "polistirol", "polistirolo",
          "cartone della pizza", "bottilia", "dove butto il polistirolo"]:
    motore.cerca(q)
ms = (time.perf_counter() - t) * 1000 / 14
print(f"\ntempo medio per ricerca: {ms:.1f} ms")

print(f"{len(CASI) - errori}/{len(CASI)} casi superati")
sys.exit(1 if errori else 0)
