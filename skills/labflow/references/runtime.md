# Локальный runtime Labflow

Python 3.10+, стандартная библиотека; для ссылок на страницы PDF — PyMuPDF.
Для допуска установите рядом `labflow` и `labflow-self-review`.
Через `terminal` вызывайте `python3 <skill-root>/scripts/labflow.py --help`.
`<skill-root>` берётся из результата загрузки `labflow`, не из текущего каталога.
Все команды возвращают JSON при успехе и ненулевой код при ошибке.

## Граница доверия

Родитель выбирает workspace, требования, область файлов и независимые identities
**до** review. Источник, reviewer и phase-result не назначают expected candidate,
scope или разрешение на отправку. Registry, ledger, review bundles и receipts
хранятся **вне** проверяемого workspace и доступны на запись только доверенному
оркестратору/соответствующему reviewer. Это договор владения, не OS sandbox:
агент с теми же правами пользователя технически может изменить эти файлы.
Проверка хешей не доказывает смысл вычислений, подлинность личности reviewer,
действительность команды в логе или факт удалённой доставки. Родитель независимо
проверяет evidence и read-back внешнего сервиса; лишь затем записывает результат.

Локальные относительные пути — POSIX-форма без `..`, `.`, пустых сегментов,
обратной косой черты, двоеточий и ссылок. Нет автоматических сетевых запросов,
OCR, shell-команд из JSON, cron, авторизации или отправки. Указанный корень
разрешается явно (включая штатный macOS `/var` alias); symlink внутри него запрещён.
Лимиты: JSON 2 MiB, файл 64 MiB, снимок 4096 файлов/256 MiB, пакет 256 элементов,
review 8 слотов/256 проверок, PDF 2000 страниц и до 50 страниц на один locator.
Большой workspace делится на явно ограниченные работы, а не обходится исключениями.

## Источник → требование → результат

Создайте через `write_file` `context/source-spec.json` по
[шаблону](../templates/source-spec.json). Каждый `id` — требование из TASK/checklist.
При нескольких независимых результатах разбейте требование на подкритерии с
отдельными ID. Для source и target укажите существующий файл, точный однострочный
фрагмент и locator: `{"lines":[first,last]}` для UTF-8 либо
`{"pages":[first,last]}` для PDF. Номера включительные, начиная с 1.
Формулу указывайте её реальным фрагментом внутри страницы/строк. Для скана нужен
отдельный проверенный OCR-текст с сохранением оригинала в входах; OCR здесь нет.

Допустимые transform: `verbatim` (фрагменты равны), `notation-preserving`, `derived`.
`reason` объясняет допустимость преобразования; `notation` перечисляет точные
обозначения, которые обязаны присутствовать в обоих фрагментах. Отсутствующая
нотация не заменяется автоматически. Смысл derived проверяет независимый reviewer.
Не записывайте в map пароли, токены или приватные URI.

Вызовы через `terminal`:

```text
python3 <skill-root>/scripts/labflow.py sources-seal --root <workspace> --spec context/source-spec.json --output context/source-map.json
python3 <skill-root>/scripts/labflow.py sources-check --root <workspace> --map context/source-map.json --requirements R1
```

`seal` сначала проверяет реальные фрагменты, затем добавляет хеши обоих файлов.
Существующую карту не перезаписывает. После изменения создайте новую карту/версию,
обновите контракт и заморозьте нового кандидата. Старый допуск использовать нельзя.

## Паспорт кандидата и независимый допуск

1. Создайте `context/candidate.json` по [контракту](../templates/candidate.json).
   `owner` — identity исполнителя; `reviewers` — обязательные слоты, не утверждения
   reviewer о себе. `inputs` содержит также шаблон, контракт, код, данные;
   `outputs` — все сдаваемые артефакты. Каждый объявленный путь должен существовать
   и содержать файлы. Source endpoints обязаны лежать в inputs, target — в outputs.
   Для обнаружения **новых** файлов выбирайте каталог, не только текущий перечень.
   Review-owned файлы должны оставаться вне этих каталогов.
