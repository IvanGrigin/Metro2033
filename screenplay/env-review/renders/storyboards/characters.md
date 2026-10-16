# Персонажи и места — единые описания

Одно и то же описание повторяется в каждом английском промте, где герой в кадре: только так нейросеть держит внешность между кадрами.

| Кто | По сценарию | EN (для нейросети) |
|---|---|---|
| Артём | 24, бледный, худой, дозорный ВДНХ, старый автомат | Artyom: pale thin young man of 24, short dark hair, light stubble, worn grey padded jacket, old Kalashnikov |
| Пётр Андреич | 60, ватник | Pyotr: old man of 60, grey beard, weathered face, quilted vatnik jacket |
| Андрей | 40, старый чёрный берет, усы, улыбка | Andrei: man of 40, bushy mustache, old black beret, easy smile |
| Кирилл | 30, худой, всклокоченный, молчаливый | Kirill: thin man of 30, messy hair, silent |
| Бритый (Хантер) | ~45, высокий, плечистый, бритый наголо, длинный кожаный плащ | Hunter: tall broad-shouldered man of 45, shaved head, long black leather coat |
| Сухой (флешбэк) | молодой солдат, ~36 (сц. 2–3), ~39 (сц. 12) | Sukhoi: soldier, square jaw, short hair, army jacket |
| Сухой (настоящее) | 55, жилистый, седой, кашель курильщика | Sukhoi, now 55, wiry and grey-haired, smoker's cough |
| Хантер без плаща | костюм в палатке (сц. 16–17) | Hunter without his coat, black turtleneck, officer's belt with a TT pistol |
| Хантер в видении | весь в белом (сц. 21) | Hunter dressed all in white |
| Мать Артёма | лица не видно — волосы и руки (сц. 2) | the woman: Artyom's mother, face unseen, long hair and arms |
| Артём ребёнком | 5 лет (сц. 2–3), 8 лет (сц. 9–12) | young Artyom: pale thin boy of 5 / of 8, short dark hair |
| Женька | 9 лет во флешбэке (сц. 9–11), 25 лет (сц. 19, 24): румяный, болтливый | Zhenya: boy of 9, freckles, lively / Zhenya: ruddy-cheeked talkative young man of 25 |
| Виталик (Заноза) | 9 лет, волочёт двустволку (сц. 9–11) | Vitalik, skinny boy of 9 |
| Чёрные | нагие, кожа чёрная, лоснящаяся, огромные глаза без белков | the Dark Ones: naked humanoids with black glossy skin like oil, huge eyes with no whites |
| Старик-чаевод | за соседним столом фабрики (сц. 19) | old tea worker: old man with gnarled hands, slow worn movements |
| Александр Николаевич | дежурный по станции, 60 (сц. 23) | Alexander Nikolaevich: station duty officer, man of 60 |
| Командир каравана | 55, басовитый, усы щёткой (сц. 23–24) | Commander: heavy-set man of 55 with a brush mustache, deep voice |
| Никита Васильич | 50, бегающие глаза (сц. 24) | Nikita: man of 50 with shifty darting eyes |
| Бурбон | 30, коротко стрижен, небрит, кожаная куртка поверх тельняшки, всё время оглядывается через плечо (сц. 29–31) | Bourbon: man of 30 with a buzz cut and stubble, leather jacket over a striped sailor's undershirt, keeps glancing over his shoulder |
| Командир заставы | 45, камуфляж, застава 250-го метра к Проспекту Мира (сц. 31) | outpost commander: weathered man of 45 in camouflage |
| Дежурный заставы | молодой, приветливый, камуфляж (сц. 31) | outpost guard: friendly young man in camouflage |
| Дозорные Алексеевской | ватники с белой буквой «А» на спине (сц. 26) | Alekseevskaya sentries: men in padded jackets with a large white letter A painted on the back |
| Патрули Рижской | камуфляж (сц. 29) | Rizhskaya patrolmen in camouflage |

| Место | EN |
|---|---|
| Северный туннель ВДНХ, 250-й метр | abandoned Moscow metro tunnel, ribbed concrete walls, rusty rails and wooden sleepers, number 250 painted white on the wall, total darkness beyond a small campfire |

Общий стиль кадра (дописывается в конец каждого промта): `cinematic film still, 35mm, dark realistic, lit only by firelight and flashlights, deep shadows, muted brown palette`.

## Production: геометрия и свет

Для каждого сюжетного кадра обязательны [общие правила постановки](PRODUCTION.md) и [блок производственного промпта](production/production-prompt.txt). Фиксировать позиции источников, камеры и персонажей до генерации. Свет технических листов ракурсов не переносить в сцену. Исторические промпты требуют отдельной проверки.

## Главный референс Чёрных — v4

Пользователь заменил прежнее направление: [исходное изображение](references/game-frames-v4/dark-ones-user-reference.png). Тяжёлые согнутые силуэты, поднятые плечи, опущенные вытянутые головы и длинные руки; мелкая анатомия в исходнике неразличима. [Правила света v4](PRODUCTION-v4.md).
