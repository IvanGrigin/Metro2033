#!/usr/bin/env python3
"""Лист требований к окружению по сценам — вход для критика окружения.

Читает metro2033.fountain, нумерует сцены так же, как их считает план
(по порядку заголовков `.ИНТ.` / `.НАТ.`, начиная с 1), и для каждой сцены
выписывает то, что окружение обязано показать:

- место и время суток из заголовка;
- строки ремарок с «проверяемыми» словами: свет, часы и время, огонь,
  надписи и цифры на стенах, геометрия (свод, колонны, эскалатор,
  туннель, ротонда...), реквизит состояния (мешки, палатки, гермозатвор...);
- точное время вида 23:40, если оно названо.

В конце печатает сквозную сводку по местам: какие сцены идут в одном месте
и при каком времени суток. Если одно место встречается и днём, и ночью,
критик обязан проверить, что свет в рендерах разный.

Использование:
    scene_env.py metro2033.fountain [--scenes 1-23] [--out файл.md]
"""
import argparse
import re
import sys
from collections import OrderedDict

HEADING = re.compile(r"^\.(ИНТ|НАТ)\.\s*(.+)$")
TIME_OF_DAY = re.compile(
    r"«?(ДЕНЬ|НОЧЬ|УТРО|ВЕЧЕР|РАССВЕТ|РАННЕЕ УТРО|ПРЕДРАССВЕТНОЕ ВРЕМЯ|ПОЗЖЕ|"
    r"ПРОДОЛЖЕНИЕ|НЕПРЕРЫВНО|СОН|ВИДЕНИЕ|ВСПЫШКА|РАНЬШЕ)»?"
)
CLOCK = re.compile(r"\b([01]?\d|2[0-3]):[0-5]\d\b")

# Группа → корни слов. Порядок групп = порядок вывода.
CUES = OrderedDict([
    ("свет", ["свет", "ламп", "фонар", "прожектор", "темн", "тьм", "мрак", "багров",
              "красн", "аварийн", "приглуш", "тускл", "сумрак", "отблеск"]),
    ("огонь", ["костёр", "костер", "огон", "огн", "пламя", "факел", "углей", "угли", "дым", "копот"]),
    ("время", ["час", "минут", "сутк", "полноч", "смен"]),
    ("надписи", ["надпис", "краской", "табличк", "указател", "столб", "«2", "«3", "плакат"]),
    ("геометрия", ["свод", "колонн", "пилон", "арк", "эскалатор", "туннел", "перегон", "тупик",
                   "стрелк", "съезд", "платформ", "пут", "рельс", "шпал", "вестибюл", "ротонд",
                   "крыш", "потол", "торц", "зал", "переход", "лестниц", "гермо", "створк",
                   "боков", "вентиляц", "сбойк", "камер"]),
    ("состояние", ["мешк", "палатк", "баррикад", "блокпост", "кордон", "застав", "пулемёт",
                   "ржав", "обруш", "завал", "сгни", "плесен", "мох", "грибн", "свинар",
                   "развал", "провал", "дрезин"]),
    ("наверху", ["небо", "звёзд", "звезд", "снег", "руин", "поверхност", "наверх"]),
])


def parse_scenes_strict(text):
    """Сцены с ремарками; блоки реплик (от @ИМЯ до пустой строки) пропускаются."""
    lines = text.splitlines()
    scenes = []
    cur = None
    in_dialogue = False
    for lineno, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line:
            in_dialogue = False
            continue
        m = HEADING.match(line)
        if m:
            cur = {"n": len(scenes) + 1, "line": lineno, "kind": m.group(1),
                   "heading": m.group(2), "action": []}
            scenes.append(cur)
            in_dialogue = False
            continue
        if cur is None:
            continue
        if line.startswith("@"):
            in_dialogue = True
            continue
        if in_dialogue or line.startswith(("#", "=", ">", "[[", "~")):
            continue
        cur["action"].append((lineno, line))
    return scenes


def split_heading(heading):
    parts = [p.strip() for p in heading.split("—")]
    times = []
    place = []
    for p in parts:
        if TIME_OF_DAY.fullmatch(p.split(" (")[0].strip()):
            times.append(p)
        else:
            place.append(p)
    return " — ".join(place), " — ".join(times) or "не указано"


