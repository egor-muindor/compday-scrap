import random

HEADLESS = True
NAVIGATION_TIMEOUT = 60_000  # ms
DELAY_BETWEEN_CATEGORIES = 3  # seconds

# Detail scraping concurrency
DETAIL_WORKERS = 3          # parallel workers
DETAIL_DELAY_MIN = 1.0      # seconds between requests per worker
DETAIL_DELAY_MAX = 2.0      # seconds between requests per worker

# Pagination for query-param based categories
LISTING_PAGE_SIZE = 60      # items per page for paginated listing


def random_delay() -> float:
    return random.uniform(DETAIL_DELAY_MIN, DETAIL_DELAY_MAX)


CATEGORIES = [
    {
        "slug": "processors",
        "name": "Процессоры socket AM5",
        "base_url": "https://www.compday.ru/komplektuyuszie/protsessory/",
        "filtered_url": "https://www.compday.ru/komplektuyuszie/protsessory/#eyJmaWx0ZXIiOnsiMTA5ODk5IjpbMzA4MTcwXSwiMTEwMjgwIjpbMzM5NzY5XX0sIm9ucGFnZSI6MTAwMDB9",
    },
    {
        "slug": "cooling",
        "name": "СЖО 240мм и 360мм",
        "base_url": "https://www.compday.ru/komplektuyuszie/Vodyanoe-ohlazhdenie-SVO/",
        "filtered_url": "https://www.compday.ru/komplektuyuszie/Vodyanoe-ohlazhdenie-SVO/#eyJmaWx0ZXIiOnsiMTExNTUxIjpbMzQ5NDIwLDM0NjUwNF19LCJvbnBhZ2UiOjEwMDAwfQ==",
    },
    {
        "slug": "motherboards",
        "name": "Материнские платы AM5 + DDR5",
        "base_url": "https://www.compday.ru/komplektuyuszie/materinskie-platy/",
        "filtered_url": "https://www.compday.ru/komplektuyuszie/materinskie-platy/#eyJmaWx0ZXIiOnsiODUiOlsyODI1MDddLCIxMTAyODAiOlszMzk3NjldfSwib25wYWdlIjoxMDAwMH0=",
    },
    {
        "slug": "memory",
        "name": "DDR5 DIMM",
        "base_url": "https://www.compday.ru/komplektuyuszie/moduli-pamyati/",
        "filtered_url": "https://www.compday.ru/komplektuyuszie/moduli-pamyati/#eyJmaWx0ZXIiOnsiMTA5OTAxIjpbMzA4NDUyXSwiMTA5OTAyIjpbMzI2NjE5XX0sIm9ucGFnZSI6MTAwMDB9",
    },
    {
        "slug": "ssd",
        "name": "SSD M2 NVMe",
        "base_url": "https://www.compday.ru/komplektuyuszie/ssd-nakopiteli/",
        "filtered_url": "https://www.compday.ru/komplektuyuszie/ssd-nakopiteli/#eyJmaWx0ZXIiOnsiMTA5OTAxIjpbMzA4NDc1XSwiMTEwMjkwIjpbMzA4NDc2LDUwNDMxOCwzNzkwMzNdLCIxMTAyOTIiOlszMTUwMDksMzA4NDc4LDM4MDk3NF19LCJvbnBhZ2UiOjEwMDAwfQ==",
    },
    {
        "slug": "hdd",
        "name": "HDD 3.5",
        "base_url": "https://www.compday.ru/komplektuyuszie/zhestkie-diski/",
        "filtered_url": "https://www.compday.ru/komplektuyuszie/zhestkie-diski/#eyJmaWx0ZXIiOnsiMTA5OTAxIjpbMzA4MzcwXX0sIm9ucGFnZSI6MTAwMDB9",
    },
    {
        "slug": "videocards",
        "name": "Видеокарты PCIe 4 + PCIe 5",
        "base_url": "https://www.compday.ru/komplektuyuszie/videokarty/",
        "filtered_url": "https://www.compday.ru/komplektuyuszie/videokarty/#eyJmaWx0ZXIiOnsiMTEwMjkwIjpbMzEzNjY2LDUwNjQxNF19LCJvbnBhZ2UiOjEwMDAwfQ==",
    },
    {
        "slug": "psu",
        "name": "Блоки питания ATX12V 3.0+",
        "base_url": "https://www.compday.ru/komplektuyuszie/bloki-pitaniya/",
        "filtered_url": "https://www.compday.ru/komplektuyuszie/bloki-pitaniya/#eyJmaWx0ZXIiOnsiMTU2IjpbNjU2Nyw2NTgyLDY2NTYsNDM1ODNdLCIxMTAzMjgiOlszNDYwNDQsNDI0OTk4XX0sIm9ucGFnZSI6MTAwMDB9",
    },
    {
        "slug": "cases",
        "name": "Корпуса",
        "base_url": "https://www.compday.ru/komplektuyuszie/korpusa/",
        "filtered_url": None,
        "query_filters": "filters%5Bprice%5D%5Bmin%5D=2000&filters%5Bprice%5D%5Bmax%5D=15000&filters%5B110300%5D%5B0%5D=316415&filters%5B110300%5D%5B1%5D=318029&filters%5B110300%5D%5B2%5D=314699&filters%5B110300%5D%5B3%5D=363964",
    },
]
