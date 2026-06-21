# PLAN.md

## 1. Цель и границы реализации

`mergetyp` v0.1 — Python 3.12 CLI-утилита для пакетной генерации PDF через внешний бинарник `typst`.

Утилита принимает Typst-шаблон `.typ`, который экспортирует `render(record)`, и файл данных `.csv`, `.json`, `.yaml` или `.yml`. На каждую запись создается временный Typst-файл вида:

```typst
#import "template.typ": render
#render((name: "Alice", course: "Typst",))
```

Ключевой принцип: приложение НЕ делает текстовую подстановку в шаблон. Python-значения конвертируются в настоящие Typst-литералы и передаются в `render(record)`.

В v0.1 запрещены Web API, FastAPI, БД, SQLAlchemy, брокеры задач, Redis, asyncio, watch mode, GUI/TUI, Excel, TOML, HTTP-источники, PNG/SVG-экспорт, email, webhooks, плагины, телеметрия, конфигурационные файлы и логирование в файл.

## 2. Архитектура и стек

### 2.1. Runtime-стек

- Python `3.12`.
- Typst CLI как внешний бинарник `typst`.
- `argparse` для CLI.
- `subprocess.run` для `typst compile`.
- `concurrent.futures.ThreadPoolExecutor` для параллельного запуска внешних процессов.
- `logging` для всего пользовательского вывода.
- Стандартная библиотека: `csv`, `json`, `pathlib`, `tempfile`, `os`, `shutil`, `math`, `re`, `dataclasses`, `typing`.
- `pydantic>=2.8,<3` для строгой валидации настроек и входных записей.
- `pyyaml>=6.0,<7` для YAML.

### 2.2. Dev-стек

- `pytest>=8.0`.
- `ruff>=0.5`.
- `mypy>=1.10`.
- `types-PyYAML>=6.0`.
- GitHub Actions CI.

### 2.3. Запрещенные зависимости

Не добавлять: FastAPI, Starlette, aiohttp, Click, Typer, Rich, Tqdm, Pandas, Jinja2, OpenPyXL, AnyIO, HTTP-клиенты, ORM, DI-контейнеры, asyncio subprocess, ProcessPoolExecutor, Celery, Taskiq, Redis, Alembic.

### 2.4. Архитектурный паттерн

Использовать слоистую CLI-архитектуру с явными границами доверия:

1. `cli.py` разбирает аргументы, настраивает логирование, создает `RuntimeSettings`, конвертирует исключения в exit code.
2. `data.py` читает CSV/JSON/YAML и валидирует записи через `contracts.py`.
3. `runner.py` применяет batch-оркестрацию, dry-run, поиск `typst`, последовательный или параллельный запуск.
4. `output.py` строит `RenderJob`, проверяет коллизии до рендеринга, пишет PDF атомарно.
5. `render.py` создает временный `.typ` рядом с шаблоном и вызывает `typst compile`.
6. `typst_value.py` преобразует Python-значения в Typst-литералы.
7. `naming.py` строит безопасные имена PDF без поддиректорий.

Поток данных:

```text
argv
  -> argparse.Namespace
  -> RuntimeSettings
  -> load_data(...) -> List[Dict[str, Any]]
  -> select_records(offset, limit)
  -> build_render_jobs(...) with collision resolution
  -> dry-run results OR typst render jobs
  -> write_pdf_atomic(...)
  -> RenderResult[]
  -> summary + exit code
```

## 3. Структура проекта

Создать ровно следующую структуру. Не добавлять production-модули вне `src/mergetyp/` без изменения `SPEC.md`.

```text
mergetyp/
├── SPEC.md
├── PLAN.md
├── README.md
├── LICENSE
├── pyproject.toml
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   └── mergetyp/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── contracts.py
│       ├── data.py
│       ├── exceptions.py
│       ├── log.py
│       ├── naming.py
│       ├── output.py
│       ├── render.py
│       ├── runner.py
│       ├── typst_value.py
│       └── py.typed
├── tests/
│   ├── test_cli.py
│   ├── test_contracts.py
│   ├── test_data.py
│   ├── test_naming.py
│   ├── test_output.py
│   ├── test_render.py
│   ├── test_runner.py
│   └── test_typst_value.py
└── examples/
    ├── certificate/
    │   ├── template.typ
    │   ├── data.csv
    │   └── README.md
    └── invoice/
        ├── template.typ
        └── data.json
```

### 3.1. Ответственность ключевых файлов

