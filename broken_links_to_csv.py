import csv
import sys
from typing import List

BROKEN_LINK_MESSAGE = "has a broken link: "


class BrokenLink:
    source: str = ''
    link: str = ''
    options: str = ''
    comments: str = ''

    def __init__(self, source: str, link: str, options: str = '', comments: str = ''):
        self.source = source
        self.link = link
        self.options = options
        self.comments = comments

    def to_csv(self):
        return [self.source, self.link, self.options, self.comments]


def print_usage():
    print(f"Usage: {sys.argv[0]} BLC_LOG_FILE", file=sys.stderr)


def is_a_broken_link(line: str) -> bool:
    return BROKEN_LINK_MESSAGE in line


def parse_broken_link(line: str) -> BrokenLink:
    line = line.replace(BROKEN_LINK_MESSAGE, '')
    line = line.replace('Page ', '')
    line = line.rstrip()
    tokens = line.split(' ', 2)
    return BrokenLink(source=tokens[0], link=tokens[1], options=tokens[2])


def write_to_csv_file(broken_links: List):
    with open('blc.csv', mode='w') as blc_file:
        blc_writer = csv.writer(blc_file, delimiter=';', quotechar="'")
        blc_writer.writerow(['SOURCE', 'DESTINY', 'OPTIONS', 'COMMENTS'])
        blc_writer.writerows([broken_link.to_csv() for broken_link in broken_links])


def main(blc_log_path):
    broken_links: List = list()
    try:
        file = open(blc_log_path)
        while line := file.readline():
            if is_a_broken_link(line):
                broken_links.append(parse_broken_link(line))
        write_to_csv_file(broken_links)
        return 0
    except Exception as error:
        print(error)
        return 3


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print_usage()
        sys.exit(2)
    else:
        sys.exit(main(sys.argv[1]))
