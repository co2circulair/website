#!/usr/bin/env python3
"""Bouwt de CO2CirculAir-site en het Word-document uit één tekstbron.

    python3 bouw.py extract   # eenmalig: haalt teksten uit site/*.html naar bron/ en maakt sjablonen
    python3 bouw.py build     # bron/ + sjablonen -> site/*.html en TEKST-MASTER.docx
    python3 bouw.py check     # bouwt naar een tijdelijke map en vergelijkt met site/

Werkwijze: de tekst staat in bron/<pagina>.md, per blok een kop "## sleutel" met daaronder de tekst.
Inline HTML (strong, a, br, mark) mag in de tekst blijven staan. De opmaak zit in bron/sjablonen/.
Nooit tekst rechtstreeks in site/*.html wijzigen: die bestanden worden overschreven bij build.
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
BRON = ROOT / "bron"
SJAB = BRON / "sjablonen"
DOCX = ROOT / "TEKST-MASTER.docx"

PAGES = [  # (bestand, naam in de bron en in Word)
    ("index.html", "home"),
    ("technology.html", "technology"),
    ("news.html", "news"),
    ("team.html", "team"),
    ("contact.html", "contact"),
    ("privacy.html", "privacy"),
]

# Delen van de pagina die in het sjabloon blijven (navigatie, voettekst, inhoudsopgave, tekening).
SKIP_BLOCKS = re.compile(
    r"<header class=\"site-header\">.*?</header>|<footer class=\"site-footer\">.*?</footer>"
    r"|<nav class=\"toc\".*?</nav>|<svg.*?</svg>",
    re.S,
)
# Volgorde: binnenste elementen eerst, zodat een li met een p erin niet als geheel wordt gepakt.
PASSES = [
    ("span", r'class="(?:kicker|value|label|year)"', None),
    ("a", r'class="btn', "btn"),
    ("th", None, None), ("td", None, None),
    ("figcaption", None, None), ("dt", None, None), ("dd", None, None),
    ("p", None, None), ("h1", None, None), ("h2", None, None), ("h3", None, None), ("h4", None, None),
    ("li", None, None), ("title", None, None),
]
BLOCK_INSIDE = re.compile(r"<(?:ul|ol|div|p|li|table|tr|svg|figure|section|h[1-4])[\s>]")


def _section_map(text):
    """Geeft per positie in de tekst de naam van de omliggende sectie."""
    marks = []
    n = 0
    for m in re.finditer(r"<section\b([^>]*)>", text):
        attrs = m.group(1)
        idm = re.search(r'id="([^"]+)"', attrs)
        clm = re.search(r'class="([^"]+)"', attrs)
        n += 1
        classes = clm.group(1).split() if clm else []
        name = idm.group(1) if idm else next((c for c in ("hero", "cta") if c in classes), f"sec{n}")
        marks.append((m.start(), name))

    def lookup(pos):
        name = "head"
        for start, nm in marks:
            if start <= pos:
                name = nm
        return name
    return lookup


def extract_page(fname, page):
    text = (SITE / fname).read_text(encoding="utf-8")
    # Bescherm de blokken die in het sjabloon blijven.
    protected = []

    def protect(m):
        protected.append(m.group(0))
        return f"\x00{len(protected) - 1}\x00"
    work = SKIP_BLOCKS.sub(protect, text)

    section_of = _section_map(work)
    counters = {}
    items = []  # (key, tekst)

    for tag, attr_re, keyname in PASSES:
        pat = re.compile(rf"<{tag}(\s[^>]*)?>(.*?)</{tag}>", re.S)
        section_of = _section_map(work)  # posities verschuiven per pass

        def repl(m):
            attrs, inner = m.group(1) or "", m.group(2)
            if attr_re and not re.search(attr_re, attrs):
                return m.group(0)
            if not inner.strip() or "{{" in inner or BLOCK_INSIDE.search(inner) or "\x00" in inner:
                return m.group(0)
            if tag == "span":
                kn = re.search(r'class="(\w+)"', attrs).group(1)
            else:
                kn = keyname or tag
            sec = section_of(m.start())
            counters[(sec, kn)] = counters.get((sec, kn), 0) + 1
            key = f"{sec}.{kn}.{counters[(sec, kn)]}"
            items.append((key, inner.strip()))
            return f"<{tag}{attrs}>{{{{{key}}}}}</{tag}>"
        work = pat.sub(repl, work)

    # Meta description
    def meta_repl(m):
        items.insert(0, ("head.description", m.group(1)))
        return m.group(0).replace(m.group(1), "{{head.description}}")
    work = re.sub(r'<meta name="description" content="([^"]*)"', meta_repl, work, count=1)

    work = re.sub(r"\x00(\d+)\x00", lambda m: protected[int(m.group(1))], work)
    items.sort(key=lambda kv: work.index("{{" + kv[0] + "}}"))  # in paginavolgorde

    SJAB.mkdir(parents=True, exist_ok=True)
    (SJAB / fname).write_text(work, encoding="utf-8")
    out = [f"# {page}, {fname}", "",
           "Eén blok per kop. De sleutel achter ## niet wijzigen, alleen de tekst eronder.", ""]
    for key, val in items:
        out += [f"## {key}", val, ""]
    (BRON / f"{page}.md").write_text("\n".join(out), encoding="utf-8")
    print(f"{fname}: {len(items)} blokken naar bron/{page}.md")


def read_bron(page):
    text = (BRON / f"{page}.md").read_text(encoding="utf-8")
    items = []
    for m in re.finditer(r"^## (\S+)\n(.*?)(?=^## |\Z)", text, re.S | re.M):
        items.append((m.group(1), m.group(2).strip()))
    return items


def build_page(fname, page, outdir):
    tpl = (SJAB / fname).read_text(encoding="utf-8")
    items = dict(read_bron(page))
    needed = set(re.findall(r"\{\{([^}]+)\}\}", tpl))
    missing, extra = needed - items.keys(), items.keys() - needed
    if missing or extra:
        sys.exit(f"{page}: ontbreekt in bron {sorted(missing)}, niet in sjabloon {sorted(extra)}")
    out = re.sub(r"\{\{([^}]+)\}\}", lambda m: items[m.group(1)], tpl)
    tmp = outdir / (fname + ".tmp")  # schrijven via tijdelijk bestand, overschrijven bleek traag
    tmp.write_text(out, encoding="utf-8")
    tmp.replace(outdir / fname)
    return items


# ---------- Word ----------

def _plain_runs(fragment):
    """Splitst inline HTML in (tekst, bold, open-markering)."""
    fragment = fragment.replace("<br>", "\n").replace("<br />", "\n")
    runs, bold, mark = [], False, None
    for tok in re.split(r"(<[^>]+>)", fragment):
        if not tok:
            continue
        if tok.startswith("<"):
            t = tok.lower()
            if t.startswith("<strong"):
                bold = True
            elif t.startswith("</strong"):
                bold = False
            elif t.startswith("<mark"):
                title = re.search(r'title="([^"]*)"', tok)
                mark = title.group(1) if title else ""
                if mark:
                    runs.append((f"[OPEN: {html.unescape(mark)}] ", False, True))
            elif t.startswith("</mark"):
                mark = None
            continue
        runs.append((html.unescape(re.sub(r"\s+", " ", tok)), bold, mark is not None))
    return runs


def build_docx(all_items):
    from docx import Document
    from docx.enum.text import WD_COLOR_INDEX
    from docx.shared import Pt

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    doc.add_heading("CO2CirculAir website, tekst", 0)
    doc.add_paragraph("Dit document is gegenereerd uit de tekstbron van de site. Wijzig de tekst hier of op papier; "
                      "de wijzigingen worden overgenomen in de bron en daaruit wordt de site opnieuw gebouwd. "
                      "Gele tekst tussen [OPEN: ...] is een opmerking van Andrea, geen sitetekst.")

    for fname, page, items in all_items:
        tpl = (SJAB / fname).read_text(encoding="utf-8")
        doc.add_page_break()
        doc.add_heading(f"{page.capitalize()} ({fname})", 1)
        for k in ("head.title.1", "head.description"):
            if k in items:
                p = doc.add_paragraph()
                p.add_run("Browsertitel: " if k.endswith("title.1") else "Omschrijving voor Google: ").italic = True
                _add_runs(p, items[k])
                p.add_run(f"  [{k}]").font.size = Pt(7)
        # Tabellen: per <table> de sleutels in rijen en kolommen.
        cellpos, tables_dims, done_tables = {}, [], set()
        for ti, tm in enumerate(re.finditer(r"<table.*?</table>", tpl, re.S)):
            rows = re.findall(r"<tr>(.*?)</tr>", tm.group(0), re.S)
            ncols = 0
            for ri, row in enumerate(rows):
                keys = re.findall(r"\{\{([^}]+)\}\}", row)
                ncols = max(ncols, len(keys))
                for ci, k in enumerate(keys):
                    cellpos[k] = (ti, ri, ci)
            tables_dims.append((len(rows), ncols))
        body = tpl[tpl.index("<main"):tpl.index("</main>")]  # navigatie en voettekst niet in Word
        for m in re.finditer(r"<(\w+)(\s[^>]*)?>\{\{([^}]+)\}\}</\1>|<meta name=\"description\" content=\"\{\{([^}]+)\}\}\"|<img\b([^>]*)>|<svg class=\"process\"", body if "<main" in tpl else tpl):
            if m.group(0).startswith("<img") or m.group(0).startswith("<svg"):
                _add_image(doc, m, fname)
                continue
            tag, attrs, key = m.group(1), m.group(2) or "", m.group(3) or m.group(4)
            if m.group(4):
                tag = "meta"
            val = items[key]
            if key in cellpos:
                ti, ri, ci = cellpos[key]
                if ti not in done_tables:
                    nrows, ncols = tables_dims[ti]
                    table = doc.add_table(rows=nrows, cols=ncols)
                    table.style = "Table Grid"
                    done_tables.add(ti)
                _add_runs(table.rows[ri].cells[ci].paragraphs[0], val, bold=(tag == "th"))
                continue
            if tag in ("title", "meta"):
                continue
            elif tag == "h1":
                _add_runs(doc.add_heading("", 2), val)
            elif tag in ("h2", "h3", "h4"):
                _add_runs(doc.add_heading("", {"h2": 3, "h3": 4, "h4": 4}[tag]), val)
            elif tag == "span":
                kind = re.search(r'class="(\w+)"', attrs).group(1)
                p = doc.add_paragraph()
                p.add_run(f"{kind}: ").italic = True
                _add_runs(p, val)
            elif tag == "a":
                p = doc.add_paragraph()
                p.add_run("knop: ").italic = True
                _add_runs(p, val)
            elif tag == "li":
                _add_runs(doc.add_paragraph(style="List Bullet"), val)
            elif tag == "figcaption":
                p = doc.add_paragraph()
                p.add_run("bijschrift: ").italic = True
                _add_runs(p, val)
            else:
                _add_runs(doc.add_paragraph(), val)
            doc.paragraphs[-1].add_run(f"  [{key}]").font.size = Pt(7)
    doc.save(DOCX)
    print(f"Word: {DOCX.name}")


def _add_image(doc, m, fname):
    """Zet een foto of de procestekening in het Word-document, met het bijschrift uit alt."""
    from docx.shared import Cm
    if m.group(0).startswith("<svg"):
        png = _render_process(fname)
        if png:
            doc.add_picture(str(png), width=Cm(16))
            doc.add_paragraph("Procestekening zoals op de site.").runs[0].italic = True
        return
    attrs = m.group(5) or ""
    src = re.search(r'src="([^"]+)"', attrs)
    if not src or "logo" in src.group(1):
        return
    path = SITE / src.group(1)
    if not path.exists():
        return
    alt = re.search(r'alt="([^"]*)"', attrs)
    width = Cm(6) if "portret" in src.group(1) else Cm(16)
    doc.add_picture(str(path), width=width)
    if alt and alt.group(1):
        doc.add_paragraph(f"Foto: {alt.group(1)}").runs[0].italic = True


def _render_process(fname):
    """Rendert de SVG-procestekening naar png via Chrome, zoals hij op de site staat."""
    import subprocess, tempfile
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome.exists():
        return None
    tpl = (SJAB / fname).read_text(encoding="utf-8")
    svg = tpl[tpl.index("<svg class=\"process\""):tpl.index("</svg>") + 6]
    tmp = Path(tempfile.mkdtemp())
    (tmp / "p.html").write_text(
        f'<!doctype html><html><head><link rel="stylesheet" href="file://{SITE}/css/fonts.css">'
        f'<link rel="stylesheet" href="file://{SITE}/css/style.css"></head>'
        f'<body style="margin:0;background:#121512"><main><section class="section" style="padding:10px">'
        f'<div style="width:1170px">{svg}</div></section></main></body></html>', encoding="utf-8")
    out = tmp / "process.png"
    subprocess.run([str(chrome), "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    "--window-size=1190,360", f"--screenshot={out}", f"file://{tmp}/p.html"],
                   capture_output=True, timeout=60)
    return out if out.exists() else None


def _add_runs(paragraph, fragment, bold=False):
    from docx.enum.text import WD_COLOR_INDEX
    for text, b, is_open in _plain_runs(fragment):
        run = paragraph.add_run(text)
        run.bold = bold or b
        if is_open:
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def build(outdir=None, docx=True):
    outdir = outdir or SITE
    all_items = []
    for fname, page in PAGES:
        items = build_page(fname, page, outdir)
        all_items.append((fname, page, items))
        print(f"{fname}: {len(items)} blokken")
    if docx:
        try:
            build_docx(all_items)
        except ImportError:
            print("Word-versie overgeslagen: python-docx ontbreekt (pip install -r requirements.txt). De site is wel gebouwd.")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cmd = args[0] if args else "build"
    variant = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--variant=")), None)
    if variant:  # aparte bron en aparte uitvoer, sjablonen en beeld gedeeld met de hoofdversie
        import shutil
        BRON = ROOT / f"bron-{variant}"
        out = ROOT / "site-versies" / variant
        out.mkdir(parents=True, exist_ok=True)
        for sub in ("css", "fonts", "img"):
            if (out / sub).exists():
                shutil.rmtree(out / sub)
            shutil.copytree(SITE / sub, out / sub)
        SITE = out
        DOCX = out / f"website-tekst-en-beeld-{variant}.docx"
    if cmd == "extract":
        BRON.mkdir(exist_ok=True)
        for fname, page in PAGES:
            extract_page(fname, page)
    elif cmd == "build":
        build()
    elif cmd == "check":
        import filecmp, tempfile
        tmp = Path(tempfile.mkdtemp())
        build(tmp, docx=False)
        for fname, _ in PAGES:
            same = filecmp.cmp(tmp / fname, SITE / fname, shallow=False)
            print(f"{fname}: {'identiek' if same else 'VERSCHILT'}")
    else:
        sys.exit(__doc__)