- `pyproject.toml` — metadata пакета, runtime/dev зависимости, console script, настройки pytest/ruff/mypy.
- `.gitignore` — исключения Python build/cache, output PDF-директорий, временных Typst-файлов.
- `.github/workflows/ci.yml` — lint, typecheck, unit tests, установка Typst и smoke-тесты examples.
- `README.md` — английская пользовательская документация и CLI reference.
- `LICENSE` — MIT license с `TBD` как автором до публикации.
- `src/mergetyp/__init__.py` — получение `__version__` через `importlib.metadata`.
- `src/mergetyp/__main__.py` — минимальный entrypoint `sys.exit(main())`.
- `src/mergetyp/cli.py` — `argparse`, `RuntimeSettings`, загрузка данных, отчет, exit codes.
- `src/mergetyp/contracts.py` — Pydantic-модели, dataclass-контракты, типы политики коллизий.
- `src/mergetyp/data.py` — загрузка CSV/JSON/YAML, CSV coercion, нормализация records.
- `src/mergetyp/exceptions.py` — ожидаемые доменные исключения с `exit_code`.
- `src/mergetyp/log.py` — настройка logger `mergetyp`.
- `src/mergetyp/naming.py` — построение и sanitization имен PDF.
- `src/mergetyp/output.py` — создание jobs, проверка/разрешение коллизий, атомарная запись PDF.
- `src/mergetyp/render.py` — поиск Typst, временный `.typ`, `subprocess.run`, возврат PDF bytes.
- `src/mergetyp/runner.py` — batch-оркестрация, dry-run, ThreadPoolExecutor.
- `src/mergetyp/typst_value.py` — конвертация Python values в Typst source literals.
- `src/mergetyp/py.typed` — marker для typed package.
- `tests/*.py` — unit-тесты бизнес-логики и CLI-поведения.
- `examples/certificate/*` — CSV пример для 3 сертификатов.
- `examples/invoice/*` — JSON пример с вложенными `items`.

## 4. Контракты и интерфейсы

### 4.1. Exit codes

| Код | Значение |
|---:|---|
| `0` | Все записи успешно обработаны или `--dry-run` прошел без ошибок |
| `1` | Ошибка валидации, неподдерживаемый формат, Typst error, коллизия, timeout, запись файлов |
| `2` | Не найден шаблон или файл данных |
| `130` | Ctrl+C |

Для ожидаемых ошибок запрещено показывать traceback.

### 4.2. Исключения

`exceptions.py` должен содержать только ожидаемые доменные исключения:

```python
class MergetypError(Exception): ...
class InputFileNotFoundError(MergetypError): exit_code = 2
class TypstNotFoundError(MergetypError): ...
class DataValidationError(MergetypError): ...
class FilenamePatternError(MergetypError): ...
class OutputCollisionError(MergetypError): ...
class OutputWriteError(MergetypError): ...
class TypstCompileError(MergetypError): ...
class TypstTimeoutError(MergetypError): ...
```

Контракт: низкоуровневые модули выбрасывают конкретное исключение; `cli.py` ловит `MergetypError`, логирует `error.message` и возвращает `error.exit_code`.

### 4.3. Data models

`contracts.py` фиксирует эти интерфейсы:

```python
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


CollisionPolicy = Literal["error", "overwrite", "rename"]
DEFAULT_JOBS = min(8, os.cpu_count() or 4)

class RuntimeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    template_path: Path = Field(description="Path to Typst template")
    data_path: Path = Field(description="Path to input data file")
    output_dir: Path = Field(default=Path("out"), description="Output directory")
    name_pattern: str = Field(default="{index}.pdf", min_length=1)
    jobs: int = Field(default=DEFAULT_JOBS, ge=1, le=64)
    compile_timeout: float = Field(default=60.0, gt=0.0, le=3600.0)
    no_coerce: bool = Field(default=False)
    dry_run: bool = Field(default=False)
    limit: Optional[int] = Field(default=None, ge=1)
    offset: int = Field(default=0, ge=0)
    encoding: str = Field(default="utf-8", min_length=1)
    collision: CollisionPolicy = Field(default="error")
    verbose: bool = Field(default=False)
    quiet: bool = Field(default=False)

@dataclass(frozen=True)
class RenderJob:
    record_index: int
    record: Dict[str, Any]
    output_path: Path

@dataclass(frozen=True)
class RenderResult:
    record_index: int
    output_path: Path
    ok: bool
    error_message: Optional[str] = None
```

`RuntimeSettings` должен реализовать валидаторы `validate_name_pattern` и `validate_logging_flags` из `SPEC.md`.
`RecordBatchModel` валидирует `List[Dict[str, Any]]`, рекурсивно разрешая только `None`, `str`, `bool`,
`int`, `float`, `list`, `dict` со строковыми ключами. Пользовательская schema-валидация полей не входит в v0.1.

### 4.4. Модульные API

