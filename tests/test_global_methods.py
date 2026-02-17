"""Tests for reverie/backend_server/global_methods.py"""
import os
import pytest

from global_methods import (
    average,
    std,
    check_if_file_exists,
    create_folder_if_not_there,
    write_list_of_list_to_csv,
    read_file_to_list,
    find_filenames,
)


# ===================================================================
# average tests
# ===================================================================

class TestAverage:
    def test_basic(self):
        assert average([1, 2, 3]) == 2.0

    def test_float(self):
        result = average([1.5, 2.5, 3.5])
        assert abs(result - 2.5) < 1e-9

    def test_single_element(self):
        assert average([42]) == 42.0

    def test_negative_values(self):
        assert average([-2, -4, -6]) == -4.0


# ===================================================================
# std tests
# ===================================================================

class TestStd:
    def test_uniform(self):
        assert std([5, 5, 5]) == 0.0

    def test_known_value(self):
        # numpy.std([1, 2, 3, 4, 5]) = sqrt(2.0) = ~1.4142
        import numpy
        expected = numpy.std([1, 2, 3, 4, 5])
        assert abs(std([1, 2, 3, 4, 5]) - expected) < 1e-9


# ===================================================================
# check_if_file_exists tests
# ===================================================================

class TestCheckIfFileExists:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "exists.txt"
        f.write_text("hello")
        assert check_if_file_exists(str(f)) is True

    def test_nonexistent_file(self, tmp_path):
        f = tmp_path / "no_such_file.txt"
        assert check_if_file_exists(str(f)) is False


# ===================================================================
# create_folder_if_not_there tests
# ===================================================================

class TestCreateFolderIfNotThere:
    def test_creates_new_folder(self, tmp_path):
        new_dir = tmp_path / "sub" / "deep"
        # Use forward-slash path as required by the implementation
        path_str = str(new_dir).replace("\\", "/")
        result = create_folder_if_not_there(path_str + "/")
        assert result is True
        assert os.path.isdir(str(new_dir))

    def test_existing_folder_returns_false(self, tmp_path):
        existing = tmp_path / "already"
        existing.mkdir()
        path_str = str(existing).replace("\\", "/")
        result = create_folder_if_not_there(path_str + "/")
        assert result is False


# ===================================================================
# write_list_of_list_to_csv + read_file_to_list round-trip tests
# ===================================================================

class TestCsvRoundTrip:
    def _nonempty(self, rows):
        """Filter out empty rows that csv.reader may produce on Windows."""
        return [r for r in rows if r]

    def test_roundtrip(self, tmp_path):
        data = [["name", "age", "city"], ["Alice", "30", "Tokyo"]]
        outfile = str(tmp_path / "out.csv").replace("\\", "/")
        write_list_of_list_to_csv(data, outfile)
        result = self._nonempty(read_file_to_list(outfile))
        assert result == data

    def test_read_with_header(self, tmp_path):
        data = [["h1", "h2"], ["v1", "v2"], ["v3", "v4"]]
        outfile = str(tmp_path / "hdr.csv").replace("\\", "/")
        write_list_of_list_to_csv(data, outfile)
        header, rows = read_file_to_list(outfile, header=True)
        rows = self._nonempty(rows)
        assert header == ["h1", "h2"]
        assert rows == [["v1", "v2"], ["v3", "v4"]]

    def test_strip_trail_false(self, tmp_path):
        data = [["  spaces  ", " val "]]
        outfile = str(tmp_path / "trail.csv").replace("\\", "/")
        write_list_of_list_to_csv(data, outfile)
        result_strip = self._nonempty(read_file_to_list(outfile, strip_trail=True))
        result_no_strip = self._nonempty(read_file_to_list(outfile, strip_trail=False))
        # With strip, leading/trailing spaces are removed
        assert result_strip == [["spaces", "val"]]
        # Without strip, original whitespace is preserved
        assert result_no_strip == [["  spaces  ", " val "]]


# ===================================================================
# find_filenames tests
# ===================================================================

class TestFindFilenames:
    def test_suffix_filter(self, tmp_path):
        (tmp_path / "a.csv").write_text("data")
        (tmp_path / "b.csv").write_text("data")
        (tmp_path / "c.txt").write_text("data")
        result = find_filenames(str(tmp_path), suffix=".csv")
        basenames = sorted([os.path.basename(f) for f in result])
        assert basenames == ["a.csv", "b.csv"]

    def test_empty_directory(self, tmp_path):
        result = find_filenames(str(tmp_path), suffix=".csv")
        assert result == []
