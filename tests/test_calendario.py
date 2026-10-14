"""Prove del calendario della raccolta, senza Home Assistant.

Uso:  python3 tests/test_calendario.py
"""
import importlib.util
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "rifiuti_agesp"
spec = importlib.util.spec_from_file_location("calendario", BASE / "calendario.py")
cal = importlib.util.module_from_spec(spec)
sys.modules["calendario"] = cal
spec.loader.exec_module(cal)

MER, SAB = 2, 5
# zona di casa: mercoledì umido, carta, vetro · sabato umido, plastica, secco
GIORNI = {"umido": [MER, SAB], "carta": [MER], "vetro": [MER], "plastica": [SAB], "secco": [SAB]}
c = cal.Calendario(GIORNI)

assert c.configurato
assert not cal.Calendario({}).configurato
assert c.raccolte(date(2026, 10, 14)) == ["umido", "carta", "vetro"]          # mercoledì
assert c.raccolte(date(2026, 10, 15)) == []                                    # giovedì
assert c.raccolte(date(2026, 10, 17)) == ["umido", "plastica", "secco"]       # sabato
assert c.prossima_raccolta(date(2026, 10, 14)) == (date(2026, 10, 17), ["umido", "plastica", "secco"])
assert c.prossimo_ritiro("umido", date(2026, 10, 14)) == date(2026, 10, 14)    # oggi incluso
assert c.prossimo_ritiro("plastica", date(2026, 10, 14)) == date(2026, 10, 17)
assert c.prossimo_ritiro("carta", date(2026, 10, 15)) == date(2026, 10, 21)
assert [g for g, _ in c.passaggi(date(2026, 10, 14), 14)] == [
    date(2026, 10, 14), date(2026, 10, 17), date(2026, 10, 21), date(2026, 10, 24)]

# eccezioni: Santo Stefano anticipato a lunedì 28/12... e Epifania annullata
ecc = cal.leggi_eccezioni("""
# festività 2026-27
26/12/2026 > 28/12/2026
2027-01-06 > annullata   # Epifania
""")
assert ecc == [cal.Eccezione(date(2026, 12, 26), date(2026, 12, 28)), cal.Eccezione(date(2027, 1, 6), None)]
c2 = cal.Calendario(GIORNI, ecc)
assert c2.raccolte(date(2026, 12, 26)) == []
assert c2.raccolte(date(2026, 12, 28)) == ["umido", "plastica", "secco"]
assert c2.nota(date(2026, 12, 28)) == "Recupero della raccolta di sabato 26/12"
assert c2.raccolte(date(2027, 1, 6)) == []
assert c2.prossimo_ritiro("carta", date(2027, 1, 4)) == date(2027, 1, 13)
assert c2.prossima_raccolta(date(2026, 12, 23)) == (date(2026, 12, 28), ["umido", "plastica", "secco"])

# spostamento su un giorno che ha già raccolte: si sommano senza doppioni
c3 = cal.Calendario(GIORNI, cal.leggi_eccezioni("17/10/2026 > 21/10/2026"))
assert c3.raccolte(date(2026, 10, 21)) == ["umido", "plastica", "carta", "vetro", "secco"]

for sbagliata in ["26/12 > 28/12/2026", "26/12/2026 28/12/2026", "31/02/2026 > annullata", "domani > annullata"]:
    try:
        cal.leggi_eccezioni(sbagliata)
    except cal.EccezioneNonValida as err:
        assert err.riga == sbagliata
    else:
        raise AssertionError(f"accettata per errore: {sbagliata}")

print("calendario: tutte le prove superate")