- `log.configure_logging(verbose: bool, quiet: bool) -> logging.Logger`.
- `data.detect_format(path: Path) -> str`.
- `data.coerce_csv_value(raw: str) -> Optional[Union[str, int, float, bool]]`.
- `data.load_data(path: Path, coerce: bool, encoding: str) -> List[Dict[str, Any]]`.
- `typst_value.is_typst_identifier(key: str) -> bool`.
- `typst_value.format_float(value: float) -> str`.
- `typst_value.to_typst(value: Any) -> str`.
- `naming.sanitize_filename(name: str) -> str`.
- `naming.build_filename(pattern: str, record: Dict[str, Any], record_index: int) -> str`.
- `output.build_render_jobs(records, output_dir, name_pattern, collision, logger) -> List[RenderJob]`.
- `output.resolve_collisions(jobs, collision, logger) -> List[RenderJob]`.
- `output.write_pdf_atomic(output_path: Path, pdf_bytes: bytes) -> None`.
- `render.find_typst() -> str`.
- `render.render_record(template_path, record, typst_bin, compile_timeout) -> bytes`.
- `runner.run_one_job(job, settings, typst_bin, logger) -> RenderResult`.
- `runner.run_batch(settings, records, logger) -> List[RenderResult]`.
- `cli.build_parser() -> argparse.ArgumentParser`.
- `cli.build_runtime_settings(args: argparse.Namespace) -> RuntimeSettings`.
- `cli.select_records(records, offset, limit) -> List[Dict[str, Any]]`.
- `cli.report_results(results, dry_run, logger) -> int`.
- `cli.run_main(argv: Optional[List[str]]) -> int`.
- `cli.main(argv: Optional[List[str]] = None) -> int`.

### 4.5. Typst literal contract

| Python | Typst |
|---|---|
| `None` | `none` |
| `True` / `False` | `true` / `false` |
| `int` | decimal integer |
| finite `float` | decimal without scientific notation |
| `nan`, `inf`, `-inf` | `none` |
| `str` | double-quoted string with escaped `\`, `"`, `\n`, `\r`, `\t` |
| empty `list` / `tuple` | `()` |
| non-empty `list` / `tuple` | `(item1, item2,)` with trailing comma |
| empty `dict` | `(:)` |
| safe ASCII key | `(name: "Alice",)` |
| unsafe key | `("full name": "Alice",)` |

Safe key regex: `^[A-Za-z_][A-Za-z0-9_]*$`. Do not use `str.isidentifier`, because Unicode keys must be quoted.

### 4.6. Filename contract

- `{index}` is always available and is one-based.
- Record fields are available as `{field_name}`.
- Missing field raises `FilenamePatternError` before rendering.
- If rendered name does not end with `.pdf`, append `.pdf`.
- Replace `[<>:"/\\|?*\x00-\x1f]` with `_`.
- Strip leading/trailing whitespace after replacement.
- If sanitized stem is empty, use `output.pdf`.
- Do not support subdirectories in `--name-pattern`.

### 4.7. Typst subprocess contract

`render_record` must call:

```text
typst compile --root <template_dir> --format pdf <temporary_typ_file> -
```

Required `subprocess.run` options: `capture_output=True`, `check=False`, `timeout=compile_timeout`, `shell=False` by omission.

Temporary `.typ` files are created in `template_path.parent` with prefix `.mergetyp_gen_` and must be deleted in `finally`.

### 4.8. Testing contract

- Все unit-тесты должны проходить без установленного `typst`, кроме явно помеченных интеграционных тестов.
- В `tests/test_render.py` monkeypatch обязателен для `subprocess.run`, `tempfile.mkstemp`/`shutil.which` использовать
  monkeypatch там, где тестируется соответствующая ветка.
- В `tests/test_runner.py` и `tests/test_cli.py` monkeypatch использовать для `find_typst`, `render_record`,
  `write_pdf_atomic`, `load_data` и `run_batch`, чтобы не запускать реальный Typst и не зависеть от окружения.
- Интеграционные тесты с реальным Typst помечать `@pytest.mark.skipif(shutil.which("typst") is None, reason="typst not installed")`.

## 5. Пошаговый план реализации

### Фаза 1. Инициализация и настройка окружения

