#!/usr/bin/env python3
"""Nieuwsoverzicht voor de Legislation-pagina: beleid en kansen per regio (Benelux, Europe, World).

Voor Berno's Claude (kiezen in de chat):
    python3 nieuws/nieuws.py lijst                     # alles wat een keuze nodig heeft, per regio
    python3 nieuws/nieuws.py kies <id> <keuze>         # houden | aanpassen | weghalen | plaatsen | niet | interessant
    python3 bouw.py build                              # zet de punten op de pagina

Voor de geplande taak (om de twee weken):
    python3 nieuws/nieuws.py moet-check                # exitcode 0: check nodig; 1: minder dan 10 dagen geleden
    python3 nieuws/nieuws.py nieuw '<json>'            # beleidspunt als voorstel toevoegen (velden: zie NIEUW_VELDEN)
    python3 nieuws/nieuws.py kans '<json>'             # kans om te presenteren toevoegen (velden: zie KANS_VELDEN)
    python3 nieuws/nieuws.py klaar                     # check afgerond: datum vastleggen
    python3 nieuws/nieuws.py word --site               # leesversie naar site/nieuwsoverzicht.docx
    python3 nieuws/nieuws.py mail                      # onderwerp en tekst van de mail aan Berno

Werkwijze: CLAUDE.md, sectie "Nieuwsoverzicht". De repository is openbaar: geen opmerkingen of
keuzes van Berno over kansen opslaan.
"""
import datetime as dt
import html
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

HIER = Path(__file__).resolve().parent
ROOT = HIER.parent
DATA = HIER / "nieuws.json"
EDITIES = HIER / "edities"
SITE_DOCX = ROOT / "site" / "nieuwsoverzicht.docx"
DOCX_URL = "https://concept--smart-dac.netlify.app/nieuwsoverzicht.docx"

REGIO = ["Benelux", "Europe", "World"]
REGIO_NL = {"Benelux": "Benelux", "Europe": "Europa", "World": "Wereld"}
BLOK = {"fuels", "ets", "benelux", "wereld", "tijdlijn"}
RECHT = {"In force", "Proposal"}
TOEPASSING = {"Greenhouses", "Fuels", "Chemicals & materials", "Food & beverage", "Storage", "All uses"}
NIEUW_VELDEN = ["id", "blok", "regio", "titel", "tekst", "nl", "rechtskracht", "toepassing", "bron"]  # plus datum, check
KANS_VELDEN = ["id", "regio", "titel", "wat", "waarom", "datum", "plaats", "link", "bron"]  # plus deadline
# Taal: titel en plaats in het Engels (komen in de mail aan Berno), wat en waarom in het Nederlands (chat en leesversie).
KEUZES = {
    "op-pagina": {"houden": None, "aanpassen": None, "weghalen": "weg"},
    "voorstel": {"plaatsen": "op-pagina", "niet": "weg"},
}
MAAND_NL = "januari februari maart april mei juni juli augustus september oktober november december".split()
MAAND_EN = "January February March April May June July August September October November December".split()
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
PLACEHOLDER = "Klik en typ hier"


def datum_nl(s):
    d = dt.date.fromisoformat(s)
    return f"{d.day} {MAAND_NL[d.month - 1]} {d.year}"


def datum_en(s):
    d = dt.date.fromisoformat(s)
    return f"{d.day} {MAAND_EN[d.month - 1]} {d.year}"


def laad():
    return json.loads(DATA.read_text(encoding="utf-8"))


def bewaar(data):
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def vandaag():
    return dt.date.today().isoformat()


def bron_tekst(b):
    return b["tekst"] + (f", {b['extra']}" if b.get("extra") else "")


def open_kansen(data):
    """Kansen die nog niet voorbij zijn (deadline, of anders de datum zelf)."""
    nu = vandaag()
    return [k for k in data.get("kansen", []) if (k.get("deadline") or k["datum"]) >= nu and k["status"] != "weg"]


def per_regio(items):
    return [(r, [i for i in items if i["regio"] == r]) for r in REGIO]


# ---------- pagina: wordt aangeroepen door bouw.py ----------

