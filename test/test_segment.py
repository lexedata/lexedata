import re

from lexedata.enrich.segment_using_clts import segment_form, SegmentReport


def test_unkown_aspiration(caplog):
    form = "-á:muaʰ"
    segment_form(form, SegmentReport())
    print(caplog.text)
    assert re.search("Unknown sound aʰ encountered in -á:muaʰ", caplog.text)