- [ ] Шаг 1: Создать базовую структуру директорий: `.github/workflows/`, `src/mergetyp/`, `tests/`, `examples/certificate/`, `examples/invoice/`. Не создавать дополнительных production-директорий.
- [ ] Шаг 2: Создать `pyproject.toml` с `setuptools>=68`, package name `mergetyp`, version `0.1.0`, Python `>=3.12`, runtime dependencies `pydantic>=2.8,<3` и `pyyaml>=6.0,<7`, dev dependencies `pytest`, `ruff`, `mypy`, `types-PyYAML`, console script `mergetyp = "mergetyp.cli:main"`, package discovery from `src`.
- [ ] Шаг 3: В `pyproject.toml` настроить `ruff` с `line-length = 120`, `target-version = "py312"`, `select = ["E", "F", "I", "B", "UP", "SIM"]`, `ignore = ["UP006", "UP007", "UP045"]`; настроить `mypy` strict для `src`; настроить pytest `testpaths = ["tests"]`.
- [ ] Шаг 4: Создать `.gitignore` с исключениями Python cache/build, `.venv`, pytest/mypy/ruff cache, `out/`, `**/out/`, `.mergetyp_gen_*`, `*.tmp`, `.DS_Store`, `Thumbs.db`.
- [ ] Шаг 5: Создать `LICENSE` с MIT license и `Copyright (c) 2026 TBD`.
- [ ] Шаг 6: Создать пустой marker `src/mergetyp/py.typed`.
- [ ] Шаг 7: Создать `src/mergetyp/__init__.py`, который получает `__version__` через `importlib.metadata.version("mergetyp")` и использует fallback `"0.1.0"` при `PackageNotFoundError`.
- [ ] Шаг 8: Создать `src/mergetyp/__main__.py` только с `sys.exit(main())`; не добавлять бизнес-логику.
- [ ] Шаг 9: Создать `src/mergetyp/log.py` с logger name `mergetyp`, очисткой handlers, `StreamHandler(sys.stderr)`, formatter `%(message)s`, режимами `quiet -> ERROR`, `verbose -> DEBUG`, default `INFO`.
- [ ] Шаг 10: Создать examples: certificate Typst template + CSV + README, invoice Typst template + JSON. Certificate и invoice templates скопировать из `SPEC.md` раздела 4.15 без переписывания; для invoice сохранить `align(right)`, `grid.cell`, escaped `billing\@...`.
- [ ] Шаг 11: Создать `README.md` на английском после examples: назначение, требование установить Typst CLI, install, quick start, `render(record)` contract, data formats, CLI reference, exit codes, security note, examples, license.
- [ ] Шаг 12: Создать `.github/workflows/ci.yml` с Python 3.12 matrix, `pip install -e ".[dev]"`, `ruff check .`, `mypy src`, `pytest -q`, установкой Typst `v0.15.0`, smoke certificate и smoke invoice.

### Фаза 2. Базовые интерфейсы и модели данных

- [ ] Шаг 13: В `src/mergetyp/exceptions.py` реализовать `MergetypError` с `message` и default `exit_code = 1`; добавить `InputFileNotFoundError` с `exit_code = 2` и остальные доменные исключения из раздела 4.2.
- [ ] Шаг 14: В `src/mergetyp/contracts.py` добавить `CollisionPolicy`, `DEFAULT_JOBS`, `RuntimeSettings`, `RecordBatchModel`, `RenderJob`, `RenderResult`, `validate_record_batch`.
- [ ] Шаг 15: В `RuntimeSettings` включить `ConfigDict(extra="forbid", strict=True)`, валидировать `jobs` диапазоном `1..64`, `compile_timeout` диапазоном `(0, 3600]`, `limit >= 1`, `offset >= 0`, `encoding` non-empty.
- [ ] Шаг 16: В `RuntimeSettings.validate_name_pattern` проверить синтаксис Python format string через `value.format_map({"index": "1"})`: `KeyError` считать допустимым отсутствующим record-полем для последующей проверки в `naming.py`, `ValueError` превращать в validation error.
- [ ] Шаг 17: В `RuntimeSettings.validate_logging_flags` запретить одновременные `--verbose` и `--quiet`.
- [ ] Шаг 18: В `RecordBatchModel` рекурсивно валидировать records: верхний уровень непустой `List[Dict[str, Any]]`, все ключи строковые, значения только `None`, `str`, `bool`, `int`, `float`, `list`, `dict` со строковыми ключами.
- [ ] Шаг 19: В `contracts.py` использовать `isinstance` только для обработки внешних данных; не добавлять ORM, API schemas или FastAPI-модели.
- [ ] Шаг 20: Создать `tests/test_contracts.py`: проверить валидные settings, запрет extra fields, конфликт `verbose`/`quiet`, пустой batch, non-string key, unsupported object, nested supported values.

### Фаза 3. Независимая бизнес-логика

#### 3.1. Загрузка данных

