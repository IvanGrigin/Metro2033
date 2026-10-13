#!/usr/bin/env python3
"""Вёрстка русскоязычного Fountain-сценария в PDF (US Letter, моноширинный 12 pt).

Поддерживается подмножество Fountain, которым пользуется metro2033.fountain:
титульная страница (Title/Credit/Author/Source/Draft date/Contact), принудительные
сцены `.`, персонажи `@`, переходы `>`, центровка `> … <`, ремарки `( … )`,
разделы `#` и синопсисы `=` (в вёрстку не попадают), заметки `[[ … ]]`,
разрыв страницы `===`, лирика `~`.

Геометрия по `sw-format-adaptation`, раздел 2.2: слева 1.5", справа 1", сверху и снизу 1",
6 строк на дюйм, 10 знаков на дюйм. Имя персонажа с 3.7", ремарка с 3.1",
реплика с 2.5" шириной 3.5", переход выровнен по правому краю 7.5".

Использование: render.py metro2033.fountain metro2033.pdf [--scenes]
С флагом --scenes дополнительно печатает «страница<TAB>заголовок сцены».
Выводит число страниц и число сцен.
"""
import re
import sys
import textwrap

from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_PATHS = {
    "Mono": "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
    "MonoBold": "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf",
}
INCH = 72
LINE = 12  # 6 строк на дюйм
TOP = 1.0 * INCH
BOTTOM = 1.0 * INCH
PAGE_W, PAGE_H = letter
LINES_PER_PAGE = int((PAGE_H - TOP - BOTTOM) / LINE)  # 54

# (отступ слева в дюймах, ширина в знаках)
LAYOUT = {
    "heading": (1.5, 60),
    "action": (1.5, 60),
    "character": (3.7, 38),
    "parenthetical": (3.1, 24),
    "dialogue": (2.5, 35),
    "transition": (None, 20),
    "centered": (None, 60),
    "lyric": (2.5, 35),
}


def parse(text):
    """Возвращает (title_page: dict, elements: list[(type, text)])."""
    lines = text.replace("\r\n", "\n").split("\n")
    title = {}
    i = 0
    key = None
    # Титульная страница: пары ключ-значение до первой пустой строки.
    if lines and re.match(r"^[A-Za-z ]+:", lines[0]):
        while i < len(lines) and lines[i].strip():
            m = re.match(r"^([A-Za-z ]+):\s*(.*)$", lines[i])
            if m:
                key = m.group(1).strip().lower()
                title[key] = [m.group(2)] if m.group(2) else []
            elif key:
                title[key].append(lines[i].strip())
            i += 1
    body = "\n".join(lines[i:])
    body = re.sub(r"\[\[.*?\]\]", "", body, flags=re.S)
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    elements = []
    blocks = re.split(r"\n\s*\n", body)
    for block in blocks:
        blines = [l.rstrip() for l in block.split("\n") if l.strip()]
        if not blines:
            continue
        first = blines[0].strip()
        if first.startswith("#") or first.startswith("="):
            if first.startswith("==="):
                elements.append(("pagebreak", ""))
            continue
        if first.startswith(".") and not first.startswith(".."):
            elements.append(("heading", first[1:].strip()))
            rest = blines[1:]
            if rest:
                elements.append(("action", "\n".join(rest)))
            continue
        if first.startswith("@"):
            elements.append(("character", first[1:].strip()))
            for l in blines[1:]:
                s = l.strip()
                if s.startswith("(") and s.endswith(")"):
                    elements.append(("parenthetical", s))
                else:
                    if elements[-1][0] == "dialogue":
                        elements[-1] = ("dialogue", elements[-1][1] + " " + s)
                    else:
                        elements.append(("dialogue", s))
            continue
        if first.startswith(">") and first.endswith("<"):
            elements.append(("centered", first[1:-1].strip()))
            continue
        if first.startswith(">"):
            elements.append(("transition", first[1:].strip()))
            continue
        if first.startswith("~"):
            elements.append(("lyric", "\n".join(l.strip().lstrip("~").strip() for l in blines)))
            continue
        text_block = "\n".join(l.lstrip("!") for l in blines)
        elements.append(("action", text_block))
    return title, elements


def wrap(kind, text):
    width = LAYOUT[kind][1]
    out = []
    for para in text.split("\n"):
        out.extend(textwrap.wrap(para, width) or [""])
    return out