def _tags(p):
    klasse = {"In force": "inforce", "Proposal": "proposal"}[p["rechtskracht"]]
    t = [f'<span class="tag {klasse}">{p["rechtskracht"]}</span>', f'<span class="tag region">{p["regio"]}</span>']
    t += [f'<span class="tag">{html.escape(a)}</span>' for a in p["toepassing"]]
    if p.get("check"):
        t.append('<span class="tag check">Check</span>')
    return '<div class="tags">' + "".join(t) + "</div>"


def _bron(p):
    b = p["bron"]
    naam = html.escape(b["tekst"])
    if b.get("url"):
        naam = f'<a href="{html.escape(b["url"])}">{naam}</a>'
    extra = f", {html.escape(b['extra'])}" if b.get("extra") else ""
    return f'<p class="source">Source: {naam}{extra}</p>'


def _kaart(p):
    merk = '<span class="new-mark">Proposed, not yet chosen</span>' if p["status"] == "voorstel" else ""
    datum = f'<time>{datum_en(p["datum"])}</time>' if p.get("datum") else ""
    return (f'<li>{merk}{datum}{_tags(p)}<h3>{html.escape(p["titel"])}</h3>'
            f'<p>{html.escape(p["tekst"])}</p>{_bron(p)}</li>')


LEGENDA = ('<div class="legend"><span class="tag inforce">In force</span> applies now '
           '<span class="tag proposal">Proposal</span> not yet law '
           '<span class="tag region">Benelux</span> <span class="tag region">Europe</span> '
           '<span class="tag region">World</span> where it applies '
           '<span class="tag">Greenhouses</span> the use it concerns</div>')


def invullen(pagina_html):
    """Vervangt <!--NIEUWS:blok--> door de punten van dat blok. 'wereld' wordt een eigen sectie, alleen als er iets in staat."""
    data = laad()
    concept = data.get("toon_voorstellen", False)
    zicht = {"op-pagina", "voorstel"} if concept else {"op-pagina"}

    def punten(blok):
        return [p for p in data["punten"] if p["blok"] == blok and p["status"] in zicht]

    def blok(m):
        naam = m.group(1)
        if naam == "legenda":
            return LEGENDA
        if naam == "download":
            return (f'<p class="source">Reading version of this edition for printing: '
                    f'<a href="nieuwsoverzicht.docx">nieuwsoverzicht.docx</a></p>') if concept else ""
        lijst = punten(naam)
        if naam == "tijdlijn":
            lijst.sort(key=lambda p: p["datum"], reverse=True)
            return '<ol class="timeline">' + "".join(_kaart(p) for p in lijst) + "</ol>" if lijst else ""
        kaarten = '<ul class="positions">' + "".join(_kaart(p) for p in lijst) + "</ul>" if lijst else ""
        if naam == "wereld":
            if not lijst:
                return ""
            return ('<section class="section"><div class="container"><span class="kicker">World</span>'
                    '<h2>Elsewhere in the world.</h2>' + kaarten + "</div></section>")
        return kaarten

    return re.sub(r"<!--NIEUWS:(\w+)-->", blok, pagina_html)


# ---------- keuzes in de chat ----------

