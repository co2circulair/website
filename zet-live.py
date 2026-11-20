#!/usr/bin/env python3
"""Zet een conceptpagina (of een bijgewerkte versie ervan) klaar voor de live site.

    python3 zet-live.py <pagina>                 # bv. markets, legislation
    python3 zet-live.py <pagina> --zonder-lege   # alinea's die nog [tussen haken] staan weglaten

Draai op de branch concept, bijgewerkt (git pull). Het script:
1. ruimt de pagina op in de conceptversie: geen gele conceptbalk, geen noindex, geen grijze notities
   voor Berno; bij Legislation stopt het tonen van voorstellen (toon_voorstellen: false);
2. zet de pagina in het menu en de voettekst van alle pagina's (vóór Team);
3. bouwt en commit dat op concept;
4. maakt vanaf origin/main een branch live-<pagina>-<datum> met precies dezelfde bestanden en bouwt;
5. vertelt wat Claude daarna doet: beide branches pushen, pull request naar main, "zet live".

Omdat main en concept daarna dezelfde bestanden hebben, botst het automatisch bijhouden niet.
Werkregels: CLAUDE.md, "Conceptpagina's".
"""
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BRON = ROOT / "bron"
SJAB = BRON / "sjablonen"
HAAK = re.compile(r"^\[[^\]]*\]$")


def git(*args, check=True):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"git {' '.join(args)} mislukte:\n{r.stderr}")
    return r.stdout.strip()


def bouw():
    for cmd in (["python3", "bouw.py", "build"], ["python3", "bouw.py", "check"]):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if r.returncode or "VERSCHILT" in r.stdout:
            sys.exit(f"{' '.join(cmd)} mislukte:\n{r.stdout}\n{r.stderr}")


def lees_bron(pagina):
    tekst = (BRON / f"{pagina}.md").read_text(encoding="utf-8")
    blokken = re.split(r"^## (\S+)\n", tekst, flags=re.M)
    return tekst, {blokken[i]: blokken[i + 1].strip() for i in range(1, len(blokken), 2)}


def haal_sleutels_weg(pagina, sleutels):
    tekst = (BRON / f"{pagina}.md").read_text(encoding="utf-8")
    for k in sleutels:
        tekst = re.sub(rf"^## {re.escape(k)}\n.*?(?=^## |\Z)", "", tekst, flags=re.M | re.S)
    (BRON / f"{pagina}.md").write_text(tekst.rstrip("\n") + "\n", encoding="utf-8")


def menunaam(waarden):
    return waarden.get("head.title.1", "").split("|")[0].strip()


def ruim_op(pagina, zonder_lege):
    fname = f"{pagina if pagina != 'home' else 'index'}.html"
    sjab = SJAB / fname
    s = sjab.read_text(encoding="utf-8")
    _, waarden = lees_bron(pagina)

    # 1. notities voor Berno (class="placeholder") gaan weg, met hun sleutels
    notities = re.findall(r'^\s*<p class="placeholder">\{\{([^}]+)\}\}</p>\n', s, flags=re.M)
    s = re.sub(r'^\s*<p class="placeholder">\{\{[^}]+\}\}</p>\n', "", s, flags=re.M)
    # 2. tekst die nog tussen haken staat
    leeg = [k for k, v in waarden.items() if HAAK.match(v) and k not in notities]
    if leeg and not zonder_lege:
        print("Deze teksten staan nog tussen haken en kunnen zo niet live:")
        for k in leeg:
            print(f"  {k}: {waarden[k]}")
        sys.exit("Vul ze in, of draai opnieuw met --zonder-lege om die alinea's weg te laten.")
    for k in leeg:
        regel = re.compile(rf"^\s*<(\w+)[^>]*>\{{\{{{re.escape(k)}\}}\}}</\1>\n", re.M)
        if not regel.search(s):
            sys.exit(f"{k} staat niet op een eigen regel in het sjabloon; dit kan het script niet weglaten. Vraag het Andrea.")
        s = regel.sub("", s)
    # 3. conceptkenmerken
    s = s.replace('<link rel="stylesheet" href="css/concept.css">\n', "")
    s = s.replace('<meta name="robots" content="noindex, nofollow">\n', "")
    s = re.sub(r'^\s*<div class="concept-banner">.*</div>\n', "", s, flags=re.M)
    sjab.write_text(s, encoding="utf-8")
    haal_sleutels_weg(pagina, notities + leeg)
    return fname, menunaam(waarden)


