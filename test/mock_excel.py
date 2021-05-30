class C:
    "A mock cell"

    def __init__(self, value, row, column, comment=None):
        self.value = value or None
        self.comment = None
        self.column = column
        self.row = row

    @property
    def coordinate(self):
        return (self.row, self.column)

    def __repr__(self):
        return repr(self.value)


class MockSingleExcelSheet:
    def __init__(self, data):
        self.data = [
            [C(d, i, j) for j, d in enumerate(dr, 1)] for i, dr in enumerate(data, 1)
        ]
        self.title = "MockSingleExcelSheet"

    def iter_rows(self, min_row=1, max_row=None, min_col=1, max_col=None):
        if max_row is None:
            max_row = len(self.data)
        if max_col is None:
            max_col = len(self.data[0])
        for row in self.data[min_row - 1 : max_row]:
            yield row[min_col - 1 : max_col]

    def iter_cols(self, min_row=1, max_row=None, min_col=1, max_col=None):
        if max_row is None:
            max_row = len(self.data)
        if max_col is None:
            max_col = len(self.data[0])
        for c, col in enumerate(zip(*self.data[min_row - 1 : max_row])):
            if c < min_col - 1:
                continue
            if c == max_col + 1:
                break
            yield col

    @property
    def max_column(self):
        return max(len(r) for r in self.data)

    @property
    def max_row(self):
        return len(self.data)