def lijst():
    data = laad()
    pag = [p for p in data["punten"] if p["status"] == "op-pagina"]
    voor = [p for p in data["punten"] if p["status"] == "voorstel"]
    kansen = [k for k in open_kansen(data) if k["status"] == "nieuw"]
    print(f"Laatste check: {datum_nl(data['laatste_check']) if data.get('laatste_check') else 'nog niet gedaan'}")
    for r, _ in per_regio(pag + voor + kansen):
        rv = [p for p in voor if p["regio"] == r]
        rk = [k for k in kansen if k["regio"] == r]
        if not (rv or rk):
            continue
        print(f"\n== {REGIO_NL[r]} ==")
        for p in rv:
            print(f"- NIEUW VOOR DE PAGINA [{p['id']}] {p['titel']}" + (f" ({datum_nl(p['datum'])})" if p.get("datum") else ""))
            print(f"    {p['nl']}")
            print(f"    {p['rechtskracht']} · {', '.join(p['toepassing'])} · Bron: {bron_tekst(p['bron'])}"
                  + ("  [nog te controleren in de oorspronkelijke tekst]" if p.get("check") else ""))
            print("    Keuze: plaatsen of niet")
        for k in rk:
            print(f"- KANS [{k['id']}] {k['titel']}, {datum_nl(k['datum'])}, {k['plaats']}")
            print(f"    {k['wat']} Wat het oplevert: {k['waarom']}")
            if k.get("deadline"):
                print(f"    Aanmelden vóór {datum_nl(k['deadline'])}")
            print(f"    Link: {k['link']}   Bron: {k['bron']}")
            print("    Keuze: interessant of niet")
    print("\n== Wat er nu op de pagina staat (houden, aanpassen of weghalen; alleen vragen als Berno iets wil veranderen) ==")
    for p in pag:
        print(f"- [{p['id']}] {REGIO_NL[p['regio']]}: {p['titel']}" + ("  [Check]" if p.get("check") else ""))
    if not (voor or kansen):
        print("\nGeen nieuwe voorstellen of kansen.")


def kies(id_, keuze):
    data = laad()
    keuze = keuze.lower()
    for k in data.get("kansen", []):
        if k["id"] == id_:
            if keuze not in ("interessant", "niet"):
                sys.exit("Bij een kans: interessant of niet.")
            k["status"] = "getoond"  # Berno's keuze zelf niet opslaan: de repository is openbaar
            bewaar(data)
            if keuze == "interessant":
                print(f"Geef Berno: {k['titel']}, {datum_nl(k['datum'])}, {k['plaats']}. "
                      + (f"Aanmelden vóór {datum_nl(k['deadline'])}. " if k.get("deadline") else "") + f"Link: {k['link']}")
            else:
                print("Genoteerd, komt niet terug.")
            return
    for p in data["punten"]:
        if p["id"] == id_:
            opties = KEUZES.get(p["status"])
            if not opties or keuze not in opties:
                sys.exit(f"Bij dit punt (status {p['status']}) kan: {', '.join(opties or [])}.")
            if opties[keuze]:
                p["status"] = opties[keuze]
            p["geschiedenis"].append({"datum": vandaag(), "keuze": keuze})
            bewaar(data)
            if keuze == "aanpassen":
                print("Herschrijf nu titel, tekst (Engels) en nl (Nederlands) in nieuws/nieuws.json naar wat Berno vraagt; "
                      "laat oud en nieuw zien en sla pas op na zijn ja.")
            else:
                print(f"{p['titel']}: {keuze}. Daarna: python3 bouw.py build")
            return
    sys.exit(f"Geen punt of kans met id {id_}.")


# ---------- toevoegen door de geplande taak ----------

def _controleer(obj, velden, soort):
    mist = [v for v in velden if not obj.get(v)]
    if mist:
        sys.exit(f"{soort}: ontbreekt {mist}")
    if obj["regio"] not in REGIO:
        sys.exit(f"regio moet een van {REGIO} zijn")
    for d in ("datum", "deadline"):
        if obj.get(d):
            dt.date.fromisoformat(obj[d])


def nieuw(js):
    p = json.loads(js)
    _controleer(p, NIEUW_VELDEN, "nieuw")
    if p["blok"] not in BLOK or p["rechtskracht"] not in RECHT or not set(p["toepassing"]) <= TOEPASSING:
        sys.exit(f"blok in {sorted(BLOK)}, rechtskracht in {sorted(RECHT)}, toepassing in {sorted(TOEPASSING)}")
    if p["blok"] == "tijdlijn" and not p.get("datum"):
        sys.exit("Nieuws in de tijdlijn heeft een datum nodig.")
    if not isinstance(p["bron"], dict) or not p["bron"].get("tekst"):
        sys.exit('bron: {"tekst": ..., "url": ..., "extra": ...}')
    data = laad()
    if any(q["id"] == p["id"] for q in data["punten"]):
        sys.exit(f"id {p['id']} bestaat al")
    p.update(status="voorstel", check=p.get("check", True), geschiedenis=[])
    data["punten"].append(p)
    bewaar(data)
    print(f"voorstel toegevoegd: {p['id']}")


