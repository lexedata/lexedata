import typing as t
from lexedata import cli

R = t.TypeVar("R", bound=t.Dict[str, t.Any])


def clean_forms(
    table: t.Iterable[R],
    form_column_name="form",
    variants_column_name="Variants",
    split_at=[",", ";"],
    split_at_and_keep=["~"],
    logger: cli.logging.Logger = cli.logger,
) -> t.Iterator[R]:
    """Split all forms that contain separators into form+variants.

    >>> for row in clean_forms([
    ...   {'F': 'a ~ æ', 'V': []},
    ...   {'F': 'bə-, be-', 'V': ['b-']}],
    ...   "F", "V"):
    ...   print(row)
    {'F': 'a', 'V': ['~æ']}
    {'F': 'bə-', 'V': ['b-', 'be-']}

    """
    for r, row in enumerate(table):
        forms = [("", row[form_column_name])]
        for separator in split_at:
            forms = [
                ("", form.strip())
                for _, chunk in forms
                for form in chunk.split(separator)
            ]
        for separator in split_at_and_keep:
            forms = [
                (first_separator if f == 0 else separator, form.strip())
                for first_separator, chunk in forms
                for f, form in enumerate(chunk.split(separator))
            ]

        if len(forms) > 1:
            logger.info(
                "Line %d: Split form '%s' into %d elements.",
                r,
                row[form_column_name],
                len(forms),
            )
            if forms[0][0]:
                logger.warn(
                    "First element was marked as variant using %s, ignoring the marker",
                    forms[0][0],
                )
            row[form_column_name] = forms[0][1]
            row[variants_column_name].extend(
                [f"{separator}{form}" for separator, form in forms[1:]]
            )
        yield row
