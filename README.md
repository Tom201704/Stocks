# QQQ gegen den 200-Tage-Schnitt — öffentliche Seite

Eine Seite, die sagt, ob QQQ über oder unter seinem 200-Tage-Schnitt steht und
um wie viel Prozent. Gedacht fürs Handy, ohne Anmeldung, ohne Depotdaten.

```
index.html     die Seite — liest daten.json daneben, rechnet selbst nichts
update.py      holt Yahoo, rechnet den Schnitt, schreibt daten.json (nur stdlib)
workflow.yml   nach .github/workflows/update.yml kopieren
daten.json     wird erzeugt; die hier liegende ist ein echter Probelauf
```

## ⚠ Warum der Browser die Daten nicht selbst holt

Yahoo schickt **keinen `Access-Control-Allow-Origin`-Header**. Eine Seite auf
`github.io` darf `query1.finance.yahoo.com` deshalb nicht abrufen — der
Browser blockt die Antwort, bevor sie ankommt. Die Alternative wäre ein
öffentlicher CORS-Proxy (`allorigins`, `corsproxy.io`): eine fremde Partei
zwischen Datenquelle und Anzeige, die ausfallen kann, ohne dass es auffällt,
und die sich bei Ausfall nicht von „nichts passiert" unterscheiden lässt.

Deshalb holt **GitHub Actions** die Daten — serverseitig gibt es kein CORS —
und committet `daten.json` ins Repo. Die Seite liest nur ihre eigene Datei,
gleiche Herkunft, immer erlaubt.

## ⚠ Nur der SMA200 entscheidet

Seit 07.11.2026 zeigt die Seite auch den **50-** und den **100-Tage-Schnitt** —
als Kontext, nicht als zweites Signal. Deshalb stehen sie in `daten.json` in
einem eigenen Feld `neben_smas` und nicht neben `sma` auf gleicher Höhe, und
deshalb sind sie in der Anzeige **neutral gefärbt**: grün/rot wie oben würde
eine zweite Ampel bauen, die es nicht gibt.

- **SMA100 als Marktfilter** ist über fünf Regime gemessen deutlich schlechter
  (8.6/6.3/6.9 % gegen 10.9/10.4/9.7 %) — der kürzere Schnitt reagiert zu
  schnell.
- **„Kaufen auch wenn SMA50 über SMA200"** wurde am 07.11.2026 verworfen:
  Calmar 0.98 → 0.62, Rückgang in **0 von 5** Fenstern besser.

Im Diagramm trägt jede Linie ihre **Beschriftung am rechten Ende** und ein
eigenes Strichmuster; die Identität hängt also nicht an der Farbe. Der SMA200
ist der dickste der drei — drei gleich starke Linien wären drei gleichwertige
Signale.

## ⚠ Tagesschluss, nicht live — und das ist Absicht

`run_all._markt_lage` und `backtest.markt_ok_roh` entscheiden beide aus der
letzten **fertigen Tagesbar**. Ein laufender Handelstag ist kein Schlusskurs;
eine Seite, die intraday hin- und herspringt, zeigte ein Signal, auf das man
nicht handeln kann — genau der Look-ahead, der im Backtest am 09.08. und
06.11.2026 je zwei Tage gekostet hat. `update.py` verwirft eine unfertige Bar
ausdrücklich und schreibt ins JSON, ob sie verworfen wurde.

## Einrichten

1. Neues, **öffentliches** Repo anlegen, z. B. `qqq-wacht`.
2. `index.html` und `update.py` ins Wurzelverzeichnis legen.
3. `workflow.yml` nach `.github/workflows/update.yml` kopieren.
4. Einmal von Hand: `python update.py` → `daten.json` entsteht, mit committen.
   (Ohne diesen Schritt zeigt die Seite bis zum ersten Action-Lauf „Keine
   Daten" — richtig, aber unnötig.)
5. *Settings → Pages → Build and deployment → Deploy from a branch →
   `main` / `root`.* Nach ein bis zwei Minuten liegt sie unter
   `https://<name>.github.io/qqq-wacht/`.
6. *Actions → QQQ gegen SMA200 → Run workflow* einmal auslösen und prüfen,
   dass der Commit kommt.
7. Auf dem iPhone in Safari öffnen → Teilen → **Zum Home-Bildschirm**.

## Was die Seite nicht kann

- **Sie schickt keine Benachrichtigung.** Eine Webseite kann nicht von selbst
  aufs Handy pushen, ohne dass sie offen ist. Dafür braucht es einen Dienst
  (IBKR-Preisalarm auf der SMA-Höhe, ntfy/Pushover aus einem lokalen Job).
- **Sie ist öffentlich.** Deshalb steht hier nur QQQ gegen seinen Schnitt —
  keine Positionen, keine Beträge, nichts Identifizierendes.

## Vergleich mit dem Dashboard

Gegengerechnet am 07.11.2026: Yahoo-SMA200 **680.89**, der IBKR-basierte Wert
in `master_portfolio.json` **680.90** — auf den Cent gleich. Der *Schlusskurs*
kann abweichen (Yahoo 656.10 gegen 658.00 im Dashboard), weil das Dashboard den
letzten Preis zum Laufzeitpunkt führt, nicht die amtliche Schlussbar. Nahe an
der Linie können beide Seiten deshalb verschiedene Vorzeichen zeigen; maßgeblich
ist `run_all`.

## Selbst testen

```
QQQ_ROH=/pfad/zu/gespeicherter_yahoo_antwort.json python update.py
```

`QQQ_ROH` liest eine gespeicherte Yahoo-Antwort statt zu holen — für Tests und
für Rechner ohne brauchbaren Zertifikatsspeicher. In Actions nie gesetzt.
