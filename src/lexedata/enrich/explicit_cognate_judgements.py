"""Create an explicit CognateTable.

If a dataset has no CognateTable, and maybe no CognatesetTable, but if it does
have a #cognatesetReference in the FormTable, then extract that column into an
explicit CognateTable, and also generate a CognatesetTable if none exists.

"""