def cues_for(sentence):
    low = sentence.lower()
    found = []
    for group, roots in CUES.items():
        if any(r.lower() in low for r in roots):
            found.append(group)
    return found


def sentences(line):
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", line) if s.strip()]


def parse_range(spec, total):
    if not spec:
        return set(range(1, total + 1))
    out = set()
    for chunk in spec.split(","):
        if "-" in chunk:
            a, b = chunk.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(chunk))
    return out


def base_place(place):
    """«СТАНЦИЯ ВДНХ — ПЛАТФОРМА» и «ВДНХ — КАБИНЕТ» → ВДНХ (для сквозной сводки)."""
    first = place.split(" — ")[0]
    first = re.sub(r"^(СТАНЦИЯ|ТУННЕЛЬ|ПЕРЕГОН)\s+", "", first)
    return first


def render(scenes, wanted, src):
    out = []
    out.append("# Требования к окружению по сценам\n")
    out.append(f"Собрано `tools/scene_env.py` из `{src}`. Номер сцены — порядковый номер заголовка.\n")
    out.append("Это **что сцена требует**, а не что сделано. Критик сверяет каждый пункт с рендером.\n")
    last_time = "не указано"
    for sc in scenes:
        place, tod = split_heading(sc["heading"])
        if tod.startswith(("ПРОДОЛЖЕНИЕ", "НЕПРЕРЫВНО", "ПОЗЖЕ")):
            eff = f"{tod} → как в предыдущей сцене: {last_time}"
        else:
            eff = tod
            last_time = tod
        sc["place"], sc["tod"] = place, eff
    for sc in scenes:
        if sc["n"] not in wanted:
            continue
        out.append(f"\n## Сцена {sc['n']} — {sc['kind']}. {sc['heading']}\n")
        out.append(f"- Строка в сценарии: {sc['line']}")
        out.append(f"- Место: {sc['place']}")
        out.append(f"- Время суток: {sc['tod']}")
        clocks = sorted({m.group(0) for _, l in sc["action"] for m in CLOCK.finditer(l)})
        if clocks:
            out.append(f"- **Точное время в кадре: {', '.join(clocks)}** — часы на модели должны показывать именно это")
        items = []
        for lineno, line in sc["action"]:
            for s in sentences(line):
                g = cues_for(s)
                if g:
                    items.append(f"- [ ] ({', '.join(g)}) «{s}» — стр. {lineno}")
        if items:
            out.append("\nПроверяемые детали:\n")
            out.extend(items)
        else:
            out.append("\nПроверяемых деталей в ремарках нет — окружение по паспорту места.")
    # Сквозная сводка
    out.append("\n## Сквозная сводка по местам\n")
    out.append("| Место | Сцены | Время суток | Что проверить |")
    out.append("|---|---|---|---|")
    groups = OrderedDict()
    for sc in scenes:
        if sc["n"] in wanted:
            groups.setdefault(base_place(sc["place"]), []).append(sc)
    for name, scs in groups.items():
        tods = sorted({s["tod"].split(" → ")[-1].replace("как в предыдущей сцене: ", "") for s in scs})
        ns = ", ".join(str(s["n"]) for s in scs)
        note = ""
        has_day = any("ДЕНЬ" in t or "УТРО" in t for t in tods)
        has_night = any("НОЧЬ" in t or "ВЕЧЕР" in t for t in tods)
        if len(scs) > 1:
            note = "одна модель на все сцены: геометрия и реквизит совпадают"
        if has_day and has_night:
            note += "; **день и ночь — свет должен различаться**"
        out.append(f"| {name} | {ns} | {'; '.join(tods)} | {note.strip('; ')} |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fountain")
    ap.add_argument("--scenes", help="например 1-23 или 2,10,20")
    ap.add_argument("--out", help="куда записать markdown (по умолчанию stdout)")
    a = ap.parse_args()
    with open(a.fountain, encoding="utf-8") as f:
        text = f.read()
    scenes = parse_scenes_strict(text)
    wanted = parse_range(a.scenes, len(scenes))
    md = render(scenes, wanted, a.fountain)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Сцен всего: {len(scenes)}, в листе: {len(wanted & set(range(1, len(scenes) + 1)))} → {a.out}")
    else:
        sys.stdout.write(md)


if __name__ == "__main__":
    main()