def paginate(elements):
    """Раскладывает элементы по страницам. Возвращает list[list[(kind, line)]]."""
    pages = [[]]
    used = 0

    def new_page():
        nonlocal used
        pages.append([])
        used = 0

    # Группируем: персонаж + ремарки + реплики — неразрывный блок (если влезает в полстраницы).
    groups = []
    k = 0
    while k < len(elements):
        kind, text = elements[k]
        if kind == "character":
            grp = [(kind, text)]
            k += 1
            while k < len(elements) and elements[k][0] in ("parenthetical", "dialogue"):
                grp.append(elements[k])
                k += 1
            groups.append(grp)
            continue
        groups.append([(kind, text)])
        k += 1

    for gi, grp in enumerate(groups):
        if grp[0][0] == "pagebreak":
            new_page()
            continue
        lines = []
        for kind, text in grp:
            t = text.upper() if kind in ("heading", "character", "transition") else text
            for l in wrap(kind, t):
                lines.append((kind, l))
        space_before = 2 if grp[0][0] == "heading" else 1
        if not pages[-1]:
            space_before = 0
        need = space_before + len(lines)
        # Заголовок сцены не остаётся внизу страницы в одиночку.
        if grp[0][0] == "heading" and gi + 1 < len(groups):
            need += 2
        if used + need > LINES_PER_PAGE:
            if grp[0][0] == "character" and len(lines) > LINES_PER_PAGE // 2:
                pass  # длинную реплику переносим как есть
            elif grp[0][0] == "action" and len(lines) > 6 and LINES_PER_PAGE - used - space_before >= 3:
                # Длинный абзац действия делим между страницами.
                room = LINES_PER_PAGE - used - space_before
                for _ in range(space_before):
                    pages[-1].append(("blank", ""))
                pages[-1].extend(lines[:room])
                new_page()
                pages[-1].extend(lines[room:])
                used = len(lines) - room
                continue
            else:
                new_page()
                space_before = 0
        for _ in range(space_before):
            pages[-1].append(("blank", ""))
        for item in lines:
            if used >= LINES_PER_PAGE:
                new_page()
            pages[-1].append(item)
            used += 1
        used += space_before
    return [p for p in pages if p]


def draw(title, pages, out_path):
    for name, path in FONT_PATHS.items():
        pdfmetrics.registerFont(TTFont(name, path))
    c = canvas.Canvas(out_path, pagesize=letter)
    c.setTitle(" ".join(title.get("title", ["Сценарий"])))
    c.setAuthor(" ".join(title.get("author", [])))

    # Титульная страница
    if title:
        y = PAGE_H - 4 * INCH
        c.setFont("MonoBold", 12)
        for l in title.get("title", []):
            c.drawCentredString(PAGE_W / 2, y, l.strip("_*").upper())
            y -= LINE * 2
        c.setFont("Mono", 12)
        y -= LINE
        for key in ("credit", "author", "source"):
            for l in title.get(key, []):
                c.drawCentredString(PAGE_W / 2, y, l)
                y -= LINE * 2
        y = BOTTOM + 3 * LINE
        for key in ("draft date", "contact"):
            for l in title.get(key, []):
                c.drawString(1.5 * INCH, y, l)
                y -= LINE
        c.showPage()

    for n, page in enumerate(pages, start=1):
        c.setFont("Mono", 12)
        if n > 1:
            c.drawRightString(7.5 * INCH, PAGE_H - 0.5 * INCH, f"{n}.")
        y = PAGE_H - TOP - LINE + 3
        for kind, text in page:
            if kind == "blank":
                y -= LINE
                continue
            c.setFont("MonoBold" if kind == "heading" else "Mono", 12)
            left, _ = LAYOUT.get(kind, (1.5, 60))
            if kind == "transition":
                c.drawRightString(7.5 * INCH, y, text)
            elif kind == "centered":
                c.drawCentredString((1.5 * INCH + 7.5 * INCH) / 2, y, text)
            else:
                c.drawString(left * INCH, y, text)
            y -= LINE
        c.showPage()
    c.save()


def main():
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        title, elements = parse(f.read())
    pages = paginate(elements)
    draw(title, pages, dst)
    if "--scenes" in sys.argv:
        rows, prev = [], None
        for n, page in enumerate(pages, start=1):
            for kind, text in page:
                if kind == "heading" and prev == "heading":
                    rows[-1][1] += " " + text  # перенос длинного заголовка
                elif kind == "heading":
                    rows.append([n, text])
                prev = kind
        for n, text in rows:
            print(f"{n}\t{text}")
    scenes = sum(1 for k, _ in elements if k == "heading")
    words = sum(len(t.split()) for _, t in elements)
    print(f"pages={len(pages)} scenes={scenes} words={words}")


if __name__ == "__main__":
    main()
