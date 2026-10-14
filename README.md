# Метро 2033 — сценарий

Экранизация романа Дмитрия Глуховского «Метро 2033». Учебная работа: полнометражный фильм, который можно разбить на три серии.

- `screenplay/metro2033.pdf` — сценарий для чтения (115 стр.).
- `screenplay/metro2033.fountain` — исходник в формате Fountain.
- `screenplay/story-bible.md` — решения адаптации, структура, персонажи, журнал.
- `screenplay/step-outline.md` — список сцен с номерами страниц и главами книги.
- `screenplay/notes.md` — сверка с книгой, результаты проверок, синопсис.
- `screenplay/tools/render.py` — сборка PDF: `python3 screenplay/tools/render.py screenplay/metro2033.fountain screenplay/metro2033.pdf`.
- `screenplay/tools/scene_env.py` — лист требований к окружению по сценам: `python3 screenplay/tools/scene_env.py screenplay/metro2033.fountain --scenes 1-23 --out …`.
- `screenplay/env-review/` — отчёты критика окружения и паспорта мест.
- `.claude/skills/env-critic/` — правила независимого критика окружения (модели станций, рендеры сцен).
- `.claude/skills/` — скиллы сценариста ([jtydhr88/screenwriting-skills](https://github.com/jtydhr88/screenwriting-skills), MIT).
