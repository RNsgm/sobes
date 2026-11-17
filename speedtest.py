#!/usr/bin/env python3
"""Измерение скорости скачивания ресурса по HTTP(S).

Делает N (по умолчанию 10) последовательных запросов к ресурсу, на каждом
дожидается полного получения тела ответа, замеряет время и объём данных,
выводит скорость каждого запроса и итоговую скорость в Мбит/с.
"""

import argparse
import sys
import time

import requests

CHUNK_SIZE = 64 * 1024


def to_mbps(num_bytes: int, seconds: float) -> float:
    """Байты за секунды -> мегабиты в секунду (1 Мбит = 10^6 бит)."""
    if seconds <= 0:
        return 0.0
    return num_bytes * 8 / seconds / 1_000_000


def fetch(url: str, timeout: float) -> tuple[int, float]:
    """Скачивает ресурс целиком. Возвращает (объём в байтах, время в секундах).

    Время считается от отправки запроса до получения последнего байта тела.
    Объём — фактически переданные по сети байты тела ответа (до распаковки
    gzip/deflate), поэтому скорость отражает реальную загрузку канала.
    """
    start = time.perf_counter()
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        downloaded = 0
        for chunk in response.raw.stream(CHUNK_SIZE, decode_content=False):
            downloaded += len(chunk)
    elapsed = time.perf_counter() - start
    return downloaded, elapsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Измеряет скорость скачивания ресурса (в Мбит/с)."
    )
    parser.add_argument("url", help="адрес ресурса, например https://example.com/file.bin")
    parser.add_argument(
        "-n", "--count", type=int, default=10,
        help="количество последовательных запросов (по умолчанию 10)",
    )
    parser.add_argument(
        "-t", "--timeout", type=float, default=30.0,
        help="таймаут соединения и чтения в секундах (по умолчанию 30)",
    )
    parser.add_argument(
        "-more", "--more", action="store_true",
        help="подробный вывод: таблица по каждому запросу и итоги. "
             "Без флага выводится только общая скорость числом (Мбит/с)",
    )
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count должен быть не меньше 1")
    return args


def main() -> int:
    args = parse_args()
    results: list[tuple[int, float]] = []

    if args.more:
        print(f"Ресурс: {args.url}")
        print(f"{'#':>3}  {'Время, с':>10}  {'Объём, байт':>14}  {'Скорость, Мбит/с':>17}")

    for i in range(1, args.count + 1):
        try:
            size, elapsed = fetch(args.url, args.timeout)
        except requests.RequestException as exc:
            print(f"{i:>3}  ошибка: {exc}", file=sys.stderr)
            continue
        results.append((size, elapsed))
        if args.more:
            print(f"{i:>3}  {elapsed:>10.3f}  {size:>14}  {to_mbps(size, elapsed):>17.2f}")

    if not results:
        print("Ни один запрос не выполнен успешно.", file=sys.stderr)
        return 1

    total_bytes = sum(size for size, _ in results)
    avg_time = sum(elapsed for _, elapsed in results) / len(results)
    avg_bytes = total_bytes / len(results)
    total_speed = to_mbps(avg_bytes, avg_time)

    if args.more:
        print()
        print(f"Успешных запросов: {len(results)} из {args.count}")
        print(f"Всего скачано:     {total_bytes} байт")
        print(f"Среднее время:     {avg_time:.3f} с")
        print(f"Общая скорость:    {total_speed:.2f} Мбит/с")
    else:
        print(f"{total_speed:.2f}")
    return 0 if len(results) == args.count else 2


if __name__ == "__main__":
    sys.exit(main())
