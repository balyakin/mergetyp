# Финальная техническая спецификация (SPEC.md)

## 1. Общее описание системы и MVP

### 1.1. Назначение продукта

`mergetyp` — это CLI-утилита на Python 3.12 для пакетной генерации PDF-документов через Typst.

Система принимает:

1. Typst-шаблон `.typ`, который экспортирует функцию `render(record)`.
2. Файл данных `.csv`, `.json`, `.yaml` или `.yml`.
3. Параметры CLI для выходной директории, имени файлов, параллелизма и режима проверки.

Система генерирует:

1. Один PDF-файл на каждую запись данных.
2. Понятный итоговый отчет о количестве успешных и ошибочных записей.
3. Ненулевой exit code при любой ошибке валидации, компиляции или записи файлов.

Ключевое свойство проекта: `mergetyp` НЕ делает текстовую подстановку в шаблон. Каждая запись данных
преобразуется в настоящий Typst-литерал и передается в `render(record)`.

### 1.2. Контракт Typst-шаблона

Каждый шаблон ОБЯЗАН экспортировать функцию `render(record)`.

Минимальный валидный шаблон:

```typst
#let render(record) = {
  set page(paper: "a4")

  [
    Hello, #record.name!
  ]
}
```

На каждую запись приложение создает временный Typst-файл следующего вида:

```typst
#import "template.typ": render
#render((name: "Alice", course: "Typst",))
```

Доступ к полям:

1. Если ключ является безопасным ASCII-идентификатором `^[A-Za-z_][A-Za-z0-9_]*$`, шаблон МОЖЕТ использовать
   `record.name`.
2. Если ключ содержит пробелы, дефисы, кириллицу, цифру в начале или спецсимволы, шаблон ОБЯЗАН использовать
   `record.at("field name")`.
3. Кодер НЕ ДОЛЖЕН генерировать некавыченные ключи с Unicode-именами или дефисами.

### 1.3. MVP

MVP включает только следующие возможности:

1. CLI-команда `mergetyp`.
2. Входные форматы: CSV, JSON, YAML.
3. Выходной формат: только PDF.
4. Вызов внешнего бинарника `typst` через `subprocess.run`.
5. Параллельный рендеринг через `ThreadPoolExecutor`.
6. Строгая Pydantic v2-валидация настроек запуска и записей данных.
7. Безопасное построение имен выходных файлов.
8. Обнаружение коллизий имен до рендеринга.
9. Атомарная запись PDF через временный файл и `os.replace`.
10. Таймаут на каждый вызов `typst compile`.
11. `--dry-run` для проверки данных, имен файлов и коллизий без генерации PDF.
12. `--limit` и `--offset` для отладки части датасета.
13. Unit-тесты для всех модулей с бизнес-логикой.
14. CI на GitHub Actions.

### 1.4. Не входит в MVP

В v0.1 ЗАПРЕЩЕНО реализовывать:

1. Web API.
2. FastAPI-приложение.
3. Базу данных.
4. SQLAlchemy.
5. Taskiq, Celery, RQ или любой брокер задач.
6. Redis.
7. Watch mode.
8. Hot reload.
9. GUI.
10. TUI.
11. Excel `.xlsx`.
12. TOML.
13. SQLite-источник данных.
14. HTTP-источник данных.
15. PNG/SVG-экспорт.
16. Отправку email.
17. Webhooks.
18. Шаблонную галерею.
19. Конфигурационные файлы `.toml`, `.yaml`, `.ini`.
20. Плагины.
21. Телеметрию.
22. Логирование в файл.

Если кодирующая LLM добавляет любой пункт из этого списка, реализация считается ошибочной.

### 1.5. Пользовательские сценарии

#### US-1. Генерация сертификатов из CSV

Как пользователь, я хочу передать `template.typ` и `data.csv`, чтобы получить по одному сертификату на каждую строку CSV.

Критерии приемки:

1. Команда завершается с exit code `0`.
2. В выходной директории создается ровно столько PDF, сколько записей в CSV после применения `--offset` и `--limit`.
3. Каждый PDF имеет ненулевой размер.
4. В случае отсутствия `typst` пользователь получает понятное сообщение без traceback.

#### US-2. Генерация инвойсов из JSON с вложенными строками

Как пользователь, я хочу передать JSON-массив объектов с вложенным массивом `items`, чтобы Typst-шаблон мог
рендерить таблицу позиций.

Критерии приемки:

1. JSON-массив объектов загружается без потери вложенных типов.
2. Вложенные списки и словари корректно преобразуются в Typst-литералы.
3. Числа с плавающей точкой не генерируются в scientific notation.
4. Ошибка в одной записи не скрывает ошибки других записей.

#### US-3. Безопасное именование PDF

Как пользователь, я хочу задать `--name-pattern "{invoice_id}.pdf"`, чтобы PDF назывались по бизнес-ключу.

Критерии приемки:

1. Если поле отсутствует, приложение падает до рендеринга с понятным сообщением.
2. Если два record дают одинаковое имя, default-поведение `--collision error` прерывает запуск до рендеринга.
3. Если имя содержит `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|` или control characters, они заменяются на `_`.
4. Поддиректории через `--name-pattern` не поддерживаются в v0.1.

### 1.6. Принятые архитектурные решения

1. Проект является CLI-библиотекой, а не сервисом.
2. Единственный внешний исполняемый компонент — `typst` CLI.
3. Pydantic v2 используется только на границах доверия: CLI-настройки и входные записи.
4. `ThreadPoolExecutor` используется потому, что Python-поток ждет внешний процесс `typst`.
5. `asyncio` не используется в v0.1, чтобы не усложнять отмену, таймауты и тестирование для простой кодирующей LLM.
6. Коллизии имен по умолчанию являются ошибкой, потому что silent overwrite равен потере пользовательских данных.
7. Весь человекочитаемый вывод идет через `logging`, а не через `print`.
8. Временные Typst-файлы создаются рядом с шаблоном, чтобы относительные `#import` и изображения работали корректно.
9. Если директория шаблона read-only, приложение падает с понятным сообщением. Multi-tenant isolation не входит в v0.1.

### 1.7. Предположения

1. Пользователь запускает `mergetyp` только с доверенными Typst-шаблонами.
2. Typst-шаблон является исполняемым документным кодом и может читать файлы внутри `--root`.
3. Пользователь сам устанавливает бинарник `typst`.
4. CI может установить `typst` из официальных релизов Typst.
5. В v0.1 входные файлы помещаются в память целиком.

### 1.8. Открытые вопросы

Блокирующих открытых вопросов нет.

Неблокирующие вопросы для будущих версий:

1. Нужна ли поддержка `.xlsx`.
2. Нужна ли streaming-обработка CSV на 100k+ записей.
3. Нужна ли веб-версия.
4. Нужна ли строгая пользовательская schema-валидация record-полей.

## 2. Архитектурный стек и глобальные ограничения

### 2.1. Обязательный стек

Кодер ОБЯЗАН использовать только следующий runtime-стек:

1. Python `3.12`.
2. Typst CLI, вызываемый как внешний бинарник `typst`.
3. `argparse` из стандартной библиотеки для CLI.
4. `subprocess.run` из стандартной библиотеки для запуска Typst.
5. `concurrent.futures.ThreadPoolExecutor` для параллельного запуска `typst`.
6. `logging` из стандартной библиотеки для вывода сообщений.
7. `csv`, `json`, `pathlib`, `tempfile`, `os`, `shutil`, `math`, `re` из стандартной библиотеки.
8. `pydantic>=2.8,<3` для строгой валидации настроек и записей.
9. `pyyaml>=6.0,<7` для YAML.

Dev-стек:

1. `pytest>=8.0`.
2. `ruff>=0.5`.
3. `mypy>=1.10`.
4. `types-PyYAML>=6.0`.

### 2.2. Запрещенные библиотеки и технологии

В v0.1 ЗАПРЕЩЕНО использовать:

1. FastAPI.
2. Starlette.
3. aiohttp.
4. asyncio subprocess.
5. SQLAlchemy.
6. Alembic.
7. Taskiq.
8. Celery.
9. Redis.
10. Click.
11. Typer.
12. Rich.
13. Tqdm.
14. Pandas.
15. Jinja2.
16. OpenPyXL.
17. AnyIO.
18. HTTP-клиенты.
19. ORM.
20. DI-контейнеры.

Если кодирующей LLM кажется, что нужна одна из этих библиотек, она должна остановиться. Для v0.1 это ошибка
архитектуры.

### 2.3. Python-стиль

Кодер ОБЯЗАН соблюдать следующие правила:

1. Максимальная длина строки — 120 символов.
2. Импорты только в начале файла.
3. Импорты сгруппированы: стандартная библиотека, внешние библиотеки, внутренние модули.
4. Из одного модуля импортировать несколько имен одной строкой.
5. Wildcard imports запрещены.
6. Относительные импорты запрещены. Использовать `from mergetyp.module import name`.
7. Все публичные функции, классы и методы имеют Google Style docstring.
8. В конце последнего предложения описания docstring точка НЕ ставится.
9. Комментарии в Python-коде запрещены, кроме тестовых блоков `# ARRANGE`, `# ACT`, `# ASSERT`.
10. `print` запрещен.
11. `logger.exception()` обязателен при логировании перехваченного исключения с traceback.
12. `isinstance` в прикладном коде запрещен, кроме обработки данных из внешних систем.
13. В этом проекте обработка CSV/JSON/YAML является внешней границей, поэтому `isinstance` допустим только в `data.py`,
    `contracts.py` и `typst_value.py`.
14. Несколько присваиваний в одной строке запрещены.
15. Для типизации использовать `typing.Dict`, `typing.List`, `typing.Optional`, `typing.Union`, `typing.TypedDict`.
16. Не использовать `list[int]`, `dict[str, object]` и другие built-in generic annotations.
17. Не использовать локальные in-memory cache.
18. Не использовать `getattr`, `setattr`, `__dict__`, `__new__`, `__call__`.

### 2.4. pyproject.toml

`pyproject.toml` ОБЯЗАН содержать следующие настройки:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "mergetyp"
version = "0.1.0"
description = "Mail-merge and batch PDF generator powered by Typst."
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [{ name = "TBD" }]
keywords = ["typst", "pdf", "mail-merge", "batch", "template", "document"]
dependencies = [
    "pydantic>=2.8,<3",
    "pyyaml>=6.0,<7",
]

[project.optional-dependencies]
dev = [
    "mypy>=1.10",
    "pytest>=8.0",
    "ruff>=0.5",
    "types-PyYAML>=6.0",
]

[project.scripts]
mergetyp = "mergetyp.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
mergetyp = ["py.typed"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]
ignore = ["UP006", "UP007", "UP045"]

[tool.mypy]
python_version = "3.12"
strict = true
files = ["src"]
```

`UP006`, `UP007` и `UP045` игнорируются намеренно, потому что код обязан использовать `typing.List`,
`typing.Dict`, `typing.Union` и `typing.Optional`.

### 2.5. Exit codes

Приложение ОБЯЗАНО возвращать:

| Код | Значение |
|---:|---|
| `0` | Все записи успешно обработаны или `--dry-run` прошел без ошибок |
| `1` | Ошибка валидации данных, неподдерживаемый формат, ошибка Typst, коллизия, timeout |
| `2` | Не найден файл шаблона или файл данных |
| `130` | Пользователь прервал выполнение через Ctrl+C |

Traceback пользователю показывать запрещено для ожидаемых ошибок.

### 2.6. Конфигурация логирования

Весь вывод приложения идет через logger `mergetyp`.

Обязательный код:

```python
import logging
import sys


