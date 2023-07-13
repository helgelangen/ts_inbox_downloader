# ts_inbox_downloader
Script for å laste ned personlige meldinger fra terrengsykkelforumet

## Systemkrav
For å bruke dette scriptet trenger du:
* Python versjon 3.8 eller nyere. Det anbefales å laste ned siste stabile versjon som er kompatibelt med ditt operativsystem.
    * For Windows kan du laste ned Python herfra: https://www.python.org/downloads/windows/
    * For MacOs anbefales det å bruke Homebrew for å installere/oppgradere Python. Alternativt kan man finne det her: https://www.python.org/downloads/macos/
    * For nyere versjoner av Linux er som oftest en ny nok Python versjon allerede installert. Sjekk med `python --version` evt. `python3 --version`, og bruk pakkeverktøyet for din distribusjon til å oppdatere.
* Python-modulene httpx og BeautifulSoup. Installer dem med pip:
```
python -m pip install httpx bs4
```
(bytt ut `python` med `python3` dersom det er kommandoen du bruker for å kjøre python 3 på ditt system)

## Laste ned dette scriptet
Du kan laste ned dette scriptet på to måter:
1. Klon repositoriet:
```
git clone https://github.com/helgelangen/ts_inbox_downloader.git
cd ts_inbox_downloader
git submodule update --init
```
2. Last ned siste release (Se under menyen 'Releases' til høyre)

## Bruke scriptet

### Legge til innloggingsinformasjon
For å ta i bruk scriptet må du oppdatere filen secret.json med innloggingsinformasjon slik at scriptet skal kunne logge seg inn på terrengsykkelforumet som deg.
Secret-filen inneholder ikke ditt brukernavn og passord i klartekst, men en 256-bits hash. Du bør allikevel ikke dele denne filen med noen etter at du har lagt inn din informasjon, da alle som har denne filen vil kunne logge inn på din konto på forumet.

Du må først finne tre forskjellige verdier. Alle disse ligger lagret i informasjonskapsler satt av domenet terrengsykkelforumet.no. Du trenger informasjonen fra disse cookiene:
* terrubbt_myid
* terrubbt_hash
* terrubbt_mysess

Det er flere måter å finne denne informasjonen på. Før du begynner, anbefales det å logge ut fra forumet og så inn igjen slik at informasjonen er oppdatert.

For Firefox kan man finne alle cookies forumet har lagret på denne måten:
1. Gå inn på terrengsykkelforumet.no
2. Høyreklikk hvor som helst på siden og trykk 'inspect'
3. I konsollen som dukker opp, gå til 'Storage', og under 'Cookies' velg 'https://www.terrengsykkelforumet.no'
4. Åpne secret.json i en teksteditor
5. Finn de tre cookiene med navn som angitt ovenfor, og erstatt dummy-verdiene i secret.json med disse verdiene
6. Lagre filen

### Kjøre scriptet
Nå er du klar til å kjøre scriptet. Åpne et terminalvindu, naviger til mappen der scriptet ligger lagret, og kjør kommandoen nedenfor:
```
python fetch_inbox.py
```
Scriptet vil nå laste ned oversikten over alle meldingstråder i innboksen din, og innholdet i alle meldingstrådene.

- Oversikten over meldingstrådene lagres i mappen fetched_messages med filnavn innbox_XXX.htm, der XXX er sidenummeret
- Innholdet i de enkelte meldingstrådene lagres i mappen fetched_messages/threads med filnavn melding_XXXXXX_YYY.htm, der XXXXXX er id'en til meldingstråden og YYY er siden i den aktuelle meldingstråden
- I tillegg blir innholdet i alle meldingstrådene parset og lagret i json-format i filen inbox.json
- Det blir også lagret en enkel logg i filen inbox_fetchlog.json