- [ ] Шаг 21: В `src/mergetyp/data.py` реализовать `detect_format`: `.csv -> "csv"`, `.json -> "json"`, `.yaml/.yml -> "yaml"`, иначе `DataValidationError` с понятным сообщением.
- [ ] Шаг 22: Реализовать `coerce_csv_value`: `"" -> None`, case-insensitive `true/false -> bool`, integers without leading zeros -> `int`, decimal floats without scientific notation -> `float`, остальное остается строкой. Обязательно сохранить `"01234"` и `"1e-5"` строками; `"0"` должен стать `int`.
- [ ] Шаг 23: Реализовать `load_csv(path, coerce, encoding)`: открыть с `newline=""` и заданным `encoding`, использовать `csv.DictReader`, поймать `UnicodeError`, `csv.Error`, `OSError`, при лишних ячейках с key `None` выбросить `DataValidationError`.
- [ ] Шаг 24: В `load_csv` после чтения вызвать `validate_record_batch`; пустой файл или пустой список должен стать `DataValidationError`.
- [ ] Шаг 25: Реализовать `load_json(path)`: читать `utf-8`, поймать `json.JSONDecodeError` и `OSError`, top-level object завернуть в список, top-level list проверить как список объектов, scalar отклонить.
- [ ] Шаг 26: Реализовать `load_yaml(path)`: использовать только `yaml.safe_load`, читать `utf-8`, поймать `yaml.YAMLError` и `OSError`, `None`/scalar отклонить, mapping завернуть в список, sequence проверить как список mappings.
- [ ] Шаг 27: Реализовать `load_data(path, coerce, encoding)` как dispatcher по `detect_format`.
- [ ] Шаг 28: Создать `tests/test_data.py` с обязательными кейсами CSV empty cell, bool, int including `-7` and `0`, leading zero, float, scientific notation, `coerce=False`/`--no-coerce` keeps all CSV values as strings including empty cell as `""`, JSON object/list/scalar/invalid, YAML mapping/sequence/invalid, unsupported extension, empty records.

#### 3.2. Typst value conversion

- [ ] Шаг 29: В `src/mergetyp/typst_value.py` определить `TYPST_IDENTIFIER_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]*$"` и `is_typst_identifier`.
- [ ] Шаг 30: Реализовать `escape_string` и `quote_string`: экранировать backslash первым, затем double quote, newline, carriage return, tab.
- [ ] Шаг 31: Реализовать `format_float`: для non-finite вернуть `"none"`, для finite подбирать decimal precision `1..17`, не использовать `repr(float)`, не выводить scientific notation, `-0.0` нормализовать в `0.0`; если round-trip не найден, вернуть значение последней precision, не выбрасывать ошибку.
- [ ] Шаг 32: Реализовать `to_typst`: порядок проверок `None`, `bool`, `int`, `float`, `str`, `list`, `tuple`, `dict`, `datetime.datetime`, `datetime.date`, иначе `DataValidationError`.
- [ ] Шаг 33: Реализовать массивы как `()` для empty и `(a, b,)` с trailing comma для non-empty; tuple обрабатывать как list.
- [ ] Шаг 34: Реализовать dict как `(:)` для empty; safe ASCII keys писать без кавычек, остальные ключи quote-string; всегда trailing comma; не использовать `str.isidentifier`.
- [ ] Шаг 35: Создать `tests/test_typst_value.py` с обязательными кейсами `None`, bool, int, finite floats, `1e-5`, `nan`, `inf`, `159.9`, `1758.9`, `0.1 + 0.2`, escaping, lists, tuple, nested lists, dicts, Unicode/dash keys, nested dict, unsupported object.

#### 3.3. Filename generation