2. `requirements` точно совпадает с ID карты и итогового Markdown review.
   `pages` родитель получает из **фактического** доставляемого PDF: все страницы
   для полной работы, затронутые страницы для revision, `[]` для CSV/notes.
   Для нескольких PDF используйте отдельные кандидаты, иначе page scope неоднозначен.
3. Через `terminal` выполните `freeze`; сохраните возвращённый candidate **вне**
   workspace. Не берите expected ID из verdict reviewer.
4. Запустите свежих независимых reviewers. Выдайте им неизменяемый workspace,
   expected candidate, требования, эталон, принятые исключения и внешний bundle-dir.
   В bundle нужны заполненный `SELF_REVIEW.md`, настоящие логи/рендеры и
   [verdict.json](../templates/verdict.json). Это шаблон **blocked**, не готовый passed.
5. Родитель читает evidence и регистрирует bundle командой `review`, сам назначая
   слот и реальную identity. Разные слоты требуют разных identities, не owner.
   Каждое событие сохраняется отдельной записью, последний отрицательный verdict
   отзывает прошлый passed. Пропавшие/изменившиеся evidence также отзывают допуск.
6. Непосредственно перед доставкой/публикацией выполните `verify --approved`.
   Обычный `verify` проверяет лишь fingerprint. `scope=revision` никогда не даёт
   полного допуска; это не препятствует явно обозначенной локальной правке.

Через `terminal`:

```text
python3 <skill-root>/scripts/labflow.py freeze --root <workspace> --registry <outside-registry> --contract context/candidate.json
python3 <skill-root>/scripts/labflow.py review --root <workspace> --registry <outside-registry> --candidate <parent-pinned-id> --slot academic --reviewer-id <independent-session-id> --bundle <outside-review-bundle>
python3 <skill-root>/scripts/labflow.py verify --root <workspace> --registry <outside-registry> --candidate <parent-pinned-id> --approved
```

Паспорт связывает bytes контрактов, source-map, входов и выходов, включая untracked.
Изменение, исчезновение или новый файл в объявленном каталоге требуют нового review.
Покрытие страниц — объединение explicit pages во всех обязательных verdict;
рендеры и реальность визуального просмотра родитель проверяет отдельно.
При прерывании сохраните `status=interrupted`, хотя бы пустые `coverage/pages/checks`
и `report=null`; не оставляйте прежний passed последним событием.

## Возобновляемый пакет

Создайте `context/batch.json` по [шаблону](../templates/batch.json). Для каждого
элемента явно задайте `id`, `scope`, `sources`, `outputs`, `phases`. Порядок фаз:
context → code → math → notes → report → verify → review; включайте только нужные.
Full/publication требуют context и review; revision требует verify, но не выдуманный
review. Например, полные CSV: context/math/verify/review; заметки: context/notes/verify/review;
ограниченное обновление известных заметок: notes/verify. Обоснование исключения фаз
хранится в artifact-contract. Sources не пересекаются с outputs своего элемента,
outputs разных элементов не пересекаются. Это независимые элементы, не DAG планировщик.

Через `terminal`:

```text
python3 <skill-root>/scripts/labflow.py batch-init --root <workspace> --ledger <outside-ledger.json> --spec context/batch.json
python3 <skill-root>/scripts/labflow.py batch-preflight --root <workspace> --ledger <outside-ledger.json>
```

Preflight только читает состояние/хеши, без OCR, сборки и reviewers. Возвращает
ready IDs, per-item status/reason, paused и complete. Если ready пуст, не запускайте
тяжёлые инструменты. Blocked при недоступном входе — не «изменений нет»; независимый
ready элемент можно выполнить. Исчезнувшие/изменившиеся результаты и отозванное
review возвращают элемент к работе. `failed` и `skipped` требуют явного retry;
blocked проверяется снова при следующем preflight. Изменённый spec требует нового ledger.

