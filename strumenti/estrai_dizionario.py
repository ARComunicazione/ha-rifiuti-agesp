"""Estrae dal PDF "Dizionario dei rifiuti" AGESP le voci e le relative destinazioni.

Le destinazioni nel PDF sono icone vettoriali colorate, non testo: lo script
renderizza le pagine a 300 DPI, divide ogni colonna in righe usando le linee
di separazione grigie e riconosce le icone dal colore di riempimento.

Requisiti: poppler (pdftoppm, pdftotext) e Pillow.
Uso:  python3 estrai_dizionario.py <dizionario.pdf> <output.json>
"""
import json, re, subprocess, sys, tempfile, unicodedata
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image

PRIMA_PAGINA, ULTIMA_PAGINA = 3, 15
XHTML = '{http://www.w3.org/1999/xhtml}'

# Colori di riempimento delle icone (legenda a pag. 2)
COLORI = {
    'umido':      (90, 49, 20),
    'plastica':   (250, 178, 11),
    'grigio':     (145, 143, 143),   # carta (solo contorno) o contenitori sul territorio (pieno)
    'vetro':      (39, 150, 60),
    'secco':      (0, 173, 239),
    'telefonare': (11, 144, 75),
    'tessili':    (0, 108, 92),
    'cmr':        (61, 178, 158),
}
SEPARATORE = (189, 188, 188)
LIME = (183, 225, 118)

DESTINAZIONI = {
    'umido':      {'nome': 'Umido', 'descrizione': 'Frazione organica (umido)', 'tipo': 'porta_a_porta', 'colore': '#5A3114', 'icona': 'mdi:food-apple'},
    'plastica':   {'nome': 'Plastica', 'descrizione': 'Plastica (imballaggi)', 'tipo': 'porta_a_porta', 'colore': '#FAB20B', 'icona': 'mdi:bottle-soda-classic'},
    'carta':      {'nome': 'Carta', 'descrizione': 'Carta, cartone e Tetra Pak', 'tipo': 'porta_a_porta', 'colore': '#918F8F', 'icona': 'mdi:newspaper-variant'},
    'vetro':      {'nome': 'Vetro e lattine', 'descrizione': 'Vetro, alluminio e banda stagnata', 'tipo': 'porta_a_porta', 'colore': '#27963C', 'icona': 'mdi:bottle-wine'},
    'secco':      {'nome': 'Secco', 'descrizione': 'Frazione indifferenziata (secco) - sacco con tag RFID', 'tipo': 'porta_a_porta', 'colore': '#00ADEF', 'icona': 'mdi:trash-can'},
    'telefonare': {'nome': 'Numero verde', 'descrizione': 'Telefonare al numero verde 800 439 040 (lun-ven 8.30-19.00, sabato 8.30-12.30)', 'tipo': 'servizio', 'colore': '#0B904B', 'icona': 'mdi:phone'},
    'tessili':    {'nome': 'Tessili', 'descrizione': 'Contenitore stradale per la raccolta dei rifiuti tessili', 'tipo': 'contenitore', 'colore': '#006C5C', 'icona': 'mdi:tshirt-crew'},
    'territorio': {'nome': 'Contenitori sul territorio', 'descrizione': 'Contenitori distribuiti sul territorio', 'tipo': 'contenitore', 'colore': '#918F8F', 'icona': 'mdi:map-marker'},
    'cmr':        {'nome': 'Centro Multiraccolta', 'descrizione': 'Centro Multiraccolta (CMR), Via Arturo Tosi 1, Busto Arsizio', 'tipo': 'centro', 'colore': '#3DB29E', 'icona': 'mdi:recycle'},
}

# Significato delle voci con due icone
LOGICHE = {
    frozenset({'plastica', 'vetro'}): ('materiale', 'Plastica se il contenitore è di plastica, Vetro se è di vetro'),
    frozenset({'cmr', 'territorio'}): ('alternativa', 'Centro Multiraccolta oppure contenitori sul territorio'),
    frozenset({'secco', 'cmr'}): ('alternativa', 'Secco oppure Centro Multiraccolta'),
}


def vicino(p, c, tol=10):
    return abs(p[0] - c[0]) <= tol and abs(p[1] - c[1]) <= tol and abs(p[2] - c[2]) <= tol


