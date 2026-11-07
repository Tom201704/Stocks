#!/usr/bin/env python3
"""Holt QQQ bei Yahoo, rechnet den 200-Tage-Schnitt und schreibt daten.json.

Laeuft in GitHub Actions, nicht im Browser. Grund ist CORS: Yahoo schickt
keinen `Access-Control-Allow-Origin`-Header, eine Seite auf github.io kann die
API also nicht selbst abrufen. Ein oeffentlicher CORS-Proxy waere die
Alternative — eine fremde Partei zwischen Datenquelle und Anzeige, die
ausfallen kann, ohne dass es jemandem auffaellt.

⚠ DER SCHLUSSKURS VON GESTERN IST DER RICHTIGE WERT, nicht der von heute.
`run_all._markt_lage` und `backtest.markt_ok_roh` entscheiden beide aus der
letzten FERTIGEN Tagesbar — ein laufender Handelstag ist kein Schlusskurs, und
eine Anzeige, die intraday hin- und herspringt, zeigt ein Signal, auf das man
nicht handeln kann. Genau der Look-ahead, der am 09.08. und 06.11.2026 je
zwei Tage Arbeit gekostet hat. Diese Seite ist deshalb bewusst nur einmal am
Tag aktuell.

Nur Standardbibliothek — in Actions soll nichts installiert werden muessen.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

SYMBOL = os.environ.get("QQQ_SYMBOL", "QQQ")
SMA_N = int(os.environ.get("QQQ_SMA", "200"))
VERLAUF_TAGE = int(os.environ.get("QQQ_VERLAUF", "180"))
ZIEL = os.environ.get("QQQ_ZIEL", os.path.join(os.path.dirname(os.path.abspath(__file__)), "daten.json"))
URL = ("https://query1.finance.yahoo.com/v8/finance/chart/"
       f"{SYMBOL}?range=2y&interval=1d&includePrePost=false")


def hole(url):
    # Yahoo antwortet ohne User-Agent mit 429. Ein generischer Client-Name,
    # keine Mailadresse — die Seite ist oeffentlich.
    req = urllib.request.Request(url, headers={
        "User-Agent": "gwgr-qqq-wacht/1.0 (+github pages)",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    # QQQ_ROH zeigt auf eine gespeicherte Yahoo-Antwort. Nur fuer Tests und
    # fuer Rechner ohne brauchbaren Zertifikatsspeicher — in Actions nie
    # gesetzt, dort wird geholt.
    vorrat = os.environ.get("QQQ_ROH")
    if vorrat:
        with open(vorrat, encoding="utf-8") as f:
            roh = json.load(f)
    else:
        roh = hole(URL)
    res = (roh.get("chart") or {}).get("result") or []
    if not res:
        raise SystemExit(f"Yahoo lieferte kein Ergebnis: {str(roh)[:300]}")
    r = res[0]
    stamps = r.get("timestamp") or []
    closes = ((r.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []

    # ⚠ FEIERTAGE UND LUECKEN KOMMEN ALS null. Wer sie mitzaehlt, rechnet den
    # Schnitt ueber weniger als 200 echte Kurse oder bekommt None in die Summe.
    bars = [(t, c) for t, c in zip(stamps, closes) if c is not None]
    if len(bars) < SMA_N + 1:
        raise SystemExit(f"nur {len(bars)} Bars, fuer SMA{SMA_N} zu wenig")

    # ⚠ LAUFENDEN HANDELSTAG VERWERFEN. Yahoo haengt waehrend der Sitzung eine
    # unfertige Bar mit dem aktuellen Preis an. Erkannt wird sie am Datum: ist
    # die letzte Bar von HEUTE (UTC-Datum des Handelstages), fliegt sie raus.
    heute = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    def tag(t):
        return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
    unfertig = tag(bars[-1][0]) == heute
    if unfertig:
        bars = bars[:-1]
    if len(bars) < SMA_N:
        raise SystemExit("nach dem Verwerfen der laufenden Bar zu wenig Daten")

    kurs = bars[-1][1]
    sma = sum(c for _, c in bars[-SMA_N:]) / SMA_N
    stand = tag(bars[-1][0])

    out = {
        "symbol": SYMBOL,
        "sma_n": SMA_N,
        "kurs": round(kurs, 2),
        "sma": round(sma, 2),
        "ueber": bool(kurs > sma),
        "abstand_pct": round((kurs / sma - 1) * 100, 2),
        "stand": stand,                       # Datum der benutzten Bar
        "geholt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bars": len(bars),
        "laufende_bar_verworfen": unfertig,
        "quelle": "Yahoo Finance, Tagesschlusskurse (unbereinigt)",
    }

    # Verlauf fuer das kleine Diagramm: je Tag Schlusskurs UND der an diesem
    # Tag gueltige Schnitt. ⚠ Der Schnitt muss MITGESCHRIEBEN werden — wer nur
    # Kurse ausliefert und im Browser den Schnitt der sichtbaren Punkte
    # rechnet, zeichnet eine andere Linie als die, ueber die entschieden wird.
    # Dieselbe Regel wie im Dashboard: das Frontend rechnet Kennzahlen nicht
    # nach, es zeigt sie.
    verlauf = []
    for k in range(max(SMA_N, len(bars) - VERLAUF_TAGE), len(bars)):
        verlauf.append({
            "d": tag(bars[k][0]),
            "c": round(bars[k][1], 2),
            "s": round(sum(c for _, c in bars[k - SMA_N + 1:k + 1]) / SMA_N, 2),
        })
    out["verlauf"] = verlauf
    # ⚠ `allow_nan=False`: ein NaN ist kein gueltiges JSON, und der Browser
    # verweigert dann die GANZE Datei. Das hat am 04.11.2026 18 MB unlesbar
    # gemacht und sah von aussen wie "es gab noch nie einen Lauf" aus.
    text = json.dumps(out, indent=1, allow_nan=False)
    with open(ZIEL, "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
