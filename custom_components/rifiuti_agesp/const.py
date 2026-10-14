"""Costanti dell'integrazione Rifiuti AGESP."""
from pathlib import Path

DOMAIN = "rifiuti_agesp"

CARTELLA = Path(__file__).parent
FILE_DIZIONARIO = CARTELLA / "data" / "dizionario_agesp.json"
FILE_SINONIMI = CARTELLA / "data" / "sinonimi.json"
CARTELLA_FRONTEND = CARTELLA / "frontend"
FILE_PANNELLO = "rifiuti-agesp-panel.js"

URL_STATICI = f"/{DOMAIN}_static"
URL_PANNELLO = "rifiuti"
COMPONENTE_PANNELLO = "rifiuti-agesp-panel"
TITOLO_PANNELLO = "Rifiuti"
ICONA_PANNELLO = "mdi:recycle"

SERVIZIO_CERCA = "cerca"
ATTR_TESTO = "testo"
ATTR_LIMITE = "limite"
LIMITE_PREDEFINITO = 10
LIMITE_MASSIMO = 50

CONF_ECCEZIONI = "eccezioni"
NOME_DISPOSITIVO = "Rifiuti AGESP"
GIORNI_PASSAGGI = 21   # quanti giorni di calendario mostra la pagina
