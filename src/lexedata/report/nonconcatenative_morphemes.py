# load all cognates corresponding to those forms
which_segment_belongs_to_which_cognateset: t.Dict[str, t.List[t.Set[str]]] = {}
for j in dataset["CognateTable"]:
    if j[c_cognate_form] in forms and j[c_cognate_cognateset] in cognateset_cache:
        form = forms[j[c_cognate_form]]
        if j[c_cognate_form] not in which_segment_belongs_to_which_cognateset:
            which_segment_belongs_to_which_cognateset[j[c_cognate_form]] = [
                set() for _ in form[c_form_segments]
            ]
        segments_judged = segment_slices_to_segment_list(
            segments=form[c_form_segments], judgement=j
        )
        for s in segments_judged:
            try:
                which_segment_belongs_to_which_cognateset[j[c_cognate_form]][s].add(
                    j[c_cognate_cognateset]
                )
            except IndexError:
                print(
                    f"WARNING: In judgement {j}, segment slice point outside valid range 0:{len(form[c_form_segments])}."
                )
                continue
