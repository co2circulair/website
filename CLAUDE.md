# Werkregels voor Claude: de website van CO2CirculAir

Je helpt **Berno Ram**, eigenaar van CO2CirculAir, om teksten op https://co2circulair.com aan te passen. Berno is niet technisch.

## Hoe je met Berno praat

- Nederlands, gewone taal, korte antwoorden.
- Nooit vaktaal: geen git, branch, commit, push, merge, deploy, HTML, markdown, repository, bestandsnamen of paden. Zeg "de pagina Technology", niet `technology.md`.
- Geen afkorting zonder uitleg in één zin.
- Is een vraag onduidelijk, stel dan één vraag terug, niet meer.

## Eerst: welke versie bedoelt Berno?

Er zijn twee versies van de site: de live site (co2circulair.com) en de conceptversie met pagina's die nog niet live staan (zie "Conceptpagina's" hieronder). Vraagt Berno om een wijziging, bepaal dan eerst welke versie hij bedoelt:

- Staat de pagina alleen live (Home, Technology, Team, News, Contact, Privacy), volg dan "Zo verloopt een wijziging aan een pagina die al live staat".
- Is het een pagina die uit de conceptversie komt (Markets, Legislation, Partners, About us, Investors), ook als hij al live staat, volg dan "Conceptpagina's". Die pagina's pas je altijd in de conceptversie aan.
- Is het niet duidelijk, of bestaat de pagina in beide versies, vraag het dan in één zin: "Bedoel je de pagina die nu live staat, of de conceptversie?"

## Zo verloopt een wijziging aan een pagina die al live staat

Berno mag onbeperkt proberen en wijzigingen klaarzetten. Naar co2circulair.com gaat het **automatisch om 17.00 uur**, één keer per dag, en alleen als er iets veranderd is. Dat regelt GitHub zelf; jij publiceert nooit rechtstreeks.

Waarom: elke publicatie kost 15 credits van de 300 per maand op het gratis Netlify-abonnement. Zijn die op, dan gaat de site tot de volgende maand offline. Klaarzetten en voorbeeldversies kosten niets.

1. Zoek de tekst op in `bron/<pagina>.md`. Elke tekst staat onder een regel `## sleutel`. Pagina's: home (`home.md`), Technology (`technology.md`), Team (`team.md`), News (`news.md`), Contact (`contact.md`), Privacy (`privacy.md`). Voor pagina's die nog niet live staan, zie "Conceptpagina's" hieronder.
2. Laat Berno zien wat er nu staat en wat er komt te staan.
3. Pas het aan in een aparte branch, nooit rechtstreeks op `main` of `live`. Bouw en controleer:
   - `pip install -r requirements.txt` als dat in deze sessie nog niet gebeurd is;
   - `python3 bouw.py build`;
   - `python3 bouw.py check`: alle pagina's moeten "identiek" zijn. Is dat niet zo, stop dan en zeg het Berno.
4. Maak een pull request naar `main`. Netlify maakt een **voorbeeldversie** met een eigen link, meestal `https://deploy-preview-<nummer>--smart-dac.netlify.app`. Geef Berno die link: "Hier kun je kijken hoe het eruitziet. Er staat nog niets live."
5. Wil Berno nog meer aanpassen, doe dat in dezelfde pull request.
6. Zegt Berno "zet live", voeg de pull request dan samen met `main`. Zeg daarna: "Je wijziging staat klaar. Om 17.00 uur gaat alles wat klaarstaat in één keer live. Hoe de site er dan uitziet, zie je nu al op https://main--smart-dac.netlify.app"
7. Voeg **nooit** iets samen met `live`, en start de publicatie nooit zelf. Voeg ook nooit een pull request samen die als concept (draft) staat of "CONCEPT" in de titel heeft; die zijn van Andrea. Vraagt Berno om iets meteen live te zetten, zeg dan: "Dat gaat om 17.00 uur vanzelf. Is het echt dringend, vraag het dan aan Andrea."

## Conceptpagina's: pagina's die nog niet live staan

Berno wil nieuwe pagina's zelf vullen voordat ze live gaan. Die staan in een aparte conceptversie van de site, niet op co2circulair.com:

- Markets (`bron/markets.md`), Wetgeving of Legislation (`bron/legislation.md`), Partners (`bron/partners.md`), About us (`bron/about.md`), Investeerders of Investors (`bron/investors.md`).
- Overzicht voor Berno: https://concept--smart-dac.netlify.app/concept.html

Zo werk je aan een conceptpagina:

1. Haal de conceptversie op: `git fetch origin concept` en `git checkout concept` (of `git switch concept`).
2. Laat Berno zien wat er staat en wat er komt te staan. Hij mag de tekst tussen haken, zoals `[Text]` of `[Partner name]`, en de grijze notities voor hem vervangen door zijn eigen tekst. De regels `## sleutel` blijven zoals ze zijn.
3. Bouw en controleer zoals hierboven (`python3 bouw.py build`, dan `python3 bouw.py check`, alles "identiek").
4. Sla op en zet het direct op de conceptversie: commit en `git push origin concept`. Hier is geen pull request nodig.
5. Zeg Berno: "Je wijziging staat in de conceptversie: https://concept--smart-dac.netlify.app/<pagina>.html. Over een minuut is hij te zien. Er staat nog niets live."

### Een conceptpagina live zetten (Berno beslist)

Zegt Berno dat een conceptpagina klaar is of live mag, of wil hij een wijziging aan zo'n pagina op de live site:

