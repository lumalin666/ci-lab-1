"""Вспомогательные функции для отчётов.

ЭКСПЕРИМЕНТ (раздел 5.7 лабораторной работы):
модуль добавлен в проект, но тесты к нему написаны НЕ были,
поэтому покрытие падает ниже порога 80% и Quality Gate
останавливает Pipeline.
"""


def summarize(items):
    """Собрать сводку по списку товаров."""
    total = len(items)
    names = [item["name"] for item in items]
    longest = max(names, key=len) if names else ""
    shortest = min(names, key=len) if names else ""
    total_length = sum(len(name) for name in names)
    average = total_length / total if total else 0
    return {
        "total": total,
        "names": names,
        "longest": longest,
        "shortest": shortest,
        "average_length": average,
    }


def filter_by_prefix(items, prefix):
    """Отфильтровать товары по началу названия."""
    result = []
    for item in items:
        if item["name"].startswith(prefix):
            result.append(item)
    return result