def kans(js):
    k = json.loads(js)
    _controleer(k, KANS_VELDEN, "kans")
    data = laad()
    if any(q["id"] == k["id"] for q in data.setdefault("kansen", [])):
        sys.exit(f"id {k['id']} bestaat al")
    k["status"] = "nieuw"
    data["kansen"].append(k)
    bewaar(data)
    print(f"kans toegevoegd: {k['id']}")


def moet_check():
    laatste = laad().get("laatste_check")
    if laatste and (dt.date.today() - dt.date.fromisoformat(laatste)).days < 10:
        print(f"Laatste check {laatste}, minder dan 10 dagen geleden: overslaan.")
        sys.exit(1)
    print("Check nodig.")


def klaar():
    data = laad()
    data["laatste_check"] = vandaag()
    bewaar(data)
    print(f"laatste_check = {data['laatste_check']}")


# ---------- leesversie in Word ----------

def maak_word(naar_site):
    from docx import Document
    from docx.shared import Cm, Pt, RGBColor
    data = laad()
    groen, grijs, rood = RGBColor(0x52, 0x9F, 0x3F), RGBColor(0x56, 0x5F, 0x54), RGBColor(0xA3, 0x2A, 0x22)
    doc = Document()
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Cm(1.8)
        s.left_margin = s.right_margin = Cm(2.0)
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10.5)

    def kop(tekst, grootte=14, kleur=groen):
        par = doc.add_paragraph()
        par.paragraph_format.space_before = Pt(10)
        r = par.add_run(tekst)
        r.bold, r.font.size, r.font.color.rgb = True, Pt(grootte), kleur

    def klein(tekst, kleur=grijs):
        r = doc.add_paragraph().add_run(tekst)
        r.font.size, r.font.color.rgb = Pt(9), kleur

    t = doc.add_paragraph().add_run("Nieuwsoverzicht CO2CirculAir")
    t.bold, t.font.size = True, Pt(16)
    s = doc.add_paragraph().add_run(
        f"Editie {datum_nl(data.get('laatste_check') or vandaag())}. Dit is de leesversie. "
        "Kiezen doe je in je Claude-app: zeg \"nieuwsoverzicht\".")
    s.italic, s.font.color.rgb = True, grijs

    voor = [p for p in data["punten"] if p["status"] == "voorstel"]
    kansen = [k for k in open_kansen(data) if k["status"] == "nieuw"]
    for r in REGIO:
        rv = [p for p in voor if p["regio"] == r]
        rk = [k for k in kansen if k["regio"] == r]
        if not (rv or rk):
            continue
        kop(REGIO_NL[r])
        for p in rv:
            par = doc.add_paragraph()
            par.add_run("Nieuw voor de pagina: ").bold = True
            par.add_run(p["titel"]).bold = True
            if p.get("datum"):
                par.add_run(f"   {datum_nl(p['datum'])}").font.color.rgb = grijs
            doc.add_paragraph(p["nl"])
            klein(f"{p['rechtskracht']} · {', '.join(p['toepassing'])} | Bron: {bron_tekst(p['bron'])}"
                  + (f" | {p['bron']['url']}" if p["bron"].get("url") else ""))
            if p.get("check"):
                klein("Nog te controleren in de oorspronkelijke tekst.", rood)
        for k in rk:
            par = doc.add_paragraph()
            par.add_run("Kans om je te laten zien: ").bold = True
            par.add_run(f"{k['titel']}").bold = True
            par.add_run(f"   {datum_nl(k['datum'])}, {k['plaats']}").font.color.rgb = grijs
            doc.add_paragraph(f"{k['wat']} Wat het oplevert: {k['waarom']}")
            klein((f"Aanmelden vóór {datum_nl(k['deadline'])} | " if k.get("deadline") else "") + f"{k['link']} | Bron: {k['bron']}")
    if not (voor or kansen):
        doc.add_paragraph("Deze twee weken geen nieuwe voorstellen of kansen.")
    kop("Wat er nu op de pagina staat", 12)
    for p in data["punten"]:
        if p["status"] == "op-pagina":
            doc.add_paragraph(f"{REGIO_NL[p['regio']]}: {p['titel']}", style="List Bullet")
    if naar_site:
        uit = SITE_DOCX
    else:
        EDITIES.mkdir(exist_ok=True)
        uit = EDITIES / f"nieuwsoverzicht-{vandaag()}.docx"
    doc.core_properties.author = "CO2CirculAir"
    doc.save(uit)
    print(uit)


