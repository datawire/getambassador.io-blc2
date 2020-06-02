import sys
from typing import Iterable

from blclib import Checker


def main(urls: Iterable[str]) -> None:
    checker = Checker()
    for url in urls:
        checker.enqueue(url)
    checker.run()


if __name__ == "__main__":
    main(sys.argv[1:])
