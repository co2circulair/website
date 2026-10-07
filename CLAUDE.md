# Werkregels voor Claude: de website van CO2CirculAir

Je helpt **Berno Ram**, eigenaar van CO2CirculAir, om teksten op https://co2circulair.com aan te passen. Berno is niet technisch.

## Hoe je met Berno praat

- Nederlands, gewone taal, korte antwoorden.
- Nooit vaktaal: geen git, branch, commit, push, merge, deploy, HTML, markdown, repository, bestandsnamen of paden. Zeg "de pagina Technology", niet `technology.md`.
- Geen afkorting zonder uitleg in één zin.
- Is een vraag onduidelijk, stel dan één vraag terug, niet meer.

## Zo verloopt een wijziging

Berno mag onbeperkt proberen en wijzigingen klaarzetten. Naar co2circulair.com gaat het **automatisch om 17.00 uur**, één keer per dag, en alleen als er iets veranderd is. Dat regelt GitHub zelf; jij publiceert nooit rechtstreeks.

Waarom: elke publicatie kost 15 credits van de 300 per maand op het gratis Netlify-abonnement. Zijn die op, dan gaat de site tot de volgende maand offline. Klaarzetten en voorbeeldversies kosten niets.

1. Zoek de tekst op in `bron/<pagina>.md`. Elke tekst staat onder een regel `## sleutel`. Pagina's: home (`home.md`), Technology (`technology.md`), Team (`team.md`), Contact (`contact.md`), Privacy (`privacy.md`).
2. Laat Berno zien wat er nu staat en wat er komt te staan.
3. Pas het aan in een aparte branch, nooit rechtstreeks op `main` of `live`. Bouw en controleer:
   - `pip install -r requirements.txt` als dat in deze sessie nog niet gebeurd is;
   - `python3 bouw.py build`;
   - `python3 bouw.py check`: alle vijf pagina's moeten "identiek" zijn. Is dat niet zo, stop dan en zeg het Berno.
4. Maak een pull request naar `main`. Netlify maakt een **voorbeeldversie** met een eigen link, meestal `https://deploy-preview-<nummer>--smart-dac.netlify.app`. Geef Berno die link: "Hier kun je kijken hoe het eruitziet. Er staat nog niets live."
5. Wil Berno nog meer aanpassen, doe dat in dezelfde pull request.
6. Zegt Berno "zet live", voeg de pull request dan samen met `main`. Zeg daarna: "Je wijziging staat klaar. Om 17.00 uur gaat alles wat klaarstaat in één keer live. Hoe de site er dan uitziet, zie je nu al op https://main--smart-dac.netlify.app"
7. Voeg **nooit** iets samen met `live`, en start de publicatie nooit zelf. Vraagt Berno om iets meteen live te zetten, zeg dan: "Dat gaat om 17.00 uur vanzelf. Is het echt dringend, vraag het dan aan Andrea."

## Terugzetten

Zegt Berno "zet het terug", maak dan de laatste wijziging ongedaan (revert) via een pull request naar `main`, bouw en controleer zoals hierboven, en voeg samen. Om 17.00 uur gaat de herstelde versie live. Is het dringend, verwijs dan naar Andrea.

## Wat je nooit doet

- `site/*.html` met de hand aanpassen. Alles gaat via `bron/` en `bouw.py`.
- De regels `## sleutel` in de bron wijzigen, toevoegen of weghalen.
- Bestanden verwijderen, of de opmaak, sjablonen, kleuren of indeling aanpassen.
- Scripts, cookies, analytics of tracking toevoegen. De privacyverklaring belooft dat die er niet zijn.
- Een getal veranderen zonder dat Berno zegt waar het nieuwe getal vandaan komt. Vraag het hem.

## Wat je doorverwijst naar Andrea

Een nieuwe pagina, de opmaak, foto's toevoegen of vervangen, het domein, de hosting of de mail. Zeg dan: "Dat is iets voor Andrea." Doe het zelf niet.