# ---------- mail aan Berno (de geplande taak verstuurt; zie CLAUDE.md) ----------

def mail():
    data = laad()
    voor = [p for p in data["punten"] if p["status"] == "voorstel"]
    kansen = [k for k in open_kansen(data) if k["status"] == "nieuw"]
    datum = datum_en(data.get("laatste_check") or vandaag())
    print(f"ONDERWERP: News overview CO2CirculAir, {datum}")
    print("TEKST:")
    print("Dear Berno,\n")
    if not (voor or kansen):
        print("No new developments or opportunities in the last two weeks. Nothing to choose this time.\n")
    else:
        def tel(n, een, meer):
            return f"{n} {een if n == 1 else meer}"
        print(f"The news overview of {datum} is ready: {tel(len(voor), 'proposal', 'proposals')} for the Legislation page "
              f"and {tel(len(kansen), 'opportunity', 'opportunities')} to present SMART-DAC.\n")
        for r in REGIO:
            rv = [p for p in voor if p["regio"] == r]
            rk = [k for k in kansen if k["regio"] == r]
            if not (rv or rk):
                continue
            print(f"{r}")
            for p in rv:
                print(f"- For the page: {p['titel']}")
            for k in rk:
                dl = f", apply before {datum_en(k['deadline'])}" if k.get("deadline") else ""
                print(f"- Opportunity: {k['titel']} ({datum_en(k['datum'])}, {k['plaats']}{dl})")
            print()
        print('To choose, open your Claude app and say: "nieuwsoverzicht". It will go through the points with you one by one.\n')
        print(f"Reading version for printing: {DOCX_URL}\n")
    print("This message is sent automatically every two weeks.")


# ---------- oude route: Word met vakjes teruglezen (alleen als Berno toch een bestand geeft) ----------

def lees(pad):
    with zipfile.ZipFile(pad) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    for sdt in root.iter(f"{{{W}}}sdt"):
        pr = sdt.find(f"{{{W}}}sdtPr")
        tag = pr.find(f"{{{W}}}tag") if pr is not None else None
        if tag is None:
            continue
        cb = pr.find(f"{{{W14}}}checkbox")
        if cb is not None:
            if cb.find(f"{{{W14}}}checked").get(f"{{{W14}}}val") in ("1", "true"):
                print(f"aangevinkt: {tag.get(f'{{{W}}}val')}")
        else:
            inhoud = "".join(t.text or "" for t in sdt.iter(f"{{{W}}}t")).strip()
            if inhoud and inhoud != PLACEHOLDER and pr.find(f"{{{W}}}showingPlcHdr") is None:
                print(f"tekst {tag.get(f'{{{W}}}val')}: {inhoud}")
    print("Zet elke keuze met: python3 nieuws/nieuws.py kies <id> <keuze>")


if __name__ == "__main__":
    a = sys.argv[1:]
    cmd = a[0] if a else ""
    if cmd == "lijst":
        lijst()
    elif cmd == "kies" and len(a) == 3:
        kies(a[1], a[2])
    elif cmd == "nieuw" and len(a) == 2:
        nieuw(a[1])
    elif cmd == "kans" and len(a) == 2:
        kans(a[1])
    elif cmd == "moet-check":
        moet_check()
    elif cmd == "klaar":
        klaar()
    elif cmd == "word":
        maak_word("--site" in a)
    elif cmd == "mail":
        mail()
    elif cmd == "lees" and len(a) == 2:
        lees(a[1])
    else:
        sys.exit(__doc__)