- [ ] Шаг 36: В `src/mergetyp/naming.py` определить illegal filename regex `[<>:"/\\|?*\x00-\x1f]`, `PDF_SUFFIX = ".pdf"`, `DEFAULT_FILENAME = "output"`.
- [ ] Шаг 37: Реализовать `StrictFormatDict.__missing__`, который выбрасывает `FilenamePatternError` с missing field и списком доступных полей.
- [ ] Шаг 38: Реализовать `sanitize_filename`: заменить illegal/control chars на `_`, сделать `strip()`, если результат пустой вернуть `"output"`.
- [ ] Шаг 39: Реализовать `build_filename`: создать mapping из record keys и one-based `index`, выполнить `pattern.format_map`, поймать `ValueError`, добавить `.pdf` если отсутствует, затем sanitize. Не разрешать `/` и `\` как path separators.
- [ ] Шаг 40: Создать `tests/test_naming.py`: default `{index}.pdf`, field pattern, missing field, append `.pdf`, illegal chars, slash/backslash replacement, empty sanitized name -> `output.pdf`.

#### 3.4. Output jobs and atomic writes

- [ ] Шаг 41: В `src/mergetyp/output.py` реализовать `build_render_jobs`: создать `output_dir` через `mkdir(parents=True, exist_ok=True)`, при `OSError` выбросить `OutputWriteError`, для каждой записи построить one-based `RenderJob`, output path сделать absolute via `.resolve()`.
- [ ] Шаг 42: Реализовать `collect_collision_messages`: обнаруживать batch duplicates и существующие файлы до рендеринга.
- [ ] Шаг 43: Реализовать `resolve_collisions`: policy `error` выбрасывает `OutputCollisionError`, `overwrite` логирует warnings и оставляет пути, `rename` вызывает rename logic.
- [ ] Шаг 44: Реализовать `rename_collisions`: добавлять suffix `_2`, `_3`, ... к stem, проверять и уже назначенные batch paths, и существующие filesystem paths, никогда не выбирать существующий файл.
- [ ] Шаг 45: Реализовать `write_pdf_atomic`: tmp path рядом с target как `<filename>.tmp` в той же директории, не в `/tmp`; `parent.mkdir`, `write_bytes` только во временный файл, `os.replace`, при `OSError` выбросить `OutputWriteError`, в `finally` удалить tmp через `missing_ok=True`.
- [ ] Шаг 46: Создать `tests/test_output.py`: atomic success, tmp removed after success, OSError cleanup and `OutputWriteError`, collision error on duplicate names, collision error on existing file, mixed duplicate+existing collision reports both messages, rename suffix, overwrite keeps path and logs warning.

#### 3.5. Typst rendering

- [ ] Шаг 47: В `src/mergetyp/render.py` реализовать `find_typst` через `shutil.which("typst")`; если `None`, выбросить `TypstNotFoundError` с сообщением про установку Typst CLI.
- [ ] Шаг 48: Реализовать `render_record`: вычислить `root = template_path.parent`, `template_name = template_path.name`, source с `#import "<template_name>": render` и `#render(<to_typst(record)>)`.
- [ ] Шаг 49: Создать temporary `.typ` через `tempfile.mkstemp(prefix=".mergetyp_gen_", suffix=".typ", dir=str(root))`; при `PermissionError` выбросить `OutputWriteError` с понятным сообщением про write permissions в директории шаблона.
- [ ] Шаг 50: Записать временный `.typ` через `os.fdopen(..., "w", encoding="utf-8")`.
- [ ] Шаг 51: Вызвать `subprocess.run` только списком аргументов: `[typst_bin, "compile", "--root", str(root), "--format", "pdf", str(temporary_path), "-"]`, с `capture_output=True`, `check=False`, `timeout=compile_timeout`.
- [ ] Шаг 52: При `subprocess.TimeoutExpired` выбросить `TypstTimeoutError`; temporary file удалить в `finally`.
- [ ] Шаг 53: Если `returncode != 0`, декодировать `stderr` как `utf-8` with `errors="replace"` и выбросить `TypstCompileError`, включив stderr в сообщение.
- [ ] Шаг 54: Вернуть `result.stdout` как PDF bytes; не писать итоговый PDF в `render.py`.
- [ ] Шаг 55: Создать `tests/test_render.py`: `find_typst` success/fail, subprocess args include `--root`, timeout passed, non-zero -> `TypstCompileError`, timeout -> `TypstTimeoutError`, temporary file cleanup after success/failure, PermissionError -> `OutputWriteError`. Реальный `typst` не вызывать; `subprocess.run` и `shutil.which` проверять через monkeypatch.

### Фаза 4. API / CLI / Интеграция слоев

#### 4.1. Runner

- [ ] Шаг 56: В `src/mergetyp/runner.py` реализовать `run_one_job`: вызвать `render_record`, затем `write_pdf_atomic`; `MergetypError` превращать в `RenderResult(ok=False, error_message=error.message)`, неожиданный `Exception` логировать через `logger.exception` и вернуть failed `RenderResult`.
- [ ] Шаг 57: Реализовать `run_jobs_sequential` простым циклом по jobs.
- [ ] Шаг 58: Реализовать `run_jobs_parallel`: `ThreadPoolExecutor(max_workers=settings.jobs)`, submit всех jobs, сбор через `as_completed`, не останавливать весь batch при ошибке одной записи.
- [ ] Шаг 59: Реализовать `run_dry_run`: логировать `dry-run: record #N -> path`, вернуть successful `RenderResult` для каждого job, не вызывать `find_typst`, `render_record` или `write_pdf_atomic`.
- [ ] Шаг 60: Реализовать `run_batch`: проверить `template_path.is_file()` и `data_path.is_file()` с `InputFileNotFoundError`, даже при аналогичных проверках в `cli.py`, потому что `SPEC.md` задает обе точки проверки; построить jobs; если empty, `DataValidationError`; при dry-run вернуть `run_dry_run`; иначе `find_typst`; если `settings.jobs == 1` или один job — sequential, иначе parallel; вернуть results sorted by `record_index`.
- [ ] Шаг 61: Создать `tests/test_runner.py`: dry-run does not call render, sequential processes all jobs, parallel processes all jobs, failed job does not hide other failures, results sorted by `record_index`. Реальный `typst` не вызывать; `find_typst`, `render_record` и `write_pdf_atomic` изолировать monkeypatch.

