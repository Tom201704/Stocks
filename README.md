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

Das Diagramm endet **nicht bei der letzten fertigen Bar**: während der
Sitzung hängt der laufende Kurs als zusätzlicher Punkt an der Kurve, sonst
fehlte genau die Bewegung, wegen der man hinsieht. ⚠ Er ist als
`vorlaeufig: true` markiert, wird als **offener Kreis** gezeichnet und unter
dem Diagramm benannt („der letzte Punkt (○) ist vorläufig") — ein
vorläufiger Punkt, der aussieht wie ein Schlusskurs, ist dieselbe Klasse wie
„PAUSCHAL 2.5 %". Seine Schnitte kommen aus `live` und nicht aus einer
zweiten Rechnung.

Im Diagramm trägt jede Linie ihre **Beschriftung am rechten Ende** und ein
eigenes Strichmuster; die Identität hängt also nicht an der Farbe. Der SMA200
ist der dickste der drei — drei gleich starke Linien wären drei gleichwertige
Signale.

## ⚠ Zwei Zeitpunkte, die leicht verwechselt werden

Ganz oben stehen **beide nebeneinander**:

```
Zuletzt geprüft Sa., 07.11., 20:03 · vor 14 Std  ·  Kurse vom Handelstag 06.11.
```

und während der US-Sitzung zusätzlich, dass der heutige Tag noch läuft:

```
… · Kurse vom Handelstag 06.11., heute läuft noch — $666.00 (−2.19 %, vorläufig)
```

Der linke Teil sagt, ob der Abgleich noch arbeitet; der rechte, wie alt die
Kurse sind. Am Wochenende stehen beide still, aber aus verschiedenen Gründen:
der Cron läuft Mo–Fr, und die letzte Bar ist die von Freitag.

Während der Sitzung zeigt die Karte ausserdem den
**Tagesverlauf** aus den drei Läufen, mit dem Schlusskurs von gestern als
Startpunkt:

```
06.11. Schluss $656.10   ·   17:00 $659.40   ·   20:00 $663.80   ·   21:00 $666.00
```

Drei Punkte sind wenig — aber die Frage während des Tages lautet „in welche
Richtung", und dafür reichen ein Anfang und zwei Zwischenstände.

⚠ **`update.py` liest dafür seine eigene vorige Ausgabe.** Das ist in diesem
Projekt schon einmal schiefgegangen (`_guard_open_orders` las seine eigene
Ausgabe und schützte dadurch nichts). Hier ist es zulässig, weil es ein
**anhängendes Protokoll** ist und keine Prüfung: fällt die alte Datei weg oder
ist sie kaputt, fängt der Verlauf bei null an — verloren gehen nur Punkte.
Ein neuer Handelstag setzt zurück, und derselbe Zeitstempel hängt nicht
zweimal an.

⚠ **Der Zusatz „heute läuft noch" ist nicht Kosmetik.** Ohne ihn liest sich
die Zeile während der Sitzung wie „die Kurse sind einen Tag alt" — der
Unterschied zwischen *einen Tag hinterher* und *heute ist noch nicht fertig*
ist aber genau der, auf den es ankommt. Die Zahl daneben entscheidet nichts;
sie steht zusätzlich in der eigenen Karte unter der Zustandskarte.

`geholt` taugt als Laufzeit, weil `update.py` es bei **jedem** Lauf auf die
aktuelle Uhrzeit setzt — `daten.json` unterscheidet sich damit nach jedem
erfolgreichen Lauf, und der Commit kommt. Scheitert der Lauf, bleibt die alte
Zeit stehen, und ab **drei Tagen** wird die Zeile amber: *„der Abgleich läuft
nicht mehr."* Drei Tage, nicht einer — sonst warnt sie jedes Wochenende, und
eine Warnung, die immer kommt, wird nicht mehr gelesen.

## Drei Läufe am Tag — und was sie bewirken

`workflow.yml` feuert werktags **16:00, 19:00 und 22:40 UTC** (Winterzeit:
17:00, 20:00, 23:40 Schweizer Zeit).

| Lauf | US-Börse | was sich ändert |
|---|---|---|
| 16:00 / 19:00 UTC | **offen** | nur der vorläufige Block `live` |
| 22:40 UTC | geschlossen | der **Zustand** — neue Tagesbar, neuer Schnitt |

- ⚠ **Ohne den vorläufigen Block wären die beiden Zwischenläufe wirkungslos.**
  `update.py` verwirft die laufende Bar; die Datei sähe aus wie am Vorabend,
  der Schritt „Zurückschreiben" fände keine Änderung und committete nichts.
  Ein Workflow, der läuft und nie schreibt, sieht gesund aus und tut nichts.
- ⚠ **Sommerzeit:** GitHub-Cron ist immer UTC. Ende März bis Ende Oktober
  sind das 18:00 und 21:00 Schweizer Zeit. Beide liegen auch dann in der
  Sitzung (US-Schluss dann 20:00 UTC), der Zweck bleibt also — nur die
  Uhrzeit verschiebt sich.
- Der vorläufige Wert **ändert den Zustand nicht** und bekommt keine
  Ampelfarbe. Verglichen wird er gegen den Schnitt, der *morgen* dastünde,
  wenn heute hier schliesst — den laufenden Kurs gegen den Schnitt von
  gestern zu halten wäre eine dritte Zahl, die es nirgends gibt.
- Ist die Datei veraltet, verschwindet er: „jetzt" aus einer vier Tage alten
  Datei wäre eine Lüge.

## ⚠ Der Abendlauf hing einen Tag hinterher (gefunden 07.11.2026)

Die erste Fassung erkannte die laufende Bar am **Datum** („ist sie von
heute?"). Das stimmt während der Sitzung und ist an jedem Werktag **nach**
Börsenschluss falsch: die Bar von heute ist dann fertig, und der 22:40-Lauf
hätte durchgehend den Schlusskurs von **gestern** veröffentlicht.

Aufgefallen ist es nur beim Nachrechnen der Cron-Zeiten — getestet worden war
an einem Samstag, und samstags ist die letzte Bar die von Freitag. ⚠ Es hätte
vollkommen gesund ausgesehen: grüner Workflow, Commit, keine Warnung auf der
Seite (ein Tag Rückstand liegt unter der 4-Werktage-Schwelle).

Jetzt entscheidet die **Sitzung**, nicht der Kalender: unfertig ist die letzte
Bar nur, wenn sie auf denselben Tag fällt wie das Ende der aktuellen regulären
Sitzung *und* dieses Ende noch in der Zukunft liegt. Am Wochenende zeigt
`currentTradingPeriod` auf die nächste Sitzung — dann unterscheiden sich die
Daten und Freitags Bar bleibt stehen. Fehlen die Felder, gibt es den alten
Datumsvergleich zurück, aber mit einer Warnung im Protokoll.

Test: `python Tools/qqq_seite/test_update.py` — 44 Fälle gegen nachgebaute
Yahoo-Antworten, ohne Netz (Sitzung läuft · Sitzung vorbei · Wochenende ·
fehlende Meta-Felder · Lücken).

## ⚠ Die Karte zeigt den aktuellsten Kurs — die REGEL nicht

Seit dem 09.11.2026 steht in der Karte während der US-Sitzung der **laufende
Kurs**, verglichen mit den Schnitten, die sich ergäben, wenn heute auf diesem
Stand schliesst (SMA50, SMA100 **und** SMA200 — alle drei gegen denselben
Kurs, sonst hätte dieselbe Karte zwei Bezugspunkte). Nach Schluss steht dort
die fertige Tagesbar. Welcher Fall gilt, steht an der Kurszeile
(`QQQ Intraday 17:52` gegen `QQQ Schlusskurs`), am `Stand` und als `intraday`
neben der Prozentzahl.

⚠ **Das ist eine Entscheidung der ANZEIGE, nicht der Regel.**
`run_all._markt_lage` und `backtest.markt_ok_roh` entscheiden weiterhin aus der
letzten **fertigen Tagesbar** — ein laufender Handelstag ist kein Schlusskurs,
und genau dieser Look-ahead hat im Backtest am 09.08. und 06.11.2026 je zwei
Tage gekostet. In `daten.json` bleibt deshalb alles getrennt: `kurs`, `sma`,
`ueber` tragen die fertige Bar, der laufende Kurs steht im Block `live`, und
`laufende_bar_verworfen` sagt, ob eine unfertige Bar weggefallen ist.

⚠ **Nahe an der Linie können Seite und `run_all` verschiedene Vorzeichen
zeigen.** Massgeblich ist `run_all`. Steht so in der Fussnote der Seite.

## Gewinn/Verlust gegen den Vortag

Eine eigene Zeile in der Karte, grün/orange: während der Sitzung der laufende
Kurs gegen den letzten Schluss (`live.seit_schluss_pct`), nach Schluss die
fertige Bar gegen die davor (`tag_pct`).

⚠ **„Vortag" ist die vorletzte fertige BAR, nicht „gestern".** Am Montag liegt
das Wochenende dazwischen, nach einem Feiertag zwei Tage. Deshalb stehen
Datum und Bezugskurs in der Beschriftung — eine Prozentzahl ohne ihren
Bezugspunkt ist eine Behauptung.

⚠ Die Farbe gehört hier zur **Zahl**, nicht zur Ampel darüber. Ohne eigene
Beschriftung wären das zwei Aussagen im selben Feld.

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