def estrai(pdf, cartella):
    subprocess.run(['pdftoppm', '-r', '300', '-png', '-f', str(PRIMA_PAGINA), '-l', str(ULTIMA_PAGINA), pdf, f'{cartella}/p'], check=True)
    bbox = f'{cartella}/bbox.html'
    subprocess.run(['pdftotext', '-bbox-layout', '-f', str(PRIMA_PAGINA), '-l', str(ULTIMA_PAGINA), pdf, bbox], check=True)
    pagine = ET.parse(bbox).getroot().iter(XHTML + 'page')

    voci, anomalie = [], []
    for pi, pagina in enumerate(pagine):
        pno = PRIMA_PAGINA + pi
        im = Image.open(f'{cartella}/p-{pno:02d}.png').convert('RGB')
        W, H = im.size
        s = W / float(pagina.get('width'))
        px = im.load()
        colonne = [(84, 828), (894, 1647)]
        intestazioni = []
        for blk in pagina.iter(XHTML + 'block'):
            t = ' '.join(w.text for w in blk.iter(XHTML + 'word'))
            if 'Leggi' in t or 'legenda' in t:
                intestazioni.append(int(float(blk.get('yMax')) * s) + 2)
        parole = [((float(w.get('xMin')) + float(w.get('xMax'))) / 2 * s,
                   (float(w.get('yMin')) + float(w.get('yMax'))) / 2 * s,
                   float(w.get('xMin')) * s, w.text) for w in pagina.iter(XHTML + 'word')]

        for ci, (x0, x1) in enumerate(colonne):
            sonde = [x0 + int((x1 - x0) * f) for f in (0.08, 0.3, 0.55, 0.8, 0.95)]
            limiti = []
            for y in range(H):
                if sum(vicino(px[x, y], SEPARATORE, 6) for x in sonde) >= 4 or all(vicino(px[x, y], LIME, 25) for x in sonde):
                    if limiti and y - limiti[-1] <= 3:
                        limiti[-1] = y
                    else:
                        limiti.append(y)
            limiti = [0] + sorted(limiti + intestazioni) + [H]

            for a, b in zip(limiti, limiti[1:]):
                if b - a < 15:
                    continue
                riga = sorted([p for p in parole if x0 - 20 <= p[0] <= x1 and a < p[1] < b], key=lambda p: (round(p[1] / 12), p[2]))
                testo = re.sub(r'\s+', ' ', ' '.join(p[3] for p in riga)).strip()
                if not testo or 'Leggi' in testo or 'legenda' in testo or re.fullmatch(r'[A-Z]|\d+', testo):
                    continue
                conteggi, somma_x = Counter(), Counter()
                for y in range(a + 2, b - 1):
                    for x in range(x1 - 330, x1):
                        p = px[x, y]
                        if p == (255, 255, 255):
                            continue
                        for k, c in COLORI.items():
                            if vicino(p, c):
                                conteggi[k] += 1
                                somma_x[k] += x
                                break
                dest = []
                # icone nell'ordine in cui compaiono, da sinistra a destra (posizione media:
                # la sfumatura del testo vicino genera qualche pixel grigio sparso)
                for k in sorted(conteggi, key=lambda k: somma_x[k] / conteggi[k]):
                    n = conteggi[k]
                    if n < 300 or (k == 'grigio' and n < 400):
                        continue   # bordi sfumati delle icone vicine
                    dest.append(('territorio' if n > 950 else 'carta') if k == 'grigio' else k)
                if not dest:
                    anomalie.append({'pagina': pno, 'voce': testo, 'problema': 'nessuna icona riconosciuta'})
                voce = {'voce': testo, 'destinazioni': dest, 'pagina': pno}
                if len(dest) > 1:
                    logica = LOGICHE.get(frozenset(dest))
                    if logica:
                        voce['logica'], voce['nota'] = logica
                    else:
                        anomalie.append({'pagina': pno, 'voce': testo, 'problema': f'combinazione non prevista {dest}'})
                voci.append(voce)
    return voci, anomalie


def chiave_ordinamento(v):
    t = unicodedata.normalize('NFKD', v['voce'].lower())
    return ''.join(c for c in t if not unicodedata.combining(c))


if __name__ == '__main__':
    pdf, out = sys.argv[1], sys.argv[2]
    with tempfile.TemporaryDirectory() as tmp:
        voci, anomalie = estrai(pdf, tmp)
    voci.sort(key=chiave_ordinamento)
    dati = {
        'fonte': 'AGESP Busto Arsizio - Dizionario dei rifiuti, ed. gennaio 2024',
        'contatti': {
            'numero_verde': '800 439 040',
            'orari_numero_verde': 'lun-ven 8.30-19.00, sabato 8.30-12.30',
            'cmr': 'Via Arturo Tosi 1, Busto Arsizio',
            'sportello': 'Via Canale 26, Busto Arsizio (lun-ven 8.00-14.00, sabato 8.00-12.00)',
            'email': 'igiene.ambientale@agesp.it',
        },
        'destinazioni': DESTINAZIONI,
        'voci': voci,
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(voci)} voci salvate in {out}')
    print(Counter(d for v in voci for d in v['destinazioni']))
    for a in anomalie:
        print('ANOMALIA', a)