LOGGER_NAME = "mergetyp"


def configure_logging(verbose: bool, quiet: bool) -> logging.Logger:
    """Configure application logging

    Args:
        verbose: Enable debug output
        quiet: Show only errors

    Returns:
        Configured application logger
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers.clear()
    logger.propagate = False

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    if quiet:
        logger.setLevel(logging.ERROR)
        return logger

    if verbose:
        logger.setLevel(logging.DEBUG)
        return logger

    logger.setLevel(logging.INFO)
    return logger
```

ЗАПРЕЩЕНО:

1. Использовать `print`.
2. Логировать в файл.
3. Добавлять JSON-логгер.
4. Добавлять цветной вывод.
5. Добавлять progress bar через внешнюю библиотеку.

### 2.7. СУБД и брокеры задач

В v0.1 СУБД и брокеры задач отсутствуют.

Кодер НЕ ДОЛЖЕН создавать:

1. SQLAlchemy engine.
2. SQLAlchemy sessionmaker.
3. Alembic migrations.
4. Taskiq broker.
5. Celery app.
6. Redis connection.

Единственная допустимая инициализация внешней зависимости — поиск бинарника `typst`.
Функция `find_typst()` ОБЯЗАНА находиться в `src/mergetyp/render.py`:

```python
import shutil

from mergetyp.exceptions import TypstNotFoundError


def find_typst() -> str:
    """Find Typst CLI binary

    Returns:
        Absolute path to Typst binary

    Raises:
        TypstNotFoundError: If Typst CLI is not available on PATH
    """
    typst_bin = shutil.which("typst")
    if typst_bin is None:
        raise TypstNotFoundError(
            "ERROR: 'typst' CLI not found on PATH. Install it from official Typst releases."
        )

    return typst_bin
```

## 3. Подробная структура проекта (Дерево директорий и файлов)

Кодер ОБЯЗАН создать ровно следующую структуру:

```text
mergetyp/
├── SPEC.md
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

ЗАПРЕЩЕНО создавать дополнительные production-модули без изменения SPEC.md.

Назначение модулей:

| Модуль | Ответственность |
|---|---|
| `cli.py` | Разбор argv, настройка логирования, конвертация ошибок в exit code |
| `contracts.py` | Pydantic-модели, dataclass-модели, TypedDict-контракты |
| `data.py` | Загрузка CSV/JSON/YAML и валидация records |
| `exceptions.py` | Кастомные исключения с exit code |
| `log.py` | Инициализация logger |
| `naming.py` | Построение и sanitization имен PDF |
| `output.py` | Коллизии, dry-run план, атомарная запись PDF |
| `render.py` | Создание временного `.typ`, вызов `typst compile`, возврат PDF bytes |
| `runner.py` | Оркестрация batch-рендеринга и параллелизм |
| `typst_value.py` | Преобразование Python-значений в Typst-литералы |

## 4. Помодульная спецификация (С алгоритмами, схемами данных и примерами кода/интерфейсов для кодера)

### 4.1. Модуль `exceptions.py`

#### Назначение

Модуль содержит только ожидаемые доменные исключения. Эти исключения перехватываются в `cli.py` и превращаются в
человекочитаемые сообщения без traceback.

#### Обязательный код

```python
class MergetypError(Exception):
    """Base class for expected application errors

    Args:
        message: Human-readable error message
    """

    exit_code = 1

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class InputFileNotFoundError(MergetypError):
    """Raised when template or data file does not exist"""

    exit_code = 2


class TypstNotFoundError(MergetypError):
    """Raised when Typst CLI is not available on PATH"""


class DataValidationError(MergetypError):
    """Raised when input data cannot be loaded or validated"""


class FilenamePatternError(MergetypError):
    """Raised when output filename pattern is invalid"""


class OutputCollisionError(MergetypError):
    """Raised when output file names collide"""


class OutputWriteError(MergetypError):
    """Raised when PDF output cannot be written"""


class TypstCompileError(MergetypError):
    """Raised when Typst returns a non-zero exit code"""


class TypstTimeoutError(MergetypError):
    """Raised when Typst compilation exceeds timeout"""
```

#### Алгоритм использования

1. Низкоуровневый модуль выбрасывает конкретное исключение.
2. Модуль НЕ пишет в stdout/stderr.
3. `cli.py` ловит `MergetypError`.
4. `cli.py` логирует `error.message`.
5. `cli.py` возвращает `error.exit_code`.

#### Нельзя

1. Нельзя выбрасывать `SystemExit` вне `cli.py`.
2. Нельзя использовать Go-style `return result, error`.
3. Нельзя возвращать `None` вместо исключения при ошибке.

### 4.2. Модуль `contracts.py`

#### Назначение

Модуль фиксирует все структуры данных, которыми обмениваются остальные модули.

Кодер ОБЯЗАН копировать эти модели и не заменять их словарями без типов.

#### Pydantic-модели и dataclass-контракты

```python
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo, field_validator

from mergetyp.exceptions import DataValidationError


CollisionPolicy = Literal["error", "overwrite", "rename"]
DEFAULT_JOBS = min(8, os.cpu_count() or 4)


class RuntimeSettings(BaseModel):
    """Validated application settings built from CLI arguments

    Args:
        template_path: Path to Typst template
        data_path: Path to CSV, JSON, YAML, or YML data file
        output_dir: Directory where PDFs will be written
        name_pattern: Output filename pattern
        jobs: Number of parallel Typst jobs
        compile_timeout: Timeout for a single Typst compilation
        no_coerce: Keep CSV values as strings
        dry_run: Validate plan without generating PDFs
        limit: Optional maximum number of records to process
        offset: Number of records to skip before processing
        encoding: CSV file encoding
        collision: Output collision policy
        verbose: Enable debug logs
        quiet: Show only errors

    Raises:
        ValidationError: If settings are invalid
    """

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

    @field_validator("name_pattern")
    @classmethod
    def validate_name_pattern(cls, value: str) -> str:
        """Validate filename pattern syntax

        Args:
            value: User-provided filename pattern

        Returns:
            Validated filename pattern

        Raises:
            ValueError: If Python format string is invalid
        """
        try:
            value.format_map({"index": "1"})
        except KeyError:
            return value
        except ValueError as error:
            raise ValueError(f"invalid name-pattern syntax: {value}") from error

        return value

    @field_validator("quiet")
    @classmethod
    def validate_logging_flags(cls, value: bool, info: ValidationInfo) -> bool:
        """Validate mutually exclusive logging flags

        Args:
            value: Quiet flag
            info: Pydantic validation info

        Returns:
            Validated quiet flag

        Raises:
            ValueError: If verbose and quiet are both enabled
        """
        data = info.data
        verbose = data.get("verbose")
        if value and verbose:
            raise ValueError("--verbose and --quiet cannot be used together")

        return value


class RecordBatchModel(BaseModel):
    """Validated batch of input records

    Args:
        records: Input records after loading

    Raises:
        ValidationError: If records contain unsupported values
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=False)

    records: List[Dict[str, Any]] = Field(min_length=1)

    @field_validator("records")
    @classmethod
    def validate_records(cls, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate all records recursively

        Args:
            value: Loaded records

        Returns:
            Validated records

        Raises:
            ValueError: If a record contains unsupported values
        """
        record_index = 1
        for record in value:
            cls.validate_record(record, record_index)
            record_index = record_index + 1

        return value

    @classmethod
    def validate_record(cls, record: Dict[str, Any], record_index: int) -> None:
        """Validate one record

        Args:
            record: Loaded record
            record_index: One-based record index

        Raises:
            ValueError: If a key or value is unsupported
        """
        for key in record:
            if not isinstance(key, str):
                raise ValueError(f"record #{record_index} contains non-string key")

            field_value = record[key]
            cls.validate_value(field_value, record_index, key)

    @classmethod
    def validate_value(cls, value: Any, record_index: int, field_path: str) -> None:
        """Validate one record value recursively

        Args:
            value: Field value
            record_index: One-based record index
            field_path: Human-readable field path

        Raises:
            ValueError: If value type is unsupported
        """
        if value is None:
            return

        if isinstance(value, str):
            return

        if isinstance(value, bool):
            return

        if isinstance(value, int):
            return

        if isinstance(value, float):
            return

        if isinstance(value, list):
            item_index = 1
            for item in value:
                item_path = f"{field_path}[{item_index}]"
                cls.validate_value(item, record_index, item_path)
                item_index = item_index + 1
            return

        if isinstance(value, dict):
            for child_key in value:
                if not isinstance(child_key, str):
                    raise ValueError(f"record #{record_index} field '{field_path}' contains non-string key")

                child_value = value[child_key]
                child_path = f"{field_path}.{child_key}"
                cls.validate_value(child_value, record_index, child_path)
            return

        value_type = type(value).__name__
        raise ValueError(f"record #{record_index} field '{field_path}' has unsupported type {value_type}")


@dataclass(frozen=True)
class RenderJob:
    """Single render job

    Args:
        record_index: One-based record index
        record: Input record
        output_path: Absolute output PDF path
    """

    record_index: int
    record: Dict[str, Any]
    output_path: Path


@dataclass(frozen=True)
class RenderResult:
    """Result of one render job

    Args:
        record_index: One-based record index
        output_path: Absolute output PDF path
        ok: Whether rendering succeeded
        error_message: Optional human-readable error
    """

    record_index: int
    output_path: Path
    ok: bool
    error_message: Optional[str] = None


def validate_record_batch(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate records using Pydantic

    Args:
        records: Loaded records

    Returns:
        Validated records

    Raises:
        DataValidationError: If Pydantic rejects records
    """
    try:
        batch = RecordBatchModel(records=records)
    except ValidationError as error:
        raise DataValidationError(f"ERROR: invalid input records: {error}") from error

    return batch.records

```

Важно:

1. `RecordBatchModel` валидирует только технически поддерживаемые типы.
2. Она НЕ проверяет, что record содержит поля, которые нужны конкретному Typst-шаблону.
3. Отсутствие поля шаблона обнаруживает Typst или `--name-pattern`.
4. Пользовательская schema-валидация не входит в v0.1.

#### Нельзя

1. Нельзя заменить `RuntimeSettings` на голый `argparse.Namespace`.
2. Нельзя хранить records как `List[Any]`.
3. Нельзя пропускать Pydantic-валидацию ради краткости.
4. Нельзя добавлять SQLAlchemy-модели.

### 4.3. Модуль `data.py`

#### Назначение

Модуль загружает входной файл и возвращает `List[Dict[str, Any]]`.

Поддерживаемые форматы:

1. `.csv`
2. `.json`
3. `.yaml`
4. `.yml`

#### Алгоритм `detect_format(path)`

1. Взять suffix файла.
2. Привести suffix к lower-case.
3. Убрать ведущую точку.
4. Если suffix `csv`, вернуть `"csv"`.
5. Если suffix `json`, вернуть `"json"`.
6. Если suffix `yaml` или `yml`, вернуть `"yaml"`.
7. Иначе выбросить `DataValidationError`.

#### Алгоритм `coerce_csv_value(raw)`

1. Если значение равно пустой строке, вернуть `None`.
2. Если значение case-insensitive равно `true`, вернуть `True`.
3. Если значение case-insensitive равно `false`, вернуть `False`.
4. Если значение является целым числом без ведущего нуля, вернуть `int`.
5. Если значение является decimal float без scientific notation, вернуть `float`.
6. Во всех остальных случаях вернуть исходную строку.

Строка `"01234"` ОБЯЗАНА остаться строкой, чтобы не ломать почтовые индексы, артикулы и телефоны.

#### Обязательный код для coercion

```python
import re
from typing import Optional, Union


CsvValue = Optional[Union[str, int, float, bool]]

INT_PATTERN = re.compile(r"^(0|-?[1-9]\d*)$")
FLOAT_PATTERN = re.compile(r"^-?(0|[1-9]\d*)\.\d+$")
TRUE_VALUE = "true"
FALSE_VALUE = "false"


def coerce_csv_value(raw: str) -> CsvValue:
    """Coerce one CSV string value into a supported Python value

    Args:
        raw: Raw CSV cell value

    Returns:
        Coerced value
    """
    if raw == "":
        return None

    lowered = raw.lower()
    if lowered == TRUE_VALUE:
        return True

    if lowered == FALSE_VALUE:
        return False

    if INT_PATTERN.match(raw):
        return int(raw)

    if FLOAT_PATTERN.match(raw):
        return float(raw)

    return raw
```

#### Алгоритм `load_csv(path, coerce, encoding)`

1. Открыть файл с `newline=""` и заданным `encoding`.
2. Создать `csv.DictReader`.
3. Для каждой строки:
   1. Преобразовать строку в обычный `dict`.
   2. Если `coerce=True`, применить `coerce_csv_value` к каждому значению.
   3. Если `coerce=False`, оставить все значения строками.
4. Если файл пустой или records пусты, выбросить `DataValidationError`.
5. Вернуть список records.

#### Алгоритм `load_json(path)`

1. Открыть файл в `utf-8`.
2. Вызвать `json.load`.
3. Если JSON невалиден, поймать `json.JSONDecodeError`.
4. Если верхний уровень является объектом, обернуть его в список.
5. Если верхний уровень не объект и не список, выбросить `DataValidationError`.
6. Передать records в `validate_record_batch`.
7. Вернуть validated records.

#### Алгоритм `load_yaml(path)`

1. Импортировать `yaml`.
2. Открыть файл в `utf-8`.
3. Вызвать `yaml.safe_load`.
4. Если YAML невалиден, поймать `yaml.YAMLError`.
5. Если результат `None`, выбросить `DataValidationError`.
6. Если верхний уровень является объектом, обернуть его в список.
7. Если верхний уровень не объект и не список, выбросить `DataValidationError`.
8. Передать records в `validate_record_batch`.
9. Вернуть validated records.

#### Обязательный код `data.py`

```python
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from mergetyp.contracts import validate_record_batch
from mergetyp.exceptions import DataValidationError


CSV_FORMAT = "csv"
JSON_FORMAT = "json"
YAML_FORMAT = "yaml"


def detect_format(path: Path) -> str:
    """Detect data file format from path suffix

    Args:
        path: Data file path

    Returns:
        Data format name

    Raises:
        DataValidationError: If suffix is unsupported
    """
    suffix = path.suffix.lower()
    suffix = suffix.lstrip(".")

    if suffix == CSV_FORMAT:
        return CSV_FORMAT

    if suffix == JSON_FORMAT:
        return JSON_FORMAT

    if suffix == YAML_FORMAT or suffix == "yml":
        return YAML_FORMAT

    raise DataValidationError(f"ERROR: unsupported data file '{path}'. Use .csv, .json, .yaml or .yml")


def load_data(path: Path, coerce: bool, encoding: str) -> List[Dict[str, Any]]:
    """Load records from supported data file

    Args:
        path: Data file path
        coerce: Coerce CSV values
        encoding: CSV encoding

    Returns:
        Validated records

    Raises:
        DataValidationError: If data cannot be loaded or validated
    """
    data_format = detect_format(path)

    if data_format == CSV_FORMAT:
        return load_csv(path, coerce, encoding)

    if data_format == JSON_FORMAT:
        return load_json(path)

    return load_yaml(path)


def load_csv(path: Path, coerce: bool, encoding: str) -> List[Dict[str, Any]]:
    """Load records from CSV file

    Args:
        path: CSV data file path
        coerce: Coerce CSV values
        encoding: CSV encoding

    Returns:
        Validated records

    Raises:
        DataValidationError: If CSV cannot be read or validated
    """
    records: List[Dict[str, Any]] = []

    try:
        with path.open(newline="", encoding=encoding) as data_file:
            reader = csv.DictReader(data_file)
            row_index = 1
            for row in reader:
                record = build_csv_record(row, coerce, row_index)
                records.append(record)
                row_index = row_index + 1
    except UnicodeError as error:
        raise DataValidationError(f"ERROR: cannot decode CSV file '{path}' with encoding '{encoding}'") from error
    except csv.Error as error:
        raise DataValidationError(f"ERROR: invalid CSV in '{path}': {error}") from error
    except OSError as error:
        raise DataValidationError(f"ERROR: cannot read data file '{path}': {error}") from error

    return validate_record_batch(records)


def build_csv_record(row: Dict[Optional[str], Optional[str]], coerce: bool, row_index: int) -> Dict[str, Any]:
    """Build one record from CSV row

    Args:
        row: CSV row
        coerce: Coerce CSV values
        row_index: One-based CSV row index

    Returns:
        Record dictionary

    Raises:
        DataValidationError: If CSV row contains extra unnamed columns
    """
    record: Dict[str, Any] = {}

    for key in row:
        if key is None:
            raise DataValidationError(f"ERROR: CSV row #{row_index} contains more cells than headers")

        raw_value = row[key]
        if raw_value is None:
            raw_value = ""

        if coerce:
            record[key] = coerce_csv_value(raw_value)
        else:
            record[key] = raw_value

    return record


def load_json(path: Path) -> List[Dict[str, Any]]:
    """Load records from JSON file

    Args:
        path: JSON data file path

    Returns:
        Validated records

    Raises:
        DataValidationError: If JSON cannot be parsed or validated
    """
    try:
        with path.open(encoding="utf-8") as data_file:
            data = json.load(data_file)
    except json.JSONDecodeError as error:
        raise DataValidationError(f"ERROR: invalid JSON in '{path}': {error}") from error
    except OSError as error:
        raise DataValidationError(f"ERROR: cannot read data file '{path}': {error}") from error

    return normalize_loaded_records(data, "JSON")


def load_yaml(path: Path) -> List[Dict[str, Any]]:
    """Load records from YAML file

    Args:
        path: YAML data file path

    Returns:
        Validated records

    Raises:
        DataValidationError: If YAML cannot be parsed or validated
    """
    try:
        with path.open(encoding="utf-8") as data_file:
            data = yaml.safe_load(data_file)
    except yaml.YAMLError as error:
        raise DataValidationError(f"ERROR: invalid YAML in '{path}': {error}") from error
    except OSError as error:
        raise DataValidationError(f"ERROR: cannot read data file '{path}': {error}") from error

    return normalize_loaded_records(data, "YAML")


def normalize_loaded_records(data: Any, format_name: str) -> List[Dict[str, Any]]:
    """Normalize loaded JSON or YAML data to records

    Args:
        data: Loaded data
        format_name: Human-readable format name

    Returns:
        Validated records

    Raises:
        DataValidationError: If loaded data is not object or array of objects
    """
    if isinstance(data, dict):
        records = [data]
        return validate_record_batch(records)

    if isinstance(data, list):
        return validate_loaded_list(data, format_name)

    data_type = type(data).__name__
    raise DataValidationError(f"ERROR: {format_name} must be an object or array of objects, got {data_type}")


def validate_loaded_list(data: List[Any], format_name: str) -> List[Dict[str, Any]]:
    """Validate loaded JSON or YAML list

    Args:
        data: Loaded list
        format_name: Human-readable format name

    Returns:
        Validated records

    Raises:
        DataValidationError: If any item is not an object
    """
    records: List[Dict[str, Any]] = []
    record_index = 1

    for item in data:
        if not isinstance(item, dict):
            item_type = type(item).__name__
            raise DataValidationError(f"ERROR: record #{record_index} is not an object, got {item_type}")

        records.append(item)
        record_index = record_index + 1

    return validate_record_batch(records)
```

#### Нельзя

1. Нельзя читать CSV без `encoding`.
2. Нельзя превращать `"01234"` в `1234`.
3. Нельзя использовать `yaml.load`.
4. Нельзя показывать пользователю traceback при JSON/YAML parse error.
5. Нельзя поддерживать Excel.
6. Нельзя загружать данные из сети.

### 4.4. Модуль `typst_value.py`

#### Назначение

Модуль преобразует Python-значения в Typst source-code literals.

Поддерживаемые значения:

1. `None`
2. `bool`
3. `int`
4. `float`
5. `str`
6. `list`
7. `tuple`
8. `dict`
9. `datetime.date`
10. `datetime.datetime`

#### Точные соответствия

| Python | Typst |
|---|---|
| `None` | `none` |
| `True` | `true` |
| `False` | `false` |
| `42` | `42` |
| `3.5` | `3.5` |
| `1e-5` | `0.00001` |
| `float("nan")` | `none` |
| `"a\"b"` | `"a\"b"` с экранированием |
| `[]` | `()` |
| `[1]` | `(1,)` |
| `[1, 2]` | `(1, 2,)` |
| `{}` | `(:)` |
| `{"name": "Alice"}` | `(name: "Alice",)` |
| `{"full name": "Alice"}` | `("full name": "Alice",)` |

#### Обязательный код для идентификаторов и float

```python
import datetime
import math
import re
from typing import Any, Dict, List

from mergetyp.exceptions import DataValidationError


TYPST_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def is_typst_identifier(key: str) -> bool:
    """Check whether a key can be emitted as an unquoted Typst dictionary key

    Args:
        key: Dictionary key

    Returns:
        True if key is safe as an unquoted Typst key
    """
    return TYPST_IDENTIFIER_PATTERN.match(key) is not None


def format_float(value: float) -> str:
    """Format float as Typst-compatible decimal literal

    Args:
        value: Python float

    Returns:
        Typst decimal literal or none
    """
    if not math.isfinite(value):
        return "none"

    value_text = f"{value:.1f}"
    for precision in range(1, 18):
        value_text = f"{value:.{precision}f}"
        if float(value_text) == value:
            break

    if value_text == "-0.0":
        return "0.0"

    return value_text


def escape_string(value: str) -> str:
    """Escape string for Typst source literal

    Args:
        value: Raw Python string

    Returns:
        Escaped string without surrounding quotes
    """
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n")
    escaped = escaped.replace("\r", "\\r")
    escaped = escaped.replace("\t", "\\t")
    return escaped


def quote_string(value: str) -> str:
    """Quote string for Typst source literal

    Args:
        value: Raw Python string

    Returns:
        Quoted Typst string literal
    """
    return '"' + escape_string(value) + '"'


def to_typst(value: Any) -> str:
    """Convert Python value to Typst source literal

    Args:
        value: Python value

    Returns:
        Typst source literal

    Raises:
        DataValidationError: If value type is unsupported
    """
    if value is None:
        return "none"

    if isinstance(value, bool):
        if value:
            return "true"

        return "false"

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        return format_float(value)

    if isinstance(value, str):
        return quote_string(value)

    if isinstance(value, list):
        return to_typst_array(value)

    if isinstance(value, tuple):
        return to_typst_array(list(value))

    if isinstance(value, dict):
        return to_typst_dict(value)

    if isinstance(value, datetime.datetime):
        return quote_string(value.isoformat())

    if isinstance(value, datetime.date):
        return quote_string(value.isoformat())

    value_type = type(value).__name__
    raise DataValidationError(f"ERROR: unsupported value type for Typst literal: {value_type}")


def to_typst_array(values: List[Any]) -> str:
    """Convert Python list to Typst array literal

    Args:
        values: Python list

    Returns:
        Typst array literal
    """
    if not values:
        return "()"

    item_literals: List[str] = []
    for item in values:
        item_literal = to_typst(item)
        item_literals.append(item_literal)

    return "(" + ", ".join(item_literals) + ",)"


def to_typst_dict(values: Dict[Any, Any]) -> str:
    """Convert Python dictionary to Typst dictionary literal

    Args:
        values: Python dictionary

    Returns:
        Typst dictionary literal
    """
    if not values:
        return "(:)"

    pair_literals: List[str] = []
    for raw_key in values:
        key = str(raw_key)
        value = values[raw_key]
        value_literal = to_typst(value)
        if is_typst_identifier(key):
            pair_literals.append(f"{key}: {value_literal}")
        else:
            key_literal = quote_string(key)
            pair_literals.append(f"{key_literal}: {value_literal}")

    return "(" + ", ".join(pair_literals) + ",)"
```

#### Алгоритм `to_typst(value)`

1. Если `value is None`, вернуть `"none"`.
2. Если `value` является `bool`, вернуть `"true"` или `"false"`.
3. Если `value` является `int`, вернуть `str(value)`.
4. Если `value` является `float`, вернуть `format_float(value)`.
5. Если `value` является `str`, вернуть строку в двойных кавычках с экранированием `\`, `"`, `\n`, `\r`, `\t`.
6. Если `value` является `list` или `tuple`:
   1. Если коллекция пустая, вернуть `"()"`.
   2. Иначе преобразовать каждый элемент через `to_typst`.
   3. Вернуть Typst-array с trailing comma.
7. Если `value` является `dict`:
   1. Если словарь пустой, вернуть `"(:)"`.
   2. Для каждой пары:
      1. Привести key к строке.
      2. Если key соответствует `TYPST_IDENTIFIER_PATTERN`, писать `key: value`.
      3. Иначе писать `"escaped key": value`.
   3. Вернуть Typst-dictionary с trailing comma.
8. Если `value` является `datetime.date` или `datetime.datetime`, вернуть ISO-строку.
9. Для всех остальных типов выбросить `DataValidationError`. Не stringify-ить молча.

#### Нельзя

1. Нельзя использовать `repr(float)`, потому что он может вернуть `1e-05`.
2. Нельзя использовать fixed precision с `rstrip("0")`, потому что `159.9` может стать
   `159.900000000000006`.
3. Нельзя использовать `str.isidentifier`, потому что он принимает Unicode.
4. Нельзя молча stringify-ить неподдерживаемые объекты.
5. Нельзя менять trailing comma в массивах и словарях.

### 4.5. Модуль `naming.py`

#### Назначение

Модуль строит имя PDF-файла из `--name-pattern`, record и one-based index.

#### Правила

1. `{index}` всегда доступен и начинается с `1`.
2. Любое поле record доступно как `{field_name}`.
3. Если поле отсутствует, выбросить `FilenamePatternError`.
4. Если результат не заканчивается на `.pdf`, добавить `.pdf`.
5. Недопустимые символы заменить на `_`.
6. Если после очистки имя пустое, использовать `output.pdf`.
7. Поддиректории запрещены. `/` и `\` всегда заменяются на `_`.

#### Обязательный код

```python
import re
from typing import Any, Dict

from mergetyp.exceptions import FilenamePatternError


ILLEGAL_FILENAME_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
PDF_SUFFIX = ".pdf"
DEFAULT_FILENAME = "output"


class StrictFormatDict(dict):
    """Dictionary for strict filename pattern formatting"""

    def __missing__(self, key: str) -> str:
        available_fields = ", ".join(str(field_name) for field_name in self.keys())
        raise FilenamePatternError(
            f"ERROR: name-pattern references field '{key}' which is not in the record. "
            f"Available fields: {available_fields}"
        )


def sanitize_filename(name: str) -> str:
    """Sanitize one filename

    Args:
        name: Raw filename

    Returns:
        Safe filename
    """
    cleaned = ILLEGAL_FILENAME_PATTERN.sub("_", name)
    cleaned = cleaned.strip()
    if cleaned:
        return cleaned

    return DEFAULT_FILENAME


def build_filename(pattern: str, record: Dict[str, Any], record_index: int) -> str:
    """Build output PDF filename for one record

    Args:
        pattern: User-provided filename pattern
        record: Input record
        record_index: One-based record index

    Returns:
        Safe PDF filename

    Raises:
        FilenamePatternError: If pattern references missing field
    """
    mapping = StrictFormatDict()
    for key in record:
        mapping[str(key)] = str(record[key])

    mapping["index"] = str(record_index)

    try:
        rendered = pattern.format_map(mapping)
    except ValueError as error:
        raise FilenamePatternError(f"ERROR: invalid name-pattern '{pattern}': {error}") from error

    if not rendered.endswith(PDF_SUFFIX):
        rendered = rendered + PDF_SUFFIX

    return sanitize_filename(rendered)
```

#### Нельзя

1. Нельзя разрешать path traversal.
2. Нельзя создавать поддиректории из `{department}/{name}.pdf`.
3. Нельзя молча заменять отсутствующее поле пустой строкой.
4. Нельзя использовать `eval`, `format` с globals или шаблонизаторы.

### 4.6. Модуль `output.py`

#### Назначение

Модуль отвечает за:

1. Создание `RenderJob`.
2. Проверку коллизий.
3. Атомарную запись PDF.
4. Очистку output directory при `--clean` не требуется в v0.1 и ЗАПРЕЩЕНА.

`--clean` намеренно НЕ входит в v0.1, чтобы кодер не удалил пользовательские файлы.

#### Алгоритм `build_render_jobs`

1. Создать `output_dir`, если директории нет.
2. Для каждого record:
   1. Вычислить one-based `record_index`.
   2. Построить filename через `build_filename`.
   3. Построить absolute `output_path`.
   4. Создать `RenderJob`.
3. Передать jobs в `resolve_collisions`.
4. Вернуть jobs.

#### Алгоритм `resolve_collisions`

1. Создать пустой словарь `seen`.
2. Для каждого job:
   1. Если `output_path` уже есть в `seen`, это batch collision.
   2. Если `output_path.exists()`, это filesystem collision.
3. Если collision policy `error`:
   1. Если есть хотя бы одна коллизия, выбросить `OutputCollisionError`.
4. Если collision policy `overwrite`:
   1. Оставить пути как есть.
   2. Логировать warning при существующих файлах и batch duplicates.
5. Если collision policy `rename`:
   1. Для каждой коллизии добавить suffix `_2`, `_3`, `_4`.
   2. Проверять и batch duplicates, и уже существующие файлы.
   3. Никогда не перезаписывать существующий файл.

Default policy ОБЯЗАН быть `error`.

#### Алгоритм `write_pdf_atomic`

1. Получить целевой `output_path`.
2. Убедиться, что parent directory существует.
3. Построить temporary path рядом с целевым: `<name>.tmp`.
4. Записать bytes во temporary path.
5. Вызвать `os.replace(tmp_path, output_path)`.
6. Если произошел `OSError`, удалить temporary path через `missing_ok=True`.
7. Выбросить `OutputWriteError` с исходной ошибкой через `from error`.

#### Обязательный код `output.py`

```python
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Set

from mergetyp.contracts import CollisionPolicy, RenderJob
from mergetyp.exceptions import OutputCollisionError, OutputWriteError
from mergetyp.naming import build_filename


TEMP_SUFFIX = ".tmp"
RENAME_START_INDEX = 2


def build_render_jobs(
    records: List[Dict[str, Any]],
    output_dir: Path,
    name_pattern: str,
    collision: CollisionPolicy,
    logger: logging.Logger,
) -> List[RenderJob]:
    """Build render jobs and resolve output path collisions

    Args:
        records: Records selected for rendering
        output_dir: Output directory
        name_pattern: Filename pattern
        collision: Collision policy
        logger: Application logger

    Returns:
        Render jobs with final output paths

    Raises:
        OutputCollisionError: If collisions exist and policy is error
        OutputWriteError: If output directory cannot be created
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise OutputWriteError(f"ERROR: cannot create output directory '{output_dir}': {error}") from error

    jobs: List[RenderJob] = []
    record_index = 1
    for record in records:
        filename = build_filename(name_pattern, record, record_index)
        output_path = (output_dir / filename).resolve()
        job = RenderJob(record_index=record_index, record=record, output_path=output_path)
        jobs.append(job)
        record_index = record_index + 1

    return resolve_collisions(jobs, collision, logger)


def resolve_collisions(
    jobs: List[RenderJob],
    collision: CollisionPolicy,
    logger: logging.Logger,
) -> List[RenderJob]:
    """Resolve output filename collisions

    Args:
        jobs: Render jobs
        collision: Collision policy
        logger: Application logger

    Returns:
        Render jobs with resolved output paths

    Raises:
        OutputCollisionError: If collision policy is error and collisions exist
    """
    if collision == "rename":
        return rename_collisions(jobs)

    messages = collect_collision_messages(jobs)
    if not messages:
        return jobs

    if collision == "overwrite":
        for message in messages:
            logger.warning(message)
        return jobs

    details = "\n".join(messages)
    raise OutputCollisionError(f"ERROR: output filename collision detected.\n{details}")


def collect_collision_messages(jobs: List[RenderJob]) -> List[str]:
    """Collect batch and filesystem collision messages

    Args:
        jobs: Render jobs

    Returns:
        Collision messages
    """
    messages: List[str] = []
    seen_paths: Dict[Path, int] = {}

    for job in jobs:
        if job.output_path in seen_paths:
            first_index = seen_paths[job.output_path]
            messages.append(
                f"record #{job.record_index} collides with record #{first_index}: {job.output_path}"
            )
        else:
            seen_paths[job.output_path] = job.record_index

        if job.output_path.exists():
            messages.append(f"record #{job.record_index} would overwrite existing file: {job.output_path}")

    return messages


def rename_collisions(jobs: List[RenderJob]) -> List[RenderJob]:
    """Rename colliding output paths

    Args:
        jobs: Render jobs

    Returns:
        Render jobs with unique output paths
    """
    resolved_jobs: List[RenderJob] = []
    used_paths: Set[Path] = set()

    for job in jobs:
        output_path = get_unique_output_path(job.output_path, used_paths)
        used_paths.add(output_path)
        resolved_job = RenderJob(record_index=job.record_index, record=job.record, output_path=output_path)
        resolved_jobs.append(resolved_job)

    return resolved_jobs


def get_unique_output_path(output_path: Path, used_paths: Set[Path]) -> Path:
    """Build unique output path by adding numeric suffix

    Args:
        output_path: Requested output path
        used_paths: Paths already assigned in current batch

    Returns:
        Unique output path
    """
    if output_path not in used_paths and not output_path.exists():
        return output_path

    suffix_number = RENAME_START_INDEX
    stem = output_path.stem
    file_suffix = output_path.suffix
    parent = output_path.parent

    while True:
        candidate_name = f"{stem}_{suffix_number}{file_suffix}"
        candidate_path = parent / candidate_name
        if candidate_path not in used_paths and not candidate_path.exists():
            return candidate_path

        suffix_number = suffix_number + 1


def write_pdf_atomic(output_path: Path, pdf_bytes: bytes) -> None:
    """Write PDF bytes atomically

    Args:
        output_path: Target PDF path
        pdf_bytes: PDF file content

    Raises:
        OutputWriteError: If writing fails
    """
    temp_path = output_path.with_name(output_path.name + TEMP_SUFFIX)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(pdf_bytes)
        os.replace(str(temp_path), str(output_path))
    except OSError as error:
        raise OutputWriteError(f"ERROR: cannot write output file '{output_path}': {error}") from error
    finally:
        temp_path.unlink(missing_ok=True)
```

#### Нельзя

1. Нельзя писать PDF напрямую через `output_path.write_bytes`.
2. Нельзя удалять чужие PDF в output directory.
3. Нельзя игнорировать batch collisions.
4. Нельзя делать `rm -rf` для output directory.

### 4.7. Модуль `render.py`

#### Назначение

Модуль выполняет только одну задачу: превратить один record в PDF bytes через Typst CLI.

Модуль НЕ знает про:

1. CLI args.
2. Коллизии имен.
3. Параллелизм.
4. Запись PDF в итоговую директорию.

#### Алгоритм `render_record`

1. Принять `template_path`, `record`, `typst_bin`, `compile_timeout`.
2. Вычислить `root = template_path.parent`.
3. Вызвать `to_typst(record)`.
4. Сформировать Typst source:
   1. `#import "template.typ": render`
   2. `#render(<record literal>)`
5. Создать temporary `.typ` файл в `root`.
6. Если `root` read-only, выбросить `OutputWriteError` с понятным сообщением.
7. Записать source во temporary file.
8. Вызвать `subprocess.run`:
   1. `typst compile`
   2. `--root <root>`
   3. `--format pdf`
   4. `<tmp_path>`
   5. `-`
   6. `capture_output=True`
   7. `check=False`
   8. `timeout=compile_timeout`
9. Если `subprocess.TimeoutExpired`, выбросить `TypstTimeoutError`.
10. Если `returncode != 0`, выбросить `TypstCompileError` с Typst stderr.
11. Вернуть `stdout` как PDF bytes.
12. В `finally` удалить temporary `.typ`.

#### Обязательный паттерн subprocess

```python
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

from mergetyp.exceptions import OutputWriteError, TypstCompileError, TypstNotFoundError, TypstTimeoutError
from mergetyp.typst_value import to_typst


def find_typst() -> str:
    """Find Typst CLI binary

    Returns:
        Absolute path to Typst binary

    Raises:
        TypstNotFoundError: If Typst CLI is not available on PATH
    """
    typst_bin = shutil.which("typst")
    if typst_bin is None:
        raise TypstNotFoundError(
            "ERROR: 'typst' CLI not found on PATH. Install it from official Typst releases."
        )

    return typst_bin


def render_record(template_path: Path, record: Dict[str, Any], typst_bin: str, compile_timeout: float) -> bytes:
    """Render one record into PDF bytes

    Args:
        template_path: Typst template path
        record: Input record
        typst_bin: Typst CLI binary path
        compile_timeout: Per-record compilation timeout in seconds

    Returns:
        PDF bytes

    Raises:
        OutputWriteError: If temporary Typst file cannot be created
        TypstCompileError: If Typst exits with non-zero code
        TypstTimeoutError: If Typst compilation exceeds timeout
    """
    root = template_path.parent
    template_name = template_path.name
    source = f'#import "{template_name}": render\n#render({to_typst(record)})\n'

    try:
        file_descriptor = tempfile.mkstemp(prefix=".mergetyp_gen_", suffix=".typ", dir=str(root))
    except PermissionError as error:
        raise OutputWriteError(
            f"ERROR: cannot write temporary Typst file to template directory '{root}'. "
            f"Check write permissions."
        ) from error

    descriptor_number = file_descriptor[0]
    temporary_name = file_descriptor[1]
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(descriptor_number, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(source)

        result = subprocess.run(
            [
                typst_bin,
                "compile",
                "--root",
                str(root),
                "--format",
                "pdf",
                str(temporary_path),
                "-",
            ],
            capture_output=True,
            check=False,
            timeout=compile_timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise TypstTimeoutError(
            f"ERROR: typst timed out after {compile_timeout}s for template '{template_name}'"
        ) from error
    finally:
        temporary_path.unlink(missing_ok=True)

    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace")
        raise TypstCompileError(
            f"ERROR: typst failed to compile record with template '{template_name}'.\n"
            f"--- typst stderr ---\n{stderr_text}"
        )

    return result.stdout
```

#### Нельзя

1. Нельзя использовать `shell=True`.
2. Нельзя вызывать `typst` без timeout.
3. Нельзя писать итоговый PDF из `render.py`.
4. Нельзя оставлять temporary `.typ` после ошибки.
5. Нельзя скрывать stderr Typst.
6. Нельзя переходить на `asyncio` в v0.1.

### 4.8. Модуль `runner.py`

#### Назначение

Модуль оркестрирует batch-рендеринг.

Он принимает:

1. `RuntimeSettings`.
2. Validated records.
3. Logger.

Он возвращает:

1. Список `RenderResult`.

#### Алгоритм `run_batch`

1. Проверить, что `template_path` существует. Если файла нет, выбросить `InputFileNotFoundError`.
2. Проверить, что `data_path` существует. Если файла нет, выбросить `InputFileNotFoundError`.
3. Построить `RenderJob` для каждой записи.
4. Если jobs пустой после применения `--offset` и `--limit`, выбросить `DataValidationError`.
5. Если `dry_run=True`:
   1. Залогировать каждую запись плана.
   2. Вернуть успешные `RenderResult` без вызова Typst.
6. Найти `typst` через `find_typst`.
7. Если `jobs == 1` или записей одна:
   1. Выполнить jobs последовательно.
8. Иначе:
   1. Создать `ThreadPoolExecutor(max_workers=settings.jobs)`.
   2. Отправить все jobs через `executor.submit`.
   3. Обойти futures через `as_completed`.
   4. Ошибку одного job записать в результат, а не падать сразу.
9. Вернуть список результатов, отсортированный по `record_index`.

#### Алгоритм `run_one_job`

1. Залогировать начало job на DEBUG.
2. Вызвать `render_record`.
3. Вызвать `write_pdf_atomic`.
4. Вернуть `RenderResult(ok=True)`.
5. Если пойман `MergetypError`, вернуть `RenderResult(ok=False, error_message=error.message)`.
6. Если пойман неожиданный `Exception`, вызвать `logger.exception(...)` и вернуть `RenderResult(ok=False, ...)`.

#### Обязательный паттерн ThreadPoolExecutor

```python
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from mergetyp.contracts import RenderJob, RenderResult, RuntimeSettings
from mergetyp.exceptions import DataValidationError, InputFileNotFoundError, MergetypError
from mergetyp.output import build_render_jobs, write_pdf_atomic
from mergetyp.render import find_typst, render_record


def run_one_job(job: RenderJob, settings: RuntimeSettings, typst_bin: str, logger: logging.Logger) -> RenderResult:
    """Render and write one job

    Args:
        job: Render job
        settings: Runtime settings
        typst_bin: Typst CLI path
        logger: Application logger

    Returns:
        Render result
    """
    try:
        pdf_bytes = render_record(settings.template_path, job.record, typst_bin, settings.compile_timeout)
        write_pdf_atomic(job.output_path, pdf_bytes)
    except MergetypError as error:
        return RenderResult(
            record_index=job.record_index,
            output_path=job.output_path,
            ok=False,
            error_message=error.message,
        )
    except Exception as error:
        logger.exception(
            "unexpected error for record_index=%s output_path=%s",
            job.record_index,
            job.output_path,
        )
        return RenderResult(
            record_index=job.record_index,
            output_path=job.output_path,
            ok=False,
            error_message=f"ERROR: unexpected error for record #{job.record_index}: {error}",
        )

    return RenderResult(record_index=job.record_index, output_path=job.output_path, ok=True)


def run_jobs_parallel(
    jobs: List[RenderJob],
    settings: RuntimeSettings,
    typst_bin: str,
    logger: logging.Logger,
) -> List[RenderResult]:
    """Run render jobs in parallel

    Args:
        jobs: Render jobs
        settings: Runtime settings
        typst_bin: Typst CLI path
        logger: Application logger

    Returns:
        Render results
    """
    results: List[RenderResult] = []

    with ThreadPoolExecutor(max_workers=settings.jobs) as executor:
        futures = []
        for job in jobs:
            future = executor.submit(run_one_job, job, settings, typst_bin, logger)
            futures.append(future)

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    return results


def run_jobs_sequential(
    jobs: List[RenderJob],
    settings: RuntimeSettings,
    typst_bin: str,
    logger: logging.Logger,
) -> List[RenderResult]:
    """Run render jobs sequentially

    Args:
        jobs: Render jobs
        settings: Runtime settings
        typst_bin: Typst CLI path
        logger: Application logger

    Returns:
        Render results
    """
    results: List[RenderResult] = []

    for job in jobs:
        result = run_one_job(job, settings, typst_bin, logger)
        results.append(result)

    return results


def run_dry_run(jobs: List[RenderJob], logger: logging.Logger) -> List[RenderResult]:
    """Return planned jobs without rendering PDFs

    Args:
        jobs: Render jobs
        logger: Application logger

    Returns:
        Successful dry-run results
    """
    results: List[RenderResult] = []

    for job in jobs:
        logger.info("dry-run: record #%s -> %s", job.record_index, job.output_path)
        result = RenderResult(record_index=job.record_index, output_path=job.output_path, ok=True)
        results.append(result)

    return results


def run_batch(
    settings: RuntimeSettings,
    records: List[Dict[str, Any]],
    logger: logging.Logger,
) -> List[RenderResult]:
    """Run batch rendering

    Args:
        settings: Runtime settings
        records: Selected records
        logger: Application logger

    Returns:
        Render results

    Raises:
        InputFileNotFoundError: If template or data file is missing
        DataValidationError: If selected record range is empty
    """
    if not settings.template_path.is_file():
        raise InputFileNotFoundError(f"ERROR: template not found: {settings.template_path}")

    if not settings.data_path.is_file():
        raise InputFileNotFoundError(f"ERROR: data file not found: {settings.data_path}")

    jobs = build_render_jobs(
        records=records,
        output_dir=settings.output_dir,
        name_pattern=settings.name_pattern,
        collision=settings.collision,
        logger=logger,
    )

    if not jobs:
        raise DataValidationError("ERROR: selected record range contains no records.")

    if settings.dry_run:
        return run_dry_run(jobs, logger)

    typst_bin = find_typst()

    if settings.jobs == 1 or len(jobs) == 1:
        results = run_jobs_sequential(jobs, settings, typst_bin, logger)
    else:
        results = run_jobs_parallel(jobs, settings, typst_bin, logger)

    return sort_results(results)


def sort_results(results: List[RenderResult]) -> List[RenderResult]:
    """Sort render results by record index

    Args:
        results: Render results

    Returns:
        Sorted render results
    """
    return sorted(results, key=lambda result: result.record_index)
```

#### Ctrl+C

`KeyboardInterrupt` ОБЯЗАН обрабатываться в `cli.py`, а не глубоко в `runner.py`.

При Ctrl+C:

1. Логировать `mergetyp: interrupted by user`.
2. Вернуть exit code `130`.
3. Не логировать traceback.
4. Не подавлять неожиданные ошибки внутри worker без `logger.exception`.

#### Нельзя

1. Нельзя использовать `ProcessPoolExecutor`.
2. Нельзя использовать `asyncio`.
3. Нельзя останавливать весь batch при первой ошибке одной записи.
4. Нельзя возвращать только boolean.

### 4.9. Модуль `cli.py`

#### Назначение

Модуль является единственным местом, где:

1. Разбирается argv.
2. Настраивается logging.
3. Ожидаемые исключения превращаются в exit code.

#### CLI-интерфейс

Обязательные аргументы:

```text
mergetyp TEMPLATE DATA
```

Опции:

| Опция | Default | Описание |
|---|---:|---|
| `-o`, `--output` | `out` | Директория PDF |
| `--name-pattern` | `{index}.pdf` | Шаблон имени файла |
| `--no-coerce` | `False` | Не приводить CSV-типы |
| `-j`, `--jobs` | `min(8, os.cpu_count() or 4)` | Количество параллельных Typst jobs |
| `--compile-timeout` | `60.0` | Таймаут одного Typst compile |
| `--dry-run` | `False` | Проверить план без рендеринга |
| `--limit` | `None` | Обработать не больше N records |
| `--offset` | `0` | Пропустить первые N records |
| `--encoding` | `utf-8` | Encoding CSV |
| `--collision` | `error` | `error`, `overwrite`, `rename` |
| `--verbose` | `False` | DEBUG logs |
| `--quiet` | `False` | Только ошибки |
| `--version` | - | Версия |

#### Обязательные validators для argparse

```python
import argparse


def positive_int(value: str) -> int:
    """Parse positive integer

    Args:
        value: Raw CLI value

    Returns:
        Parsed positive integer

    Raises:
        ArgumentTypeError: If value is not positive integer
    """
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"must be an integer, got {value}") from error

    if number < 1:
        raise argparse.ArgumentTypeError(f"must be >= 1, got {number}")

    return number


def non_negative_int(value: str) -> int:
    """Parse non-negative integer

    Args:
        value: Raw CLI value

    Returns:
        Parsed non-negative integer

    Raises:
        ArgumentTypeError: If value is negative
    """
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"must be an integer, got {value}") from error

    if number < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {number}")

    return number


def positive_float(value: str) -> float:
    """Parse positive float

    Args:
        value: Raw CLI value

    Returns:
        Parsed positive float

    Raises:
        ArgumentTypeError: If value is not positive float
    """
    try:
        number = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"must be a number, got {value}") from error

    if number <= 0.0:
        raise argparse.ArgumentTypeError(f"must be > 0, got {number}")

    return number
```

#### Обязательный код `build_parser`

```python
import argparse

from mergetyp import __version__
from mergetyp.contracts import DEFAULT_JOBS


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        prog="mergetyp",
        description=(
            "Generate one PDF per data record using a Typst template. "
            "The template must export render(record)."
        ),
    )
    parser.add_argument("template", help="Path to the .typ template file.")
    parser.add_argument("data", help="Path to .csv, .json, .yaml or .yml data file.")
    parser.add_argument("-o", "--output", default="out", help="Output directory.")
    parser.add_argument("--name-pattern", default="{index}.pdf", help="Output filename pattern.")
    parser.add_argument("--no-coerce", action="store_true", help="Keep CSV values as strings.")
    parser.add_argument("-j", "--jobs", type=positive_int, default=DEFAULT_JOBS, help="Parallel Typst jobs.")
    parser.add_argument("--compile-timeout", type=positive_float, default=60.0, help="Typst timeout in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Validate plan without generating PDFs.")
    parser.add_argument("--limit", type=positive_int, default=None, help="Maximum number of records to process.")
    parser.add_argument("--offset", type=non_negative_int, default=0, help="Number of records to skip.")
    parser.add_argument("--encoding", default="utf-8", help="CSV encoding.")
    parser.add_argument(
        "--collision",
        choices=["error", "overwrite", "rename"],
        default="error",
        help="Output filename collision policy.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    parser.add_argument("--quiet", action="store_true", help="Show only errors.")
    parser.add_argument("--version", action="version", version=f"mergetyp {__version__}")
    return parser
```

#### Алгоритм `main(argv)`

1. Создать parser.
2. Распарсить argv.
3. Настроить logger.
4. Построить `RuntimeSettings`.
5. Если Pydantic выбросил `ValidationError`, залогировать ошибку и вернуть `1`.
6. Проверить существование template file:
   1. Если не существует, залогировать `ERROR: template not found: <path>`.
   2. Вернуть `2`.
7. Проверить существование data file:
   1. Если не существует, залогировать `ERROR: data file not found: <path>`.
   2. Вернуть `2`.
8. Загрузить records через `load_data`.
9. Применить `offset` и `limit`.
10. Запустить `run_batch`.
11. Посчитать `success_count`.
12. Посчитать `error_count`.
13. Залогировать summary.
14. Если `error_count > 0`, залогировать каждую ошибку и вернуть `1`.
15. Вернуть `0`.
16. Если `KeyboardInterrupt`, вернуть `130`.
17. Если пойман неожиданный `Exception`, вызвать `logger.exception` и вернуть `1`.

#### Обязательный паттерн создания `RuntimeSettings`

`RuntimeSettings` использует `strict=True`, поэтому строки путей из `argparse` ОБЯЗАТЕЛЬНО преобразовать в
`Path` до создания Pydantic-модели.

```python
import argparse
from pathlib import Path

from mergetyp.contracts import RuntimeSettings


def build_runtime_settings(args: argparse.Namespace) -> RuntimeSettings:
    """Build validated runtime settings from parsed CLI arguments

    Args:
        args: Parsed argparse namespace

    Returns:
        Validated runtime settings

    Raises:
        ValidationError: If settings are invalid
    """
    return RuntimeSettings(
        template_path=Path(args.template).resolve(),
        data_path=Path(args.data).resolve(),
        output_dir=Path(args.output).resolve(),
        name_pattern=args.name_pattern,
        jobs=args.jobs,
        compile_timeout=args.compile_timeout,
        no_coerce=args.no_coerce,
        dry_run=args.dry_run,
        limit=args.limit,
        offset=args.offset,
        encoding=args.encoding,
        collision=args.collision,
        verbose=args.verbose,
        quiet=args.quiet,
    )
```

#### Обязательный код `run_main`

```python
import logging
from typing import Any, Dict, List, Optional

from mergetyp.contracts import RenderResult
from mergetyp.data import load_data
from mergetyp.exceptions import DataValidationError, InputFileNotFoundError
from mergetyp.log import configure_logging
from mergetyp.runner import run_batch


def run_main(argv: Optional[List[str]]) -> int:
    """Run CLI business flow

    Args:
        argv: Optional command line arguments

    Returns:
        Process exit code

    Raises:
        MergetypError: If expected application error occurs
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    logger = configure_logging(args.verbose, args.quiet)
    settings = build_runtime_settings(args)

    if not settings.template_path.is_file():
        raise InputFileNotFoundError(f"ERROR: template not found: {settings.template_path}")

    if not settings.data_path.is_file():
        raise InputFileNotFoundError(f"ERROR: data file not found: {settings.data_path}")

    records = load_data(
        path=settings.data_path,
        coerce=not settings.no_coerce,
        encoding=settings.encoding,
    )
    selected_records = select_records(records, settings.offset, settings.limit)
    results = run_batch(settings, selected_records, logger)
    return report_results(results, settings.dry_run, logger)


def select_records(
    records: List[Dict[str, Any]],
    offset: int,
    limit: Optional[int],
) -> List[Dict[str, Any]]:
    """Apply offset and limit to records

    Args:
        records: Loaded records
        offset: Number of records to skip
        limit: Optional maximum number of records

    Returns:
        Selected records

    Raises:
        DataValidationError: If selection is empty
    """
    selected_records = records[offset:]
    if limit is not None:
        selected_records = selected_records[:limit]

    if not selected_records:
        raise DataValidationError("ERROR: selected record range contains no records.")

    return selected_records


def report_results(results: List[RenderResult], dry_run: bool, logger: logging.Logger) -> int:
    """Report batch results

    Args:
        results: Render results
        dry_run: Whether this was a dry run
        logger: Application logger

    Returns:
        Process exit code
    """
    success_count = 0
    error_count = 0

    for result in results:
        if result.ok:
            success_count = success_count + 1
        else:
            error_count = error_count + 1
            logger.error(result.error_message)

    action = "planned" if dry_run else "generated"
    total_count = len(results)
    logger.info("mergetyp: done. %s/%s PDF(s) %s.", success_count, total_count, action)

    if error_count > 0:
        return 1

    return 0
```

#### Паттерн обработки ошибок в `main`

```python
import logging
from typing import List, Optional

from pydantic import ValidationError

from mergetyp.exceptions import InputFileNotFoundError, MergetypError


def main(argv: Optional[List[str]] = None) -> int:
    """Run mergetyp CLI

    Args:
        argv: Optional command line arguments

    Returns:
        Process exit code
    """
    logger = logging.getLogger("mergetyp")

    try:
        return run_main(argv)
    except KeyboardInterrupt:
        logger.error("mergetyp: interrupted by user")
        return 130
    except InputFileNotFoundError as error:
        logger.error(error.message)
        return error.exit_code
    except MergetypError as error:
        logger.error(error.message)
        return error.exit_code
    except ValidationError as error:
        logger.error("ERROR: invalid CLI settings: %s", error)
        return 1
    except Exception:
        logger.exception("ERROR: unexpected fatal error")
        return 1
```

#### Нельзя

1. Нельзя делать бизнес-логику в `main`.
2. Нельзя вызывать `sys.exit` внутри `run_main`.
3. Нельзя использовать `print`.
4. Нельзя пропускать Pydantic-валидацию settings.
5. Нельзя показывать traceback для ожидаемых ошибок.

### 4.10. Модуль `__main__.py`

Файл должен быть минимальным:

```python
import sys

from mergetyp.cli import main


sys.exit(main())
```

Нельзя добавлять сюда бизнес-логику.

### 4.11. Файл `__init__.py`

Файл должен быть минимальным:

```python
from importlib.metadata import PackageNotFoundError, version


try:
    __version__ = version("mergetyp")
except PackageNotFoundError:
    __version__ = "0.1.0"
```

Нельзя дублировать версию вручную в нескольких местах, кроме fallback.

### 4.12. Точное поведение edge cases

| Ситуация | Поведение |
|---|---|
| `typst` нет на PATH | `ERROR: 'typst' CLI not found...`, exit `1` |
| Шаблон не существует | `ERROR: template not found: <path>`, exit `2` |
| Данные не существуют | `ERROR: data file not found: <path>`, exit `2` |
| Неподдерживаемое расширение | `ERROR: unsupported data file...`, exit `1` |
| Пустой CSV/JSON/YAML | `ERROR: data source contains no records.`, exit `1` |
| `--offset`/`--limit` дают пустую выборку | `ERROR: selected record range contains no records.`, exit `1` |
| JSON/YAML top-level scalar | `ERROR: JSON/YAML must be an object or array of objects...`, exit `1` |
| JSON/YAML array contains scalar | `ERROR: record #N is not an object...`, exit `1` |
| CSV пустая ячейка | `None` при coercion, `""` при `--no-coerce` |
| CSV `true`, `FALSE` | `bool` при coercion |
| CSV `42`, `-7`, `0` | `int` при coercion |
| CSV `01234` | остается `str` |
| CSV `3.5` | `float` |
| CSV `1e-5` | остается `str` |
| `float("nan")`, `inf` | Typst `none` |
| Unicode key `имя` | quoted key `"имя": ...`, доступ `record.at("имя")` |
| Key with dash `invoice-id` | quoted key `"invoice-id": ...`, доступ `record.at("invoice-id")` |
| `--name-pattern` missing field | ошибка до рендеринга, exit `1` |
| Имя без `.pdf` | `.pdf` добавляется |
| Slash in filename | заменяется на `_` |
| Batch filename collision | default `error`, exit `1` до рендеринга |
| Existing output file | default `error`, exit `1` до рендеринга |
| `--collision overwrite` | разрешает перезапись, логирует warning |
| `--collision rename` | добавляет suffix `_2`, `_3`, не перезаписывает |
| Typst compile timeout | `ERROR: typst timed out...`, exit `1` |
| Typst non-zero exit | stderr Typst включается в сообщение, exit `1` |
| Ctrl+C | `mergetyp: interrupted by user`, exit `130` |
| `--dry-run` | Typst не вызывается, PDF не пишутся |

### 4.13. README.md

README должен быть на английском языке.

README ОБЯЗАН содержать:

1. Что такое `mergetyp`.
2. Требование установить Typst CLI.
3. Установку Python-пакета.
4. Quick start с `template.typ` и `data.csv`.
5. Контракт `render(record)`.
6. Таблицу форматов данных.
7. CLI reference.
8. Exit codes.
9. Security note: использовать только trusted Typst templates.
10. Примеры `examples/certificate` и `examples/invoice`.
11. License.

README НЕ ДОЛЖЕН обещать hosted version как гарантированный roadmap.

### 4.14. Обязательные служебные файлы

#### ФАЙЛ: `.gitignore`

```gitignore
__pycache__/
*.py[cod]
*.egg-info/
build/
dist/
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/

out/
**/out/
.mergetyp_gen_*
*.tmp

.DS_Store
Thumbs.db
```

#### ФАЙЛ: `LICENSE`

Кодер ОБЯЗАН заменить `TBD` на имя автора перед публикацией.

```text
MIT License

Copyright (c) 2026 TBD

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

#### ФАЙЛ: `README.md`

````markdown
# mergetyp

Mail-merge for PDFs, powered by [Typst](https://github.com/typst/typst).

`mergetyp` generates one PDF per data record from a Typst template and a CSV, JSON, or YAML file.

## Requirements

Install the Typst CLI first:

```bash
typst --version
```

Install Typst from the official releases, Homebrew, or Cargo:

```bash
brew install typst
cargo install --locked typst-cli
```

## Install

```bash
python -m pip install mergetyp
```

Until the package is published:

```bash
python -m pip install .
```

## Quick start

`template.typ`:

```typst
#let render(record) = {
  set page(paper: "a4")

  [
    Hello, #record.name!
  ]
}
```

`data.csv`:

```csv
name
Alice
Bob
Charlie
```

Run:

```bash
mergetyp template.typ data.csv -o out --name-pattern "{name}.pdf"
```

Outputs:

```text
out/Alice.pdf
out/Bob.pdf
out/Charlie.pdf
```

## Template contract

Every template must export `render(record)`.

For every record, `mergetyp` generates temporary Typst source like this:

```typst
#import "template.typ": render
#render((name: "Alice",))
```

Use `record.name` for safe ASCII keys. Use `record.at("field name")` for keys with spaces, dashes, Unicode,
or other non-identifier characters.

## Data formats

| Format | Behavior |
|---|---|
| `.csv` | CSV cells are strings. By default `mergetyp` coerces booleans, integers, floats, and empty cells. |
| `.json` | Top-level object or array of objects. Values keep native JSON types. |
| `.yaml`, `.yml` | Top-level mapping or sequence of mappings. Values keep native YAML types. |

Use `--no-coerce` to keep all CSV cells as strings.

## CLI

```text
mergetyp TEMPLATE DATA [options]

