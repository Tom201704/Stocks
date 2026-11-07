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
# ⚠ NUR `SMA_N` ENTSCHEIDET. 50 und 100 sind Kontext, kein zweites Signal:
# SMA100 als Marktfilter ist gemessen deutlich schlechter (8.6/6.3/6.9 % gegen
# 10.9/10.4/9.7 % ueber fuenf Regime), und die ODER-Regel mit dem Index-SMA50
# wurde am 07.11.2026 verworfen (Calmar 0.98 -> 0.62, Rueckgang 0/5 Fenster).
# Wer sie hier gleichwertig faerbt, baut eine zweite Ampel, die es nicht gibt.
SMA_NEBEN = [int(x) for x in
             (os.environ.get("QQQ_SMA_NEBEN", "50,100").split(",")) if x.strip()]
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

    def tag(t):
        return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")

    # ⚠ LAUFENDEN HANDELSTAG VERWERFEN — aber nur den WIRKLICH laufenden.
    #
    # Die erste Fassung verglich das Datum der letzten Bar mit HEUTE und warf
    # sie weg, wenn beide gleich waren. Das ist an jedem Werktag nach
    # Boersenschluss FALSCH: die Bar von heute ist dann fertig, und der
    # 22:40-UTC-Lauf haette durchgehend den Schlusskurs von GESTERN
    # veroeffentlicht. Gefunden am 07.11.2026 beim Nachrechnen der
    # Cron-Zeiten, nicht im Betrieb — am Samstag getestet, und samstags ist
    # die letzte Bar die von Freitag, also fiel es nicht auf.
    # ⚠ Es haette vollkommen gesund ausgesehen: gruener Lauf, Commit, Seite
    # ohne Warnung (ein Tag Rueckstand liegt unter der 4-Werktage-Schwelle).
    #
    # Jetzt entscheidet die SITZUNG, nicht der Kalender: unfertig ist die
    # letzte Bar nur, wenn sie auf denselben Tag faellt wie das Ende der
    # aktuellen regulaeren Sitzung UND dieses Ende noch in der Zukunft liegt.
    # Am Wochenende zeigt `currentTradingPeriod` auf die NAECHSTE Sitzung —
    # dann unterscheiden sich die Daten und Freitags Bar bleibt stehen.
    meta = r.get("meta") or {}
    reg = ((meta.get("currentTradingPeriod") or {}).get("regular") or {})
    schluss_ts = reg.get("end")
    letzte_ts = meta.get("regularMarketTime")
    if schluss_ts and letzte_ts:
        unfertig = (tag(bars[-1][0]) == tag(schluss_ts)
                    and int(letzte_ts) < int(schluss_ts))
    else:
        # Rueckfall auf die alte, grobe Regel — aber LAUT, damit niemand
        # glaubt, hier sei die Sitzung geprueft worden.
        print("WARNUNG: currentTradingPeriod/regularMarketTime fehlen, "
              "Rueckfall auf den Datumsvergleich (kann einen Tag hinterherhinken)")
        unfertig = tag(bars[-1][0]) == datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if unfertig:
        laufender_kurs = bars[-1][1]
        bars = bars[:-1]
    else:
        laufender_kurs = None
    if len(bars) < SMA_N:
        raise SystemExit("nach dem Verwerfen der laufenden Bar zu wenig Daten")

    kurs = bars[-1][1]
    sma = sum(c for _, c in bars[-SMA_N:]) / SMA_N
    stand = tag(bars[-1][0])

    def schnitt(n):
        """SMA ueber n Bars, oder None wenn es nicht genug sind.

        ⚠ None, nicht 0 und nicht der Mittelwert ueber weniger Bars. Ein aus
        80 Kursen gerechneter 'SMA100' saehe aus wie eine Messung und waere
        keine — dieselbe Lehre wie `tech_score: 0/2`.
        """
        return (sum(c for _, c in bars[-n:]) / n) if len(bars) >= n else None

    neben = []
    for n in SMA_NEBEN:
        w = schnitt(n)
        neben.append({
            "n": n,
            "sma": round(w, 2) if w is not None else None,
            "ueber": (kurs > w) if w is not None else None,
            "abstand_pct": round((kurs / w - 1) * 100, 2) if w else None,
        })

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
        # ⚠ In einem EIGENEN Feld, nicht neben `sma` auf gleicher Hoehe. Die
        # Struktur soll schon sagen, welcher Schnitt die Regel traegt.
        "neben_smas": neben,
    }

    # ── VORLAEUFIGER STAND WAEHREND DER SITZUNG ───────────────────────────
    # ⚠ AENDERT DEN ZUSTAND NICHT. Entschieden wird aus der letzten fertigen
    # Bar; das hier ist Kontext, wie SMA50 und SMA100. Es steht in einem
    # eigenen Feld und bekommt in der Anzeige keine Ampelfarbe.
    #
    # ⚠ Gerechnet wird der Schnitt, der MORGEN dastuende, wenn heute hier
    # schliesst: die letzten 199 fertigen Schlusskurse plus der laufende.
    # Den laufenden Kurs gegen den Schnitt von gestern zu halten waere eine
    # dritte Zahl, die es nirgends gibt.
    live_px = laufender_kurs or meta.get("regularMarketPrice")
    out["live"] = None
    if unfertig and live_px:
        prov = (sum(c for _, c in bars[-(SMA_N - 1):]) + float(live_px)) / SMA_N
        out["live"] = {
            "kurs": round(float(live_px), 2),
            "sma_wenn_schluss": round(prov, 2),
            "abstand_pct": round((float(live_px) / prov - 1) * 100, 2),
            "ueber": bool(float(live_px) > prov),
            "zeit": (datetime.fromtimestamp(int(letzte_ts), timezone.utc)
                     .strftime("%Y-%m-%dT%H:%M:%SZ") if letzte_ts else None),
        }

    # Verlauf fuer das kleine Diagramm: je Tag Schlusskurs UND der an diesem
    # Tag gueltige Schnitt. ⚠ Der Schnitt muss MITGESCHRIEBEN werden — wer nur
    # Kurse ausliefert und im Browser den Schnitt der sichtbaren Punkte
    # rechnet, zeichnet eine andere Linie als die, ueber die entschieden wird.
    # Dieselbe Regel wie im Dashboard: das Frontend rechnet Kennzahlen nicht
    # nach, es zeigt sie.
    verlauf = []
    for k in range(max(SMA_N, len(bars) - VERLAUF_TAGE), len(bars)):
        punkt = {
            "d": tag(bars[k][0]),
            "c": round(bars[k][1], 2),
            "s": round(sum(c for _, c in bars[k - SMA_N + 1:k + 1]) / SMA_N, 2),
        }
        for n in SMA_NEBEN:
            punkt[f"s{n}"] = (round(sum(c for _, c in bars[k - n + 1:k + 1]) / n, 2)
                              if k + 1 >= n else None)
        verlauf.append(punkt)
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