#### 4.2. CLI

- [ ] Шаг 62: В `src/mergetyp/cli.py` реализовать argparse validators `positive_int`, `non_negative_int`, `positive_float`, которые выбрасывают `argparse.ArgumentTypeError` с конкретным сообщением.
- [ ] Шаг 63: Реализовать `build_parser` с positional `TEMPLATE DATA` и опциями `-o/--output`, `--name-pattern`, `--no-coerce`, `-j/--jobs`, `--compile-timeout`, `--dry-run`, `--limit`, `--offset`, `--encoding`, `--collision {error,overwrite,rename}`, `--verbose`, `--quiet`, `--version`.
- [ ] Шаг 64: Реализовать `build_runtime_settings`: строки путей из argparse обязательно преобразовать в `Path(...).resolve()` до создания strict Pydantic `RuntimeSettings`.
- [ ] Шаг 65: Реализовать `select_records`: применить `offset`, затем `limit`; если выборка пустая, выбросить `DataValidationError("ERROR: selected record range contains no records.")`.
- [ ] Шаг 66: Реализовать `report_results`: посчитать successful/failed, залогировать `result.error_message` для failed, выбрать `action = "planned" if dry_run else "generated"`, summary логировать параметризованно как `logger.info("mergetyp: done. %s/%s PDF(s) %s.", success_count, total_count, action)`, вернуть `1` если есть ошибки, иначе `0`.
- [ ] Шаг 67: Реализовать `run_main`: parser -> logging -> settings -> existence checks -> `load_data(coerce=not settings.no_coerce)` -> `select_records` -> `run_batch` -> `report_results`. Не вызывать `sys.exit` внутри `run_main`.
- [ ] Шаг 68: Реализовать `main`: ловить `KeyboardInterrupt` -> log `mergetyp: interrupted by user` and return `130`; `InputFileNotFoundError` -> return `2`; other `MergetypError` -> return `1`; Pydantic `ValidationError` -> log invalid CLI settings and return `1`; unexpected `Exception` -> `logger.exception("ERROR: unexpected fatal error")` and return `1`.
- [ ] Шаг 69: Создать `tests/test_cli.py`: missing template `2`, missing data `2`, invalid `--jobs 0`, invalid `--compile-timeout 0`, `--verbose` + `--quiet`, Pydantic `ValidationError` on settings returns `1`, expected `MergetypError` exit code, `KeyboardInterrupt` `130`, unexpected exception logs and returns `1`, offset beyond records `1`, limit+offset empty `1`. `load_data`/`run_batch` изолировать monkeypatch там, где тест не проверяет их напрямую.

### Фаза 5. Документация, примеры, CI и валидация

- [ ] Шаг 70: Проверить `README.md`: не обещать hosted version, не упоминать web roadmap как обязательство, ясно указать security note про trusted Typst templates.
- [ ] Шаг 71: Проверить examples вручную на соответствие contract `render(record)`; certificate должен использовать safe keys via `record.name`, invoice должен использовать `record.at(...)` для бизнес-полей.
- [ ] Шаг 72: Создать или обновить интеграционные/smoke проверки так, чтобы unit tests не требовали установленный `typst`; реальные Typst smoke-команды оставить в CI после установки Typst. Если добавляются pytest-интеграционные тесты с реальным Typst, пометить их `@pytest.mark.skipif(shutil.which("typst") is None, reason="typst not installed")`.
- [ ] Шаг 73: Убедиться, что все Python public functions/classes/methods имеют Google Style docstring без точки в конце последнего предложения описания.
- [ ] Шаг 74: Проверить стиль кода: imports только в начале, группы imports standard/external/internal, wildcard imports отсутствуют, относительные импорты отсутствуют, built-in generics `list[int]`/`dict[str, object]` не используются, несколько присваиваний в одной строке отсутствуют.
- [ ] Шаг 75: Проверить запреты: нет `print` в `src/`, нет `shell=True`, нет `SystemExit` вне `cli.py`, нет `yaml.load`, нет `pandas`, нет `click/typer/rich/tqdm`, нет БД/ORM/брокеров/HTTP-клиентов, нет локальных in-memory cache, нет `getattr`, `setattr`, `__dict__`, `__new__`, `__call__`.
- [ ] Шаг 76: Проверить, что `isinstance` в production-коде используется только в `data.py`, `contracts.py` и `typst_value.py`, где обрабатываются значения с внешних границ доверия.
- [ ] Шаг 77: Выполнить локальную установку: `python -m pip install -e ".[dev]"`.
- [ ] Шаг 78: Выполнить `ruff check .`; исправить только проблемы в рамках утвержденной архитектуры.
- [ ] Шаг 79: Выполнить `mypy src`; не отключать strict и не добавлять `type: ignore` без крайней необходимости.
- [ ] Шаг 80: Выполнить `pytest -q`; все unit-тесты должны проходить без установленного Typst, кроме явно пропускаемых интеграционных.
- [ ] Шаг 81: Выполнить `python -m mergetyp --version` и убедиться, что команда возвращает версию без traceback.
- [ ] Шаг 82: Если Typst установлен, выполнить smoke certificate: `mergetyp examples/certificate/template.typ examples/certificate/data.csv -o /tmp/mergetyp-cert --name-pattern "{name}.pdf"` и проверить 3 ненулевых PDF.
- [ ] Шаг 83: Если Typst установлен, выполнить smoke invoice: `mergetyp examples/invoice/template.typ examples/invoice/data.json -o /tmp/mergetyp-invoice --name-pattern "{invoice_id}.pdf"` и проверить 2 ненулевых PDF.

