import csv


def num_lines(filename, delimiter=','):
    with open(filename, 'r') as file:
        lines = csv.reader(file, delimiter=delimiter)
        count = _count_lines(lines, filename)

        return count


def _count_lines(lines, filename):
    count = 0
    cols = None

    for line in lines:
        if cols is None:
            cols = len(line)

        if len(line) != cols:
            raise InvalidCSVFormat.wrong_number_if_cols(filename)

        count += 1

    return count


class InvalidCSVFormat(Exception):
    @staticmethod
    def wrong_number_if_cols(filename):
        return InvalidCSVFormat(
            f'All rows must have the same number of columns in {filename}.')

    def __init__(self, message):
        self.message = message