Options:
  -o, --output DIR             Output directory. Default: out
  --name-pattern PATTERN       Filename pattern. Default: {index}.pdf
  --no-coerce                  Keep CSV values as strings
  -j, --jobs N                 Parallel Typst jobs
  --compile-timeout SECONDS    Timeout for one Typst compile. Default: 60
  --dry-run                    Validate plan without generating PDFs
  --limit N                    Process at most N records
  --offset N                   Skip first N records
  --encoding ENCODING          CSV encoding. Default: utf-8
  --collision POLICY           error, overwrite, or rename. Default: error
  --verbose                    Enable debug logs
  --quiet                      Show only errors
  --version                    Print version
```

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Success |
| `1` | Validation, rendering, timeout, or output error |
| `2` | Template or data file not found |
| `130` | Interrupted by Ctrl+C |

## Security

Typst templates are executable document code. Run `mergetyp` only with trusted templates. Do not keep secrets in the
template directory because Typst can read files inside its project root.

Temporary `.typ` files contain record data and are deleted after rendering. If the process is killed by the operating
system, cleanup is not guaranteed.

## Examples

See:

```text
examples/certificate
examples/invoice
```

## License

MIT.
````

### 4.15. Приложение A: примеры

#### ФАЙЛ: `examples/certificate/template.typ`

```typst
// Certificate template. Exports render(record).
// Expected record fields: name (str), course (str), date (str).
#let render(record) = {
  set page(paper: "a4", margin: 0pt)
  set align(center)

  pad(x: 2cm, y: 2.5cm)[
    #rect(width: 100%, height: 100%, stroke: 2pt + rgb("#b08d2e"), inset: 1.2cm)[
      #v(1.2cm)
      #text(size: 14pt, tracking: 4pt, fill: rgb("#b08d2e"))[CERTIFICATE OF COMPLETION]
      #v(0.4cm)
      #line(length: 30%, stroke: 1pt + rgb("#b08d2e"))
      #v(1.4cm)
      #text(size: 11pt, fill: gray)[This certifies that]
      #v(0.6cm)
      #text(size: 34pt, weight: "bold")[#record.name]
      #v(0.8cm)
      #text(size: 11pt, fill: gray)[has successfully completed]
      #v(0.4cm)
      #text(size: 18pt, weight: "bold", fill: rgb("#1f3a5f"))[#record.course]
      #v(1.4cm)
      #grid(
        columns: (1fr, 1fr),
        column-gutter: 2cm,
        align(center)[
          #line(length: 50%, stroke: 0.5pt + black)
          #v(0.2em)
          #text(size: 9pt)[#record.date]
        ],
        align(center)[
          #line(length: 50%, stroke: 0.5pt + black)
          #v(0.2em)
          #text(size: 9pt)[Acme Academy]
        ],
      )
    ]
  ]
}
```

#### ФАЙЛ: `examples/certificate/data.csv`

```csv
name,course,date
Alice Johnson,Introduction to Typst,2026-06-21
Bob Smith,Advanced Mail Merge,2026-06-21
Charlie Doe,Document Automation,2026-06-21
```

#### ФАЙЛ: `examples/certificate/README.md`

````markdown
# Certificate example

Generate one certificate PDF per row of the CSV:

```bash
mergetyp template.typ data.csv -o out --name-pattern "{name}.pdf"
```
````

#### ФАЙЛ: `examples/invoice/template.typ`

Кодер ОБЯЗАН копировать шаблон без переписывания. В нем намеренно учтены четыре Typst-ловушки:

1. Тело функции обернуто в `[ ... ]` после `set`-правил.
2. Для правого выравнивания используется `align(right)[...]`, а не `right[...]`.
3. Внутри `grid(...)` используется `grid.cell(...)`, а не `table.cell(...)`.
4. Символ `@` в email экранирован как `\@`.

```typst
// Invoice template. Exports render(record).
// Uses record.at(...) for access. Fields:
//   invoice_id (str), date (str), client (str), email (str),
//   items (array of {description, qty, price}),
//   subtotal (num), tax (num), total (num).
#let money(n) = "$" + str(n)

