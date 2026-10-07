# Website CO2CirculAir

De website op https://co2circulair.com.

- `bron/` bevat alle tekst, per pagina een bestand. Hier worden teksten aangepast.
- `bron/sjablonen/` bevat de opmaak van elke pagina.
- `bouw.py` maakt uit de bron de pagina's in `site/`.
- `site/` is wat er online staat. Netlify publiceert deze map zodra er een nieuwe versie op `main` staat.

Pas nooit iets direct in `site/*.html` aan: dat wordt bij de volgende bouw overschreven. Zie `CLAUDE.md` voor de werkwijze.

Wijzigingen gaan via een voorbeeldversie en hooguit één keer per dag live; zie `CLAUDE.md`.
