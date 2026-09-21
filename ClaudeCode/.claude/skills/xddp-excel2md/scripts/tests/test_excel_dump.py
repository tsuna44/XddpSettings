import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

try:
    import openpyxl
except ImportError:
    openpyxl = None

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if openpyxl is not None:
    from excel_dump import dump  # noqa: E402


@unittest.skipIf(openpyxl is None, "openpyxl not installed")
class TestExcelDump(unittest.TestCase):
    def _write_and_dump(self, rows):
        wb = openpyxl.Workbook()
        ws = wb.active
        for row in rows:
            ws.append(row)
        with tempfile.TemporaryDirectory() as tmp_dir:
            excel_path = Path(tmp_dir) / "test.xlsx"
            wb.save(excel_path)
            buf = io.StringIO()
            with redirect_stdout(buf):
                dump(str(excel_path))
            return buf.getvalue()

    def test_empty_cell_becomes_empty_string(self):
        output = self._write_and_dump([["a", None, "c"]])
        self.assertEqual(output, "a\t\tc\n")

    def test_multiple_rows_and_columns(self):
        output = self._write_and_dump([["a1", "b1"], ["a2", "b2"]])
        self.assertEqual(output, "a1\tb1\na2\tb2\n")


if __name__ == "__main__":
    unittest.main()
