# Website CO2CirculAir

De website op https://co2circulair.com.

- `bron/` bevat alle tekst, per pagina een bestand. Hier worden teksten aangepast.
- `bron/sjablonen/` bevat de opmaak van elke pagina.
- `bouw.py` maakt uit de bron de pagina's in `site/`.
- `site/` is wat er online staat. Wijzigingen worden klaargezet op `main` (voorbeeld: https://main--smart-dac.netlify.app). Elke dag om 17.00 uur zet GitHub ze, als er iets veranderd is, door naar `live`; Netlify publiceert `live` op co2circulair.com. Zie `.github/workflows/publiceer.yml`.

Pas nooit iets direct in `site/*.html` aan: dat wordt bij de volgende bouw overschreven. Zie `CLAUDE.md` voor de werkwijze.