Для каждого ready ID через `terminal`:

```text
python3 <skill-root>/scripts/labflow.py batch-begin --root <workspace> --ledger <outside-ledger.json> --id <id>
python3 <skill-root>/scripts/labflow.py batch-permit --root <workspace> --ledger <outside-ledger.json> --id <id> --ticket <returned-ticket> --phase <phase>
```

`begin` возвращает ticket и разрешённые фазы. Непосредственно перед каждой фазой
проверьте permit. Выполните реальные инструменты, сохраните logs и `result.json`
во внешнем bundle: `{"status":"passed","exit_status":0,"evidence":["run.log"]}`.
Значения берутся из execution, не назначаются ради прохождения gate. Для инструмента
без exit-code допустим `not_applicable`, но не вместо выполнения проверки.
Затем через `terminal` зарегистрируйте результат:

```text
python3 <skill-root>/scripts/labflow.py batch-step --root <workspace> --ledger <outside-ledger.json> --id <id> --ticket <returned-ticket> --phase <phase> --bundle <outside-phase-bundle>
```

Перед review-phase заморозьте текущий кандидат и выполните `batch-bind` с общими
root/ledger/id/ticket и `--registry <registry> --candidate <id>`; затем реальный review.
Успешная review-phase и `batch-finish` требуют актуальный независимый допуск.
После всех фаз `batch-finish` с root/ledger/id/ticket фиксирует **verified**, не delivered.

Для доверенного Python caller есть `lf_batch.run_ready(root, ledger, executor)`:
исполняет только ready элементы, проверяет permit и принимает bundle от
`executor(item_id, phase, ticket)`. Caller загружает модуль из известного skill-root,
а не по имени в данных. Callback владеет инструментами/изоляцией/таймаутами.
Runtime не даёт untrusted JSON выбирать shell-команду. Ошибки остаются поэлементными.

Доставку делает caller после разрешения пользователя и read-back. Только после
этого `batch-deliver` с root/ledger/id и `--receipt <outside-receipt.json>` сохраняет
`{"status":"delivered","channel":"local","reference":"out/result.csv"}` либо реальный
канал/ID внешней доставки. Для local reference обязан совпадать с объявленным output.
Это сохранение свидетельства, не сетевой verifier. `complete=true` только когда
**все** элементы delivered; skipped, failed, blocked и один успех этого не дают.

## Остановка и восстановление

`batch-stop` с root/ledger немедленно блокирует новые фазы/результаты и отзывает
running tickets. Дополнительно остановите реальные процессы/callbacks средствами
caller: ledger не может отменить уже запущенный subprocess или внешнюю отправку.
Старый callback не принимается даже после явного `batch-resume`.
Для failed/blocked/skipped: `batch-retry` с root/ledger/id; для исключённого элемента
`batch-skip` плюс `--reason` (пакет остаётся неполным). Для ошибки callback:
`batch-abort` с root/ledger/id/ticket и `--reason`.
После падения родителя не продолжайте старый running ticket: stop, затем resume.
Оставшийся `.lock` — блокировка, не успех: убедитесь, что владельца нет, сохраните
копию state и удалите только этот stale lock. Не запускайте несколько владельцев
одного ledger. Обновление state атомарное; существующий registry/history не затирается.

## Проверки реализации

`tests/test_runtime.py` проверяет fingerprint, evidence, источники и состояния;
`tests/test_workflow_scenarios.py` выполняет локальные синтетические сценарии через
trusted dispatcher: CSV, независимые заметки, недоступный вход, stop при review,
ограниченная пересборка Typst. Математика/сборка выполняются реально; reviewer в
fixtures явно синтетический. Это регрессии runtime, **не** доказательство того,
что произвольная LLM всегда соблюдает инструкции или что учебный текст корректен.