## 6. Edge Cases, которые обязательно покрыть

- `typst` отсутствует на PATH -> `TypstNotFoundError`, exit `1`, без traceback.
- Template missing -> exit `2`.
- Data missing -> exit `2`.
- Unsupported extension -> exit `1`.
- Empty CSV/JSON/YAML -> `DataValidationError`.
- `--offset`/`--limit` выбирают пустой диапазон -> `DataValidationError`.
- JSON/YAML top-level scalar -> `DataValidationError`.
- JSON/YAML array содержит scalar -> `DataValidationError` с номером record.
- CSV empty cell -> `None` при coercion и `""` при `--no-coerce`.
- CSV `true`, `FALSE` -> bool при coercion.
- CSV `42`, `-7`, `0` -> int при coercion.
- CSV `01234` -> string.
- CSV `3.5` -> float.
- CSV `1e-5` -> string.
- `float("nan")`, `inf`, `-inf` -> Typst `none`.
- Unicode key `имя` -> quoted Typst key `"имя": ...`.
- Dash key `invoice-id` -> quoted Typst key `"invoice-id": ...`.
- Missing `--name-pattern` field -> fail before rendering.
- Filename without `.pdf` -> append suffix.
- Slash/backslash in filename -> `_`.
- Batch filename collision -> default error before rendering.
- Existing output file -> default error before rendering.
- `--collision overwrite` -> warning, path unchanged.
- `--collision rename` -> `_2`, `_3`, no overwrite.
- Typst timeout -> `TypstTimeoutError`, exit `1`.
- Typst non-zero -> include stderr in `TypstCompileError`.
- Ctrl+C -> `130`, no traceback.
- `--dry-run` -> no Typst call and no PDF writes.

## 7. Финальный Definition of Done

- [ ] `pyproject.toml` соответствует `SPEC.md`.
- [ ] Все файлы из дерева проекта существуют.
- [ ] Нет production-файлов вне утвержденной структуры.
- [ ] Нет запрещенных зависимостей.
- [ ] Нет `print` в `src/`.
- [ ] Нет `shell=True`.
- [ ] Нет `SystemExit` вне `cli.py`.
- [ ] Нет `getattr`, `setattr`, `__dict__`, `__new__`, `__call__`.
- [ ] Нет локальных in-memory cache.
- [ ] `isinstance` используется только в `data.py`, `contracts.py`, `typst_value.py`.
- [ ] `typst compile` всегда вызывается с timeout.
- [ ] PDF пишутся только через `write_pdf_atomic`.
- [ ] Коллизии имен проверяются до рендеринга.
- [ ] Default collision policy — `error`.
- [ ] `--dry-run` не создает PDF.
- [ ] `--jobs 0` и `--jobs -1` невозможны.
- [ ] Float не выводится через scientific notation.
- [ ] Unicode keys в Typst dict всегда кавычатся.
- [ ] CSV `"01234"` остается строкой.
- [ ] Ctrl+C возвращает `130`.
- [ ] `ruff check .` проходит.
- [ ] `mypy src` проходит.
- [ ] `pytest -q` проходит.
- [ ] Smoke-тесты examples проходят с реальным Typst.
- [ ] GitHub Actions CI проходит.
