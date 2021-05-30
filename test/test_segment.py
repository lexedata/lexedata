from lexedata.enrich.segment_using_clts import segment_form, SegmentReport


def test_unkown_aspiration(caplog):
    form = "mísidʰu"
    raw_tokens = segment_form(form, SegmentReport())
    assert caplog.text.endswith("Unknown sound ʰ encountered in mísidʰu")

