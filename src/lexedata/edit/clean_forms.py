"""Clean forms.

Move comma-separated alternative forms to the variants column. Move elements in
brackets to the comments if they are separated from the forms by whitespace;
strip brackets and move the form with brackets to the variants if there is no
whitespace separating it.


This is a rough heuristic, but hopefully it helps with the majority of cases.

"""

import string
import typing as t
from pathlib import Path

import pycldf

from lexedata import cli

R = t.TypeVar("R", bound=t.Dict[str, t.Any])


class Skip(Exception):
    """Mark this form to be skipped."""

    def __init__(self, message):
        self.message = message


def unbracket_single_form(form, opening_bracket, closing_bracket):
    """Remove a type of brackets from a form.

    Return the modified form, the variants (i.e. a list containing the form
    with brackets), and all comments (bracket parts that were separated from
    the form by whitespace)

    >>> unbracket_single_form("not in here anyway", "(", ")")
    ('not in here anyway', [], [])

    >>> unbracket_single_form("da (dialectal)", "(", ")")
    ('da', [], ['(dialectal)'])

    >>> unbracket_single_form("da(n)", "(", ")")
    ('dan', ['da'], [])

    >>> unbracket_single_form("(n)da(s) (dialectal)", "(", ")")
    ('ndas', ['da', 'das', 'nda'], ['(dialectal)'])

    """
    variants = []
    comments = []
    while opening_bracket in form:
        try:
            start = form.index(opening_bracket)
            end = form.index(closing_bracket, start)
        except ValueError:
            raise Skip("unbalanced brackets")

        if (start == 0 or (start != 0 and form[start - 1] in string.whitespace)) and (
            end == len(form) - 1
            or (end != len(form) - 1 and form[end + 1] in string.whitespace)
        ):
            comments.append(form[start : end + 1])
            form = "{:}{:}".format(form[:start], form[end + 1 :]).strip()

        else:
            f, vs, _ = unbracket_single_form(
                form[end + 1 :].strip(), opening_bracket, closing_bracket
            )
            vs.append(f)
            variants.extend([form[:start] + v for v in vs])
            form = "{:}{:}{:}".format(
                form[:start], form[start + 1 : end], form[end + 1 :]
            )

    return form, variants, comments


def treat_brackets(
    table: t.Iterable[R],
    form_column_name="form",
    variants_column_name="variants",
    comment_column_name="comment",
    bracket_pairs=[("(", ")")],
    logger: cli.logging.Logger = cli.logger,
) -> t.Iterator[R]:

    """Make sure forms contain no brackets.

    >>> for row in treat_brackets([
    ...   {'F': 'a(m)ba', 'V': [], 'C': ''},
    ...   {'F': 'da (dialectal)', 'V': [], 'C': ''},
    ...   {'F': 'tu(m) (informal)', 'V': [], 'C': '2p'}],
    ...   "F", "V", "C"):
    ...   print(row)
    {'F': 'amba', 'V': ['aba'], 'C': ''}
    {'F': 'da', 'V': [], 'C': '(dialectal)'}
    {'F': 'tum', 'V': ['tu'], 'C': '2p; (informal)'}


    Skipping works even when it is noticed only late in the process.

    >>> for row in treat_brackets([
    ...   {'F': 'a[m]ba (unbalanced', 'V': [], 'C': ''},
    ...   {'F': 'tu(m) (informal', 'V': [], 'C': ''}],
    ...   "F", "V", "C", [("[", "]"), ("(", ")")]):
    ...   print(row)
    {'F': 'a[m]ba (unbalanced', 'V': [], 'C': ''}
    {'F': 'tu(m) (informal', 'V': [], 'C': ''}

    """
    for r, row in enumerate(table):
        form = row[form_column_name]
        variants = row[variants_column_name][:]
        comment = [row[comment_column_name]] if row[comment_column_name] else []
        try:
            for opening_b, closing_b in bracket_pairs:
                if opening_b not in form and closing_b not in form:
                    continue

                form, new_variants, new_comments = unbracket_single_form(
                    form, opening_b, closing_b
                )
                variants.extend(new_variants)
                comment.extend(new_comments)
            # We avoid dict.update() here, so that in a recursive call where an
            # earlier bracket has already succeeded, still the whole form cell
            # is skipped. Or at least I thought that was the logic, except
            # there are no recursive calls to treat_brackets.
            yield {
                **row,
                form_column_name: form,
                variants_column_name: variants,
                comment_column_name: "; ".join(comment),
            }
        except Skip as e:
            # TODO: Should we have a message here?
            logger.error(
                "Line %d: Form '%s' has %s. I did not modify the row.",
                r,
                row[form_column_name],
                e.message,
            )
            yield row


def clean_forms(
    table: t.Iterable[R],
    form_column_name="form",
    variants_column_name="variants",
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


if __name__ == "__main__":
    parser = cli.parser(
        __package__ + "." + Path(__file__).stem,
        description=__doc__.split("\n\n\n")[0],
        epilog=__doc__.split("\n\n\n")[1],
    )
    parser.add_argument(
        "--brackets",
        "-b",
        metavar="LR",
        nargs="+",
        default=[],
        help="Remove brackets from forms, generating variants and comments. Every LR must be a two-character string where L is the left bracket and R is the right bracket.",
    )

    parser.add_argument(
        "--separator",
        "-s",
        nargs="*",
        default=None,
        help="Take SEPARATOR as a separator between forms. If --separator is not given, use tilde '~', comma ',' and semicolon ';'.",
    )
    parser.add_argument(
        "--keep",
        "-k",
        nargs="*",
        default=None,
        help="Take KSEPARATOR as a separator between forms, but include it in front of a variant. If --keep is not given, keep '~' and none of the other separators.",
        metavar="KSEPARATOR",
    )

    args = parser.parse_args()
    logger = cli.setup_logging(args)

    dataset = pycldf.Wordlist.from_metadata(args.metadata)

    if not args.brackets:
        args.brackets = [("(", ")")]
    if args.separator is None:
        args.separator = ["~", ",", ";"]
    if args.keep is None:
        kseparators = {"~"}.intersection(args.separator)
    else:
        kseparators = set(args.keep)
        args.separator = [s for s in args.separator if s not in kseparators]

    # TODO: Connect command line arguments and functions.
    forms = list(dataset["FormTable"])
    try:
        c_variants = (dataset["FormTable", "variants"].name,)
    except KeyError:
        dataset.add_columns("FormTable", "variants")
        dataset["FormTable", "variants"].separator = ";"
        for form in forms:
            form["variants"] = []

    if args.brackets:
        forms = list(
            treat_brackets(
                forms,
                dataset["FormTable", "form"].name,
                dataset["FormTable", "variants"].name,
                dataset["FormTable", "comment"].name,
                logger=logger,
            )
        )
    if args.separator:
        forms = list(
            clean_forms(
                forms,
                dataset["FormTable", "form"].name,
                dataset["FormTable", "variants"].name,
                split_at=args.separator,
                split_at_and_keep=kseparators,
                logger=logger,
            )
        )
    dataset.write(FormTable=forms)