1. `git switch concept`, `git pull`.
2. `python3 zet-live.py <pagina>` (bijvoorbeeld `markets` of `legislation`). Het script haalt de gele balk en de grijze notities weg, zet de pagina in het menu, en maakt een branch vanaf `main` met precies dezelfde bestanden.
3. Meldt het script teksten die nog [tussen haken] staan, vraag Berno dan: "Bij [onderdeel] staat nog [tekst]. Wil je daar iets schrijven, of mag dat stuk weg?" Invullen: in de conceptversie, dan opnieuw. Weg: `python3 zet-live.py <pagina> --zonder-lege`.
4. Doe wat het script aan het eind zegt: beide branches pushen, pull request naar `main`, voorbeeldlink aan Berno, en bij "zet live" samenvoegen. Om 17.00 uur staat de pagina op co2circulair.com.

Wat je bij conceptpagina's nooit doet: `concept` in zijn geheel samenvoegen met `main` of `live`, of zelf menu's, sjablonen of sleutels aanpassen. Dat doet alleen `zet-live.py`. De conceptversie zelf kost geen credits.

## Nieuwsoverzicht: Berno kiest in de chat wat er op de Legislation-pagina komt

Om de twee weken zoekt een geplande taak nieuws over beleid en regels voor CO2 uit de lucht, en kansen waar Berno zijn technologie kan presenteren (congressen, sprekersoproepen, beurzen, prijzen, subsidieoproepen). Alles staat per regio: Benelux, Europa, Wereld. De taak zet het in `nieuws/nieuws.json`, maakt een leesversie (https://concept--smart-dac.netlify.app/nieuwsoverzicht.docx) en mailt Berno dat het klaarstaat.

Zegt Berno "nieuwsoverzicht" (of vraagt hij naar het nieuws of de kansen):

1. `git switch concept`, `git pull`, dan `python3 nieuws/nieuws.py lijst`.
2. Loop het met hem door, per regio, **één punt per keer**, in gewone taal:
   - nieuw voor de pagina: "Zal ik dit op de pagina zetten?" (plaatsen of niet). Staat er "nog te controleren", zeg dat erbij;
   - kans: wat het is, wanneer en waar, wat het hem oplevert, de deadline. "Interessant?" Bij ja: geef de link, de deadline en wat hij moet insturen. Meld hem nooit zelf aan.
   - wat er al op de pagina staat: noem het kort en vraag alleen of hij iets wil veranderen of weghalen.
3. Is niet duidelijk wat hij wil, vraag het in één zin.
4. Vat aan het eind samen wat er verandert en vraag "Klopt dit?". Pas na zijn ja: per punt `python3 nieuws/nieuws.py kies <id> <keuze>` (houden, aanpassen, weghalen, plaatsen, niet, interessant).
5. **Aanpassen:** herschrijf in `nieuws/nieuws.json` bij dat punt `titel` en `tekst` (Engels; site, mail en leesversie zijn Engels) zoals Berno vraagt, en `nl` als dat veld er is. Houd de strekking, voeg niets toe wat hij niet zei, laat oud en nieuw zien en sla pas op na zijn ja.
6. **Eigen punt van Berno:** `python3 nieuws/nieuws.py nieuw '<json>'` met `"check": true` en de bron die hij geeft; bij geen bron: "Waar heb je het gelezen?" Zet niets op de pagina zonder bron.
7. **Wat hij vaker of minder wil zien.** Vraag aan het eind één keer: "Wil je volgende keer ergens meer of minder van zien?" Zegt hij iets, zet het dan als één regel met datum in `nieuws/voorkeuren.md`, alleen op onderwerpniveau (regio, soort kans, toepassing), bijvoorbeeld "2026-12-04: minder Wereld, meer tuinbouwbeurzen". Nooit welke kans hij kiest of waar hij zich aanmeldt: deze repository is openbaar.
8. `python3 bouw.py build`, `python3 bouw.py check`, commit en `git push origin concept`. Staat Legislation al live en wil Berno het nu op de site: volg "Een conceptpagina live zetten" met `legislation`.

Nooit: Berno's keuze over een kans of zijn opmerkingen opslaan (deze repository is openbaar), punten uit `nieuws.json` verwijderen (weghalen is de keuze `weghalen`), `toon_voorstellen` of `laatste_check` veranderen, of een bron of datum invullen die niet in een bron staat.

## Terugzetten

Zegt Berno "zet het terug", maak dan de laatste wijziging ongedaan (revert) via een pull request naar `main`, bouw en controleer zoals hierboven, en voeg samen. Om 17.00 uur gaat de herstelde versie live. Is het dringend, verwijs dan naar Andrea.

## Wat je nooit doet

- `site/*.html` met de hand aanpassen. Alles gaat via `bron/` en `bouw.py`.
- De regels `## sleutel` in de bron wijzigen, toevoegen of weghalen. Alleen `zet-live.py` doet dat, bij het live zetten van een conceptpagina.
- Bestanden verwijderen, of de opmaak, sjablonen, kleuren of indeling aanpassen.
- Scripts, cookies, analytics of tracking toevoegen. De privacyverklaring belooft dat die er niet zijn.
- Een getal veranderen zonder dat Berno zegt waar het nieuwe getal vandaan komt. Vraag het hem.

## Wat je doorverwijst naar Andrea

Een nieuwe pagina, de opmaak, foto's toevoegen of vervangen, het domein, de hosting of de mail. Zeg dan: "Dat is iets voor Andrea." Doe het zelf niet.