def zet_in_menu(fname, naam):
    """Menu-item vóór Team in navigatie en voettekst van elk sjabloon; op de eigen pagina aria-current."""
    for sjab in sorted(SJAB.glob("*.html")):
        s = sjab.read_text(encoding="utf-8")
        if f'href="{fname}"' in s:
            continue
        def item(m):
            eigen = sjab.name == fname and m.start() < s.find("<footer")
            huidig = ' aria-current="page"' if eigen else ""
            return f'{m.group(1)}<li><a href="{fname}"{huidig}>{naam}</a></li>\n{m.group(0)}'
        nieuw = re.sub(r'^(\s*)<li><a href="team\.html"', item, s, flags=re.M)
        if nieuw == s:
            sys.exit(f"Geen Team-item gevonden in {sjab.name}; menu niet aangepast. Vraag het Andrea.")
        sjab.write_text(nieuw, encoding="utf-8")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit(__doc__)
    pagina = args[0]
    if git("rev-parse", "--abbrev-ref", "HEAD") != "concept":
        sys.exit("Draai dit op de branch concept (git switch concept, git pull).")
    if git("status", "--porcelain"):
        sys.exit("Er staan nog niet-opgeslagen wijzigingen; eerst committen of terugzetten.")
    if not (BRON / f"{pagina}.md").exists():
        sys.exit(f"Geen pagina {pagina} in bron/.")

    # 1-3: conceptversie opruimen en bouwen
    fname, naam = ruim_op(pagina, "--zonder-lege" in sys.argv)
    zet_in_menu(fname, naam)
    extra = []
    if pagina == "legislation":
        data = json.loads((ROOT / "nieuws" / "nieuws.json").read_text(encoding="utf-8"))
        data["toon_voorstellen"] = False
        (ROOT / "nieuws" / "nieuws.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        extra = ["nieuws/nieuws.py", "nieuws/nieuws.json"]
    bouw()
    git("add", "-A")
    if git("status", "--porcelain"):
        git("commit", "-m", f"{naam}: klaar voor de live site (conceptkenmerken weg, in het menu)")

    # 4: dezelfde bestanden op een branch vanaf main
    sjab = SJAB / fname
    s = sjab.read_text(encoding="utf-8")
    css = [f"site/css/{c}" for c in re.findall(r'href="css/([^"]+)"', s)]
    img = [f"site/img/{i}" for i in re.findall(r'src="img/([^"]+)"', s)]
    git("fetch", "origin", "main")
    op_main = set(git("ls-tree", "-r", "--name-only", "origin/main").splitlines())
    sjablonen = [f"bron/sjablonen/{p.name}" for p in SJAB.glob("*.html") if f"bron/sjablonen/{p.name}" in op_main]
    bestanden = sorted(set([f"bron/{pagina}.md", f"bron/sjablonen/{fname}", "bouw.py", "zet-live.py", *sjablonen,
                            *css, *img, *extra]))
    tak = f"live-{pagina}-{dt.date.today().isoformat()}"
    git("switch", "-c", tak, "origin/main")
    git("checkout", "concept", "--", *bestanden)
    bouw()
    git("add", "-u")  # alleen bestanden die main al kent, plus de nieuwe hieronder: geen losse bestanden meenemen
    git("add", "--", *bestanden, f"site/{fname}")
    git("commit", "-m", f"{naam} naar de live site")
    print(f"""Klaar. Twee dingen staan klaar:
- concept: de opgeschoonde pagina, met {naam} in het menu
- {tak}: dezelfde bestanden vanaf main

Nu doen (Claude):
1. git push origin concept
2. git push -u origin {tak}
3. Maak een pull request van {tak} naar main met de titel "{naam} naar de live site".
4. Geef Berno de voorbeeldlink van die pull request: "Zo komt {naam} op de site te staan. Er staat nog niets live."
5. Zegt Berno "zet live": voeg de pull request samen. Om 17.00 uur staat {naam} op co2circulair.com.""")


if __name__ == "__main__":
    main()
