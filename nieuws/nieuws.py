#!/usr/bin/env python3
"""Nieuwsoverzicht voor de Legislation-pagina: punten in nieuws.json, Word met vakjes voor Berno.

    python3 nieuws/nieuws.py word                        # Word-overzicht met aanklikbare vakjes, in nieuws/edities/
    python3 nieuws/nieuws.py lees <bestand>.docx         # wat Berno aanvinkte en schreef; verandert niets
    python3 nieuws/nieuws.py lees <bestand>.docx --toepassen   # zet zijn keuzes in nieuws.json
    python3 bouw.py build                                # zet de punten op de pagina (bouw.py roept invullen() aan)

Werkwijze: CLAUDE.md, sectie "Nieuwsoverzicht". Teruggestuurde Word-bestanden nooit in de repository zetten:
die is openbaar en ze bevatten Berno's opmerkingen.
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
DATA = HIER / "nieuws.json"
EDITIES = HIER / "edities"
BRON = HIER.parent / "bron" / "legislation.md"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
NS = f'xmlns:w="{W}" xmlns:w14="{W14}"'
KEUZES = {"op-pagina": ["Houden", "Aanpassen", "Weghalen"], "voorstel": ["Plaatsen", "Niet"]}
PLACEHOLDER = "Klik en typ hier"
MAAND_NL = "januari februari maart april mei juni juli augustus september oktober november december".split()
MAAND_EN = "January February March April May June July August September October November December".split()


def datum_nl(d):
    return f"{d.day} {MAAND_NL[d.month - 1]} {d.year}"


def datum_en(d):
    return f"{d.day} {MAAND_EN[d.month - 1]} {d.year}"


def laad():
    return json.loads(DATA.read_text(encoding="utf-8"))


def bewaar(data):
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bron_tekst(p):
    b = p["bron"]
    return b["tekst"] + (f", {b['extra']}" if b.get("extra") else "")


def paginanaam():
    m = re.search(r"^## sec1\.kicker\.1\n(.+)$", BRON.read_text(encoding="utf-8"), re.M)
    return m.group(1).strip() if m else "Legislation"


# ---------- pagina: wordt aangeroepen door bouw.py ----------

def _tags(p):
    klasse = {"In force": "inforce", "Proposal": "proposal"}[p["rechtskracht"]]
    t = [f'<span class="tag {klasse}">{p["rechtskracht"]}</span>', f'<span class="tag region">{html.escape(p["regio"])}</span>']
    t += [f'<span class="tag">{html.escape(a)}</span>' for a in p["toepassing"]]
    if p["check"]:
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
    datum = f'<time>{datum_en(dt.date.fromisoformat(p["datum"]))}</time>' if p.get("datum") else ""
    return (f'<li>{merk}{datum}{_tags(p)}<h3>{html.escape(p["titel"])}</h3>'
            f'<p>{html.escape(p["tekst"])}</p>{_bron(p)}</li>')


LEGENDA = ('<div class="legend"><span class="tag inforce">In force</span> applies now '
           '<span class="tag proposal">Proposal</span> not yet law '
           '<span class="tag region">EU</span> or <span class="tag region">Netherlands</span> where it applies '
           '<span class="tag">Greenhouses</span> the use it concerns</div>')


def invullen(pagina_html):
    """Vervangt <!--NIEUWS:blok--> in de pagina door de punten van dat blok."""
    data = laad()
    zicht = {"op-pagina", "voorstel"} if data.get("toon_voorstellen") else {"op-pagina"}

    def blok(m):
        naam = m.group(1)
        if naam == "legenda":
            return LEGENDA
        punten = [p for p in data["punten"] if p["blok"] == naam and p["status"] in zicht]
        if naam == "tijdlijn":
            punten.sort(key=lambda p: p["datum"], reverse=True)
            return '<ol class="timeline">' + "".join(_kaart(p) for p in punten) + "</ol>" if punten else ""
        return '<ul class="positions">' + "".join(_kaart(p) for p in punten) + "</ul>" if punten else ""

    return re.sub(r"<!--NIEUWS:(\w+)-->", blok, pagina_html)


# ---------- Word ----------

def _vakje(par, tag, label):
    from docx.oxml import parse_xml
    from docx.shared import Pt
    par._p.append(parse_xml(
        f'<w:sdt {NS}><w:sdtPr><w:tag w:val="{html.escape(tag)}"/>'
        '<w14:checkbox><w14:checked w14:val="0"/>'
        '<w14:checkedState w14:val="2612" w14:font="MS Gothic"/>'
        '<w14:uncheckedState w14:val="2610" w14:font="MS Gothic"/></w14:checkbox></w:sdtPr>'
        '<w:sdtContent><w:r><w:rPr><w:rFonts w:ascii="MS Gothic" w:eastAsia="MS Gothic" w:hAnsi="MS Gothic"/>'
        '<w:sz w:val="26"/></w:rPr><w:t>☐</w:t></w:r></w:sdtContent></w:sdt>'))
    par.add_run(f" {label}      ").font.size = Pt(11)


def _tekstveld(par, tag):
    from docx.oxml import parse_xml
    par._p.append(parse_xml(
        f'<w:sdt {NS}><w:sdtPr><w:tag w:val="{html.escape(tag)}"/><w:showingPlcHdr/></w:sdtPr>'
        '<w:sdtContent><w:r><w:rPr><w:color w:val="8A8A8A"/></w:rPr>'
        f'<w:t>{PLACEHOLDER}</w:t></w:r></w:sdtContent></w:sdt>'))


def maak_word():
    from docx import Document
    from docx.shared import Cm, Pt, RGBColor
    data = laad()
    vandaag = dt.date.today()
    EDITIES.mkdir(exist_ok=True)
    uit = EDITIES / f"nieuwsoverzicht-{vandaag.isoformat()}.docx"
    groen, grijs = RGBColor(0x52, 0x9F, 0x3F), RGBColor(0x56, 0x5F, 0x54)
    doc = Document()
    for s in doc.sections:
        s.top_margin = s.bottom_margin = Cm(1.8)
        s.left_margin = s.right_margin = Cm(2.0)
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10.5)

    def kop(tekst, grootte=14):
        par = doc.add_paragraph()
        par.paragraph_format.space_before = Pt(10)
        r = par.add_run(tekst)
        r.bold, r.font.size, r.font.color.rgb = True, Pt(grootte), groen

    def punt(p):
        par = doc.add_paragraph()
        par.paragraph_format.space_before = Pt(10)
        r = par.add_run(p["titel"])
        r.bold, r.font.size = True, Pt(11.5)
        if p.get("datum"):
            par.add_run(f"   {datum_nl(dt.date.fromisoformat(p['datum']))}").font.color.rgb = grijs
        doc.add_paragraph(p["nl"])
        meta = doc.add_paragraph()
        labels = [p["rechtskracht"], p["regio"], *p["toepassing"]]
        m = meta.add_run(f"{' · '.join(labels)}   |   Bron: {bron_tekst(p)}")
        m.font.size, m.font.color.rgb = Pt(9), grijs
        if p["check"]:
            c = meta.add_run("   (nog te controleren in de oorspronkelijke tekst)")
            c.font.size, c.font.color.rgb = Pt(9), RGBColor(0xA3, 0x2A, 0x22)
        k = doc.add_paragraph()
        for label in KEUZES[p["status"]]:
            _vakje(k, f"{p['id']}|{label}", label)
        o = doc.add_paragraph()
        o.add_run("Opmerking: ").bold = True
        _tekstveld(o, f"{p['id']}|opmerking")

    t = doc.add_paragraph().add_run(f"Nieuwsoverzicht CO2CirculAir, pagina {paginanaam()}")
    t.bold, t.font.size, t.font.color.rgb = True, Pt(16), RGBColor(0x14, 0x18, 0x13)
    s = doc.add_paragraph().add_run(
        f"Editie {datum_nl(vandaag)}. Klik per punt één vakje aan, typ eventueel een opmerking, sla op "
        "en geef het document aan je Claude. Op papier mag ook.")
    s.italic, s.font.color.rgb = True, grijs

    op, voor = ([p for p in data["punten"] if p["status"] == st] for st in ("op-pagina", "voorstel"))
    kop("Deel 1. Wat er op de pagina staat")
    if op:
        doc.add_paragraph("Houden, aanpassen (zet bij Opmerking wat anders moet) of weghalen.")
        for p in op:
            punt(p)
    else:
        doc.add_paragraph("Er staan nog geen punten op de pagina.")
    kop("Deel 2. Nieuw voorgesteld")
    if voor:
        doc.add_paragraph("Plaatsen op de pagina of niet.")
        for p in voor:
            punt(p)
    else:
        doc.add_paragraph("Deze twee weken geen nieuws dat de pagina verandert.")
    kop("Zelf iets toevoegen?", 12)
    doc.add_paragraph("Nieuws of een ontwikkeling die erop moet: de link of een korte omschrijving.")
    for i in range(3):
        _tekstveld(doc.add_paragraph(), f"toevoegen|{i + 1}")
    doc.save(uit)
    print(uit)


# ---------- terug lezen (alleen standaardbibliotheek) ----------

def lees_docx(pad):
    """{tag: True/False voor een vakje, tekst voor een invulveld}."""
    with zipfile.ZipFile(pad) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    uit = {}
    for sdt in root.iter(f"{{{W}}}sdt"):
        pr = sdt.find(f"{{{W}}}sdtPr")
        tag = pr.find(f"{{{W}}}tag") if pr is not None else None
        if tag is None:
            continue
        sleutel = tag.get(f"{{{W}}}val")
        cb = pr.find(f"{{{W14}}}checkbox")
        if cb is not None:
            uit[sleutel] = cb.find(f"{{{W14}}}checked").get(f"{{{W14}}}val") in ("1", "true")
        else:
            inhoud = "".join(t.text or "" for t in sdt.iter(f"{{{W}}}t")).strip()
            leeg = pr.find(f"{{{W}}}showingPlcHdr") is not None or inhoud == PLACEHOLDER
            uit[sleutel] = "" if leeg else inhoud
    return uit


def lees(pad, toepassen):
    pad = Path(pad)
    velden = lees_docx(pad)
    data = laad()
    vandaag = dt.date.today().isoformat()
    open_werk, gewijzigd = [], False
    for p in data["punten"]:
        keuzes = KEUZES.get(p["status"])
        if not keuzes or f"{p['id']}|{keuzes[0]}" not in velden:
            continue  # stond niet in deze editie
        aan = [k for k in keuzes if velden.get(f"{p['id']}|{k}")]
        opm = velden.get(f"{p['id']}|opmerking", "")
        print(f"- {p['titel']} [{p['id']}]: {', '.join(aan) or 'geen vakje'}" + (f". Opmerking: {opm}" if opm else ""))
        if len(aan) != 1:
            open_werk.append(f"{p['titel']}: {'meer dan één vakje' if aan else 'geen vakje'}, Berno vragen wat hij bedoelt")
            continue
        keuze = aan[0]
        if keuze == "Aanpassen":
            open_werk.append(f"{p['titel']} [{p['id']}]: herschrijven naar zijn opmerking, oud en nieuw aan Berno laten zien")
        elif opm:
            open_werk.append(f"{p['titel']}: {keuze.lower()}, met opmerking; vragen of er iets moet veranderen")
        if toepassen:
            p["geschiedenis"].append({"datum": vandaag, "keuze": keuze})
            p["status"] = {"Weghalen": "weg", "Plaatsen": "op-pagina", "Niet": "weg"}.get(keuze, p["status"])
            gewijzigd = True
    for k, v in sorted(velden.items()):
        if k.startswith("toevoegen|") and v:
            print(f"- Zelf toegevoegd: {v}")
            open_werk.append(f"Berno's eigen punt: bron opzoeken en als voorstel in nieuws.json zetten ({v})")
    if open_werk:
        print("\nNog te doen:")
        for o in open_werk:
            print(f"  * {o}")
    if toepassen and gewijzigd:
        bewaar(data)
        print("\nnieuws.json bijgewerkt. Daarna: python3 bouw.py build")
    elif not toepassen:
        print("\nNiets veranderd. Toepassen met --toepassen.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["word"]:
        maak_word()
    elif args[:1] == ["lees"] and len(args) >= 2:
        lees(args[1], "--toepassen" in args)
    else:
        sys.exit(__doc__)