#let render(record) = {
  set page(
    paper: "a4",
    margin: (x: 2cm, top: 2.2cm, bottom: 1.6cm),
  )
  set text(size: 10.5pt)

  [
    #align(right, text(size: 9pt, fill: gray)[
      Invoice #record.at("invoice_id") · #record.at("date")
    ])
    #v(0.8cm)

    #grid(
      columns: (1fr, 1fr),
      column-gutter: 1.5cm,
      [
        #text(size: 16pt, weight: "bold", fill: rgb("#1f3a5f"))[Acme Co.]
        #v(0.3em)
        #text(size: 9pt, fill: gray)[
          123 Market Street \
          San Francisco, CA 94103 \
          billing\@acme.example
        ]
      ],
      align(right)[
        #text(size: 9pt, fill: gray)[BILLED TO]
        #v(0.3em)
        #text(size: 12pt, weight: "bold")[#record.at("client")]
        #text(size: 9pt, fill: gray)[#record.at("email")]
      ],
    )

    #v(1.2cm)

    #let items = record.at("items")
    #table(
      columns: (1fr, 2.2cm, 2.5cm, 2.5cm),
      align: (left, right, right, right),
      stroke: none,
      table.header(
        table.cell(fill: rgb("#1f3a5f"))[#text(white, weight: "bold")[Description]],
        table.cell(fill: rgb("#1f3a5f"))[#text(white, weight: "bold")[Qty]],
        table.cell(fill: rgb("#1f3a5f"))[#text(white, weight: "bold")[Unit Price]],
        table.cell(fill: rgb("#1f3a5f"))[#text(white, weight: "bold")[Amount]],
      ),
      ..items.map(it => (
        [#it.at("description")],
        [#text(rgb("#444"))[#it.at("qty")]],
        [#text(rgb("#444"))[#money(it.at("price"))]],
        [#money(it.at("qty") * it.at("price"))],
      )).flatten(),
    )

    #v(0.6cm)

    #align(right)[
      #grid(
        columns: (4.5cm, 3cm),
        column-gutter: 0.5cm,
        [Subtotal], align(right)[#money(record.at("subtotal"))],
        [Tax], align(right)[#money(record.at("tax"))],
        grid.cell(stroke: (top: 0.5pt + gray))[#v(0.3em)],
        grid.cell(stroke: (top: 0.5pt + gray))[#v(0.3em)],
        text(weight: "bold", size: 12pt)[Total Due],
        text(weight: "bold", size: 12pt, fill: rgb("#1f3a5f"))[#money(record.at("total"))],
      )
    ]

    #v(1.2cm)
    #align(center, text(size: 9pt, fill: gray)[
      Payment due within 30 days. Thank you for your business!
    ])
  ]
}
```

#### ФАЙЛ: `examples/invoice/data.json`

```json
[
  {
    "invoice_id": "INV-001",
    "date": "2026-06-21",
    "client": "Globex Corporation",
    "email": "ap@globex.example",
    "items": [
      {"description": "Consulting — Strategy", "qty": 10, "price": 150},
      {"description": "Hosting (monthly)", "qty": 1, "price": 99}
    ],
    "subtotal": 1599,
    "tax": 159.9,
    "total": 1758.9
  },
  {
    "invoice_id": "INV-002",
    "date": "2026-06-21",
    "client": "Initech",
    "email": "billing@initech.example",
    "items": [
      {"description": "Licence — Pro tier", "qty": 5, "price": 49}
    ],
    "subtotal": 245,
    "tax": 24.5,
    "total": 269.5
  }
]
```

### 4.16. Намеренные отличия от `pre-spec.md`

Эти изменения подтверждены как обязательное поведение SPEC:

1. Unicode-ключи и ключи с дефисом всегда кавычатся в Typst-словаре.
2. CSV `"01234"` остается строкой.
3. Неподдерживаемый Python-тип в `to_typst` вызывает `DataValidationError`, а не молча превращается в строку.
4. README не обещает hosted-версию.
5. `demo/` и GIF-демо не входят в v0.1.

## 5. Стратегия тестирования и CI/CD требования

### 5.1. Общие правила тестов

1. Тесты пишутся на `pytest`.
2. Все тестовые данные должны быть захардкожены.
3. Генерация random/uuid запрещена.
4. Каждый тест делится комментариями:
   1. `# ARRANGE`
   2. `# ACT`
   3. `# ASSERT`
5. Не использовать сетевые запросы.
6. Unit-тесты не должны требовать установленный `typst`, кроме явно помеченных интеграционных тестов.
7. Для `subprocess.run` использовать monkeypatch.
8. Для файлов использовать `tmp_path`.
9. Проверять не только success path, но и ошибки.

### 5.2. Минимальный набор тестов

#### `tests/test_typst_value.py`

Обязательные кейсы:

1. `None -> none`.
2. `True -> true`.
3. `False -> false`.
4. `int`.
5. `float`.
6. `1e-5 -> 0.00001`.
7. `float("nan") -> none`.
8. `float("inf") -> none`.
9. `159.9 -> 159.9`.
10. `1758.9 -> 1758.9`.
11. `0.1 + 0.2 -> 0.30000000000000004`.
12. Экранирование кавычек.
13. Экранирование backslash.
14. Экранирование newline/tab.
15. Empty list.
16. One-item list.
17. Nested list.
18. Empty dict.
19. Dict with ASCII identifier.
20. Dict with Unicode key.
21. Dict with dash key.
22. Nested dict.
23. Unsupported object raises `DataValidationError`.

Пример обязательного теста:

```python
from mergetyp.typst_value import to_typst


def test_float_scientific_notation_is_rendered_as_decimal() -> None:
    # ARRANGE
    value = 0.00001

    # ACT
    result = to_typst(value)

    # ASSERT
    assert result == "0.00001"
```

#### `tests/test_data.py`

Обязательные кейсы:

1. CSV empty cell.
2. CSV bool case-insensitive.
3. CSV int.
4. CSV leading zero remains string.
5. CSV float.
6. CSV scientific notation remains string.
7. JSON single object becomes one record.
8. JSON array of objects.
9. JSON scalar fails.
10. YAML single mapping.
11. YAML sequence of mappings.
12. Invalid JSON raises `DataValidationError`.
13. Invalid YAML raises `DataValidationError`.
14. Unsupported extension raises `DataValidationError`.
15. Empty records fail.

#### `tests/test_naming.py`

Обязательные кейсы:

1. Default `{index}.pdf`.
2. Field pattern.
3. Missing field.
4. Appends `.pdf`.
5. Illegal chars replaced.
6. Slash replaced.
7. Empty sanitized name returns `output.pdf`.

#### `tests/test_output.py`

Обязательные кейсы:

1. `write_pdf_atomic` writes target file.
2. Temporary file is removed after successful replace.
3. OSError removes temporary file and raises `OutputWriteError`.
4. Collision policy `error` fails on duplicate generated names.
5. Collision policy `error` fails on existing file.
6. Collision policy `rename` generates suffix.
7. Collision policy `overwrite` keeps original path.

#### `tests/test_render.py`

Обязательные кейсы:

1. `find_typst` returns path when available.
2. `find_typst` raises `TypstNotFoundError`.
3. `render_record` calls `subprocess.run` with `--root`.
4. `render_record` passes timeout.
5. Non-zero Typst return code raises `TypstCompileError`.
6. `TimeoutExpired` raises `TypstTimeoutError`.
7. Temporary file is deleted after success.
8. Temporary file is deleted after failure.
9. PermissionError during temporary file creation raises `OutputWriteError`.

#### `tests/test_runner.py`

Обязательные кейсы:

1. `dry_run` does not call `render_record`.
2. Sequential mode processes all jobs.
3. Parallel mode processes all jobs.
4. One failed job does not hide other failures.
5. Summary counts success and errors.

#### `tests/test_cli.py`

Обязательные кейсы:

1. Missing template returns `2`.
2. Missing data returns `2`.
3. Invalid `--jobs 0` fails through argparse.
4. Invalid `--compile-timeout 0` fails.
5. `--verbose` and `--quiet` together fail.
6. Expected `MergetypError` returns its exit code.
7. `KeyboardInterrupt` returns `130`.
8. Unexpected exception returns `1` and calls `logger.exception`.
9. `--offset` greater than record count returns `1`.
10. `--limit` combined with `--offset` that selects no records returns `1`.

### 5.3. Интеграционные тесты

Интеграционные тесты с реальным Typst должны быть отдельными и пропускаться, если `typst` отсутствует.

Обязательные сценарии:

1. `examples/certificate/template.typ` + `data.csv` генерируют 3 PDF.
2. `examples/invoice/template.typ` + `data.json` генерируют 2 PDF.
3. Каждый PDF имеет размер больше `0`.

### 5.4. CI/CD

Файл `.github/workflows/ci.yml` ОБЯЗАТЕЛЕН.

Минимальная конфигурация:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    env:
      TYPST_VERSION: v0.15.0
    strategy:
      matrix:
        python-version: ["3.12"]

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install package
        run: python -m pip install -e ".[dev]"

      - name: Ruff
        run: ruff check .

      - name: Mypy
        run: mypy src

      - name: Pytest
        run: pytest -q

      - name: Install Typst
        run: |
          mkdir -p /tmp/typst
          curl -sSL \
            "https://github.com/typst/typst/releases/download/${TYPST_VERSION}/typst-x86_64-unknown-linux-musl.tar.xz" \
            | tar -xJ --strip-components=1 -C /tmp/typst
          sudo mv /tmp/typst/typst /usr/local/bin/typst
          typst --version

      - name: Smoke certificate example
        run: |
          mergetyp examples/certificate/template.typ examples/certificate/data.csv \
            -o /tmp/mergetyp-certificate-out \
            --name-pattern "{name}.pdf"
          test -s "/tmp/mergetyp-certificate-out/Alice Johnson.pdf"

      - name: Smoke invoice example
        run: |
          mergetyp examples/invoice/template.typ examples/invoice/data.json \
            -o /tmp/mergetyp-invoice-out \
            --name-pattern "{invoice_id}.pdf"
          test -s "/tmp/mergetyp-invoice-out/INV-001.pdf"
```

### 5.5. Локальная проверка перед сдачей

Кодер ОБЯЗАН выполнить:

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src
pytest -q
python -m mergetyp --version
mergetyp examples/certificate/template.typ examples/certificate/data.csv -o /tmp/mergetyp-cert --name-pattern "{name}.pdf"
mergetyp examples/invoice/template.typ examples/invoice/data.json -o /tmp/mergetyp-invoice --name-pattern "{invoice_id}.pdf"
```

Если `typst` не установлен, установить его до smoke-тестов.

### 5.6. Финальный чек-лист готовности реализации

Перед сдачей реализация считается готовой только если:

1. `pyproject.toml` соответствует разделу 2.4.
2. Все модули из раздела 3 существуют.
3. Нет production-файлов вне утвержденной структуры.
4. Нет запрещенных зависимостей.
5. Нет `print` в `src/`.
6. Нет `shell=True`.
7. Нет `SystemExit` вне `cli.py`.
8. `typst compile` вызывается с timeout.
9. PDF пишутся только через `write_pdf_atomic`.
10. Коллизии имен проверяются до рендеринга.
11. Default collision policy — `error`.
12. `--dry-run` не создает PDF.
13. `--jobs 0` и `--jobs -1` невозможны.
14. `float` не выводится через scientific notation.
15. Unicode keys в Typst словаре кавычатся.
16. CSV `"01234"` остается строкой.
17. Ctrl+C возвращает `130`.
18. Все unit-тесты проходят.
19. Smoke-тесты examples проходят с реальным Typst.
20. CI проходит на GitHub Actions.

### 5.7. Чего делать НЕЛЬЗЯ по модулям

#### `cli.py`

1. Нельзя писать бизнес-логику.
2. Нельзя использовать `print`.
3. Нельзя вызывать Typst напрямую.
4. Нельзя писать файлы.

#### `contracts.py`

1. Нельзя добавлять ORM-модели.
2. Нельзя добавлять FastAPI request/response schemas.
3. Нельзя выключать `extra="forbid"` для settings.

#### `data.py`

1. Нельзя использовать `pandas`.
2. Нельзя поддерживать Excel.
3. Нельзя использовать `yaml.load`.
4. Нельзя угадывать encoding.

#### `typst_value.py`

1. Нельзя использовать `repr(float)`.
2. Нельзя использовать `str.isidentifier`.
3. Нельзя stringify-ить неподдерживаемые типы.

#### `naming.py`

1. Нельзя разрешать `/` как разделитель директорий.
2. Нельзя молча игнорировать missing field.
3. Нельзя использовать шаблонизатор.

#### `output.py`

1. Нельзя писать PDF напрямую.
2. Нельзя удалять существующие файлы без явной политики.
3. Нельзя игнорировать коллизии.

#### `render.py`

1. Нельзя использовать `shell=True`.
2. Нельзя вызывать Typst без timeout.
3. Нельзя писать итоговые PDF.
4. Нельзя оставлять temporary `.typ`.

#### `runner.py`

1. Нельзя использовать `asyncio`.
2. Нельзя использовать `ProcessPoolExecutor`.
3. Нельзя падать на первой ошибке записи.
4. Нельзя скрывать неожиданные исключения без `logger.exception`.

### 5.8. Статус спецификации

Статус: готово к реализации.

Реализация не заблокирована.
