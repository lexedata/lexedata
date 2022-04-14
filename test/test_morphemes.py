from lexedata.report.nonconcatenative_morphemes import cluster_overlaps
from io import StringIO


def test_cluster():
    string = StringIO()
    cluster_overlaps([("root1", "root2"), ("name1", "name2")], string)
    assert (
        string.getvalue().strip().split()
        == """
    Cluster of overlapping cognate sets:
        name1
        name2
    Cluster of overlapping cognate sets:
        root1
        root2
    """.strip().split()
    )
