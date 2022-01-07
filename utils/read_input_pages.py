from typing import List


class ReadInputPages:
    __file_path: str = ""
    __base_url: str = ""

    def __init__(self, file_path: str, base_url: str):
        self.__file_path = file_path
        self.__base_url = base_url

    def read_input_pages(self) -> List:
        pages_to_check = []
        try:
            with open(self.__file_path, mode='r') as input_pages:
                while line := input_pages.readline():
                    pages_to_check += [
                        self.__parse_file_to_page(page) for page in line.split(' ')
                    ]
        except FileNotFoundError as err:
            print(f"Is not possible to read the file: {err}")
            return []
        return pages_to_check

    def __parse_file_to_page(self, page_path: str) -> str:
        """
        Converts a file to path to an address to enqueue in the checker
        input: ambassador-docs/docs/edge-stack/2.0/howtos/advanced-rate-limiting.md
        returns: {base_url}/docs/edge-stack/2.0/howtos/advanced-rate-limiting/
        """
        page_path = page_path.replace(".md\n", "")
        page_path = page_path.replace("ambassador-docs/", "")
        page_path = page_path.replace('v', '', 1) if "telepresence" in page_path else page_path
        return self.__base_url + page_path
