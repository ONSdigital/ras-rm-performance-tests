import os
import unittest
from contextlib import contextmanager
from tempfile import mkstemp

from sdc import csvfile


class FileTest(unittest.TestCase):
    def test_num_rows_raise_if_the_file_is_not_found(self):
        with self.assertRaises(FileNotFoundError) as context:
            csvfile.num_lines('missing_file.txt')

    def test_num_lines_returns_the_number_of_lines(self):
        content = 'a1,a2,a3\nb1,b2,b3'

        with _temp_file(content) as filename:
            self.assertEqual(2, csvfile.num_lines(filename))

    def test_num_lines_ignores_trailing_new_lines(self):
        content = 'a1,a2,a3\n'

        with _temp_file(content) as filename:
            self.assertEqual(1, csvfile.num_lines(filename))

    def test_num_lines_raises_if_rows_have_differing_number_of_cols(self):
        content = 'a1,a2,a3\nb1,b2'

        with _temp_file(content) as filename:
            with self.assertRaises(csvfile.InvalidCSVFormat) as context:
                csvfile.num_lines(filename)

        self.assertEqual(
            f'All rows must have the same number of columns in {filename}.',
            str(context.exception))

    def test_num_lines_raises_using_a_different_delimiter(self):
        content = 'a1:a2:a3\nb1:b2'

        with _temp_file(content) as filename:
            with self.assertRaises(csvfile.InvalidCSVFormat):
                csvfile.num_lines(filename=filename, delimiter=':')


@contextmanager
def _temp_file(content):
    _, filename = mkstemp(suffix='.csv')

    file = open(filename, 'w')
    file.write(content)
    file.close()

    yield filename

    os.remove(filename)
