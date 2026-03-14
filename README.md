# compday-scrap

Скрапер каталога компьютерных комплектующих с сайта [compday.ru](https://www.compday.ru). Собирает данные о товарах и сохраняет их локально в JSON для дальнейшего анализа или интеграции.

## Возможности

- Сбор каталогов товаров с фильтрацией по категориям
- Детальный сбор характеристик каждого товара (цены, спецификации, наличие, гарантия)
- Обновление только цен без полного пересбора
- Параллельная обработка с настраиваемым количеством воркеров
- Возобновляемый сбор деталей (при прерывании продолжит с того же места)

## Категории

| Slug | Описание | Фильтры |
|------|----------|---------|
| `processors` | Процессоры | Socket AM5 |
| `cooling` | Системы жидкостного охлаждения | 240мм и 360мм |
| `motherboards` | Материнские платы | AM5 + DDR5 |
| `memory` | Модули памяти | DDR5 DIMM |
| `ssd` | SSD-накопители | M2 NVMe, PCIe 4.0/5.0 |
| `hdd` | Жёсткие диски | 3.5" |
| `videocards` | Видеокарты | PCIe 4 + PCIe 5 |
| `psu` | Блоки питания | ATX12V 3.0+, 80 PLUS Silver+ |
| `cases` | Корпуса | Цена 2000–15000, форм-факторы ATX/mATX/Mini-ITX/E-ATX |

## Установка

### Требования

- Python 3.14+
- Node.js (для Playwright)

### macOS / Linux

```bash
# Клонировать репозиторий
git clone https://github.com/egor-muindor/compday-scrap.git
cd compday-scrap

# Создать виртуальное окружение и установить зависимости
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Установить браузер для Playwright (нужен для сбора каталогов)
playwright install chromium
```

### Windows

```powershell
# Клонировать репозиторий
git clone https://github.com/egor-muindor/compday-scrap.git
cd compday-scrap

# Создать виртуальное окружение и установить зависимости
python -m venv .venv
.venv\Scripts\activate
pip install -e .

# Установить браузер для Playwright (нужен для сбора каталогов)
playwright install chromium
```

> Если используете [uv](https://docs.astral.sh/uv/), замените `pip install -e .` на `uv pip install -e .`

## Использование

### 1. Сбор каталогов (listing)

Первый этап — собрать список товаров из каталога. Использует Playwright (headless-браузер), так как сайт рендерит каталог через JavaScript.

Два режима работы:
- **Hash-фильтры** — для категорий с `filtered_url`: загружает страницу, нажимает кнопку «Все» для отображения всех товаров
- **Пагинация** — для категорий с `query_filters` (например, корпуса): обходит страницы по 60 товаров (`?p=1&onpage=60&...`)

```bash
# Собрать все категории (с предустановленными фильтрами)
python cli.py listing

# Собрать одну категорию
python cli.py listing --category processors

# Собрать без фильтров (полный каталог)
python cli.py listing --base
python cli.py listing --category processors --base
```

Результат сохраняется в `data/listing/{slug}.json`. Каждый товар содержит:
- `title` — название
- `price` — цена
- `specs` — краткое описание
- `url` — ссылка на детальную страницу

### 2. Сбор деталей (details)

Второй этап — обходит каждую ссылку из listing и собирает полные характеристики. Использует HTTP-запросы (без браузера) — работает быстро.

```bash
# Собрать детали для всех категорий
python cli.py details

# Собрать детали для одной категории
python cli.py details --category processors

# Указать количество параллельных воркеров (по умолчанию 3)
python cli.py details --workers 5

# Сбросить прогресс и собрать заново
python cli.py details --category processors --reset-progress
```

Результат сохраняется в `data/details/{slug}.json`. Каждый товар содержит:
- `title` — полное название
- `code` — код товара
- `price` — цена за наличные
- `card_price` — цена при оплате картой
- `availability` — наличие (Сегодня / Завтра)
- `specs` — полная таблица характеристик (все key-value пары)
- `images` — ссылки на изображения
- `warranty` — гарантия
- `url` — ссылка на страницу товара
- `scraped_at` — дата и время сбора (UTC)

#### Возобновление при прерывании

Прогресс сохраняется в `data/progress.json`. Если процесс был прерван, при следующем запуске уже собранные товары будут пропущены. Для полного пересбора используйте `--reset-progress`.

### 3. Обновление цен (update-prices)

Обновляет только цены в существующих listing-файлах, не перезаписывая остальные данные. Логирует изменения цен, новые и удалённые товары.

```bash
# Обновить цены для всех категорий
python cli.py update-prices

# Обновить цены для одной категории
python cli.py update-prices --category processors
```

## Конфигурация

Параметры находятся в `scraper/config.py`:

| Параметр | По умолчанию | Описание |
|----------|-------------|----------|
| `HEADLESS` | `True` | Запускать браузер без GUI |
| `NAVIGATION_TIMEOUT` | `60000` мс | Таймаут навигации (Playwright) |
| `DELAY_BETWEEN_CATEGORIES` | `3` сек | Задержка между категориями (listing) |
| `DETAIL_WORKERS` | `3` | Количество параллельных воркеров (details) |
| `DETAIL_DELAY_MIN` | `1.0` сек | Минимальная задержка между запросами на воркер |
| `DETAIL_DELAY_MAX` | `2.0` сек | Максимальная задержка между запросами на воркер |
| `LISTING_PAGE_SIZE` | `60` | Количество товаров на странице (для пагинации) |

## Структура данных

```
data/
  listing/
    processors.json       # Каталог процессоров
    cooling.json          # Каталог СЖО
    ...
  details/
    processors.json       # Детали процессоров
    cooling.json          # Детали СЖО
    ...
  progress.json           # Прогресс сбора деталей
```

## Примеры

### Полный сбор с нуля

```bash
# 1. Собрать каталоги всех категорий
python cli.py listing

# 2. Собрать детали всех товаров (параллельно, 3 воркера)
python cli.py details
```

### Обновить цены и пересобрать детали для видеокарт

```bash
python cli.py update-prices --category videocards
python cli.py details --category videocards --reset-progress
```

### Быстрый сбор с 5 воркерами

```bash
python cli.py details --workers 5
```

---

Нужен подобный проект — парсер, скрапер или интеграция с данными? Пишите: [github@muindor.com](mailto:github@muindor.com) или в Telegram: [@Muindor](https://t.me/Muindor)
