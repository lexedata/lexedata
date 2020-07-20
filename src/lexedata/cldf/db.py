import functools
import typing as t
from collections import OrderedDict, defaultdict

import csvw.db
import pycldf.db

from csvw.db import ColSpec, quoted, insert
from pycldf.db import BIBTEX_FIELDS, TableTranslation, TERMS, PRIMARY_KEY_NAMES, clean_bibtex_key

T = t.TypeVar('T', bound="TableSpec")


class TableSpec(csvw.db.TableSpec):
    @classmethod
    def association_table(
            cls: t.Type[T],
            atable: str,
            apk: str,
            btable: str,
            bpk: str,
            context: t.Optional[str] = None) -> T:
        suffix = f"__{context:}" if context else ""
        afk = ColSpec('{0}_{1}'.format(atable, apk))
        bfk = ColSpec('{0}_{1}'.format(btable, bpk))
        if afk.name == bfk.name:
            afk.name += '_1'
            bfk.name += '_2'
        return cls(
            name=f"{atable:}_{btable:}{suffix:}",
            columns=[afk, bfk] + ([ColSpec('context')] if context == "Source" else []),
            foreign_keys=[
                ([afk.name], atable, [apk]),
                ([bfk.name], btable, [bpk]),
            ],
            primary_key=[
                afk.name, bfk.name
            ]
        )

    @classmethod
    def from_table_metadata(
            cls: t.Type[T],
            table: csvw.metadata.Table) -> T:
        """
        Create a `TableSpec` from the schema description of a `csvw.metadata.Table`.

        :param table: `csvw.metadata.Table` instance.
        :return: `TableSpec` instance.
        """
        spec = cls(name=table.local_name, primary_key=table.tableSchema.primaryKey)
        list_valued = {c.header for c in table.tableSchema.columns if c.separator}
        for fk in table.tableSchema.foreignKeys:
            # We only support Foreign Key references between tables!
            if not fk.reference.schemaReference:
                if len(fk.columnReference) == 1 and fk.columnReference[0] in list_valued:
                    # List-valued foreign keys are turned into a many-to-many relation!
                    assert len(fk.reference.columnReference) == 1, \
                        'Composite key {0} in table {1} referenced'.format(
                            fk.reference.columnReference,
                            fk.reference.resource)
                    assert spec.primary_key and len(spec.primary_key) == 1, \
                        'Table {0} with list-valued foreign must have non-composite ' \
                        'primary key'.format(spec.name)
                    spec.many_to_many[fk.columnReference[0]] = TableSpec.association_table(
                        spec.name,
                        spec.primary_key[0],
                        fk.reference.resource.string,
                        fk.reference.columnReference[0],
                        context=fk.columnReference[0]
                    )
                else:
                    spec.foreign_keys.append((
                        sorted(fk.columnReference),
                        fk.reference.resource.string,
                        sorted(fk.reference.columnReference),
                    ))
        for c in table.tableSchema.columns:
            if c.header not in spec.many_to_many:
                datatype = c.inherit('datatype')
                spec.columns.append(ColSpec(
                    name=c.header,
                    csvw_type=datatype.base if datatype else datatype,
                    separator=c.inherit('separator'),
                    required=c.inherit('required'),
                    csvw=c.inherit('datatype'),
                ))
        return spec

    @classmethod
    def schema(
            cls: t.Type[T],
            tg: csvw.TableGroup) -> t.List[T]:
        """
        Convert the table and column descriptions of a `TableGroup` into specifications for the
        DB schema.

        :param ds:
        :return: A pair (tables, reference_tables).
        """
        tables = {}
        for tname, table in tg.tabledict.items():
            t = cls.from_table_metadata(table)
            tables[t.name] = t
            for at in t.many_to_many.values():
                tables[at.name] = at

        # We must determine the order in which tables must be created!
        ordered = OrderedDict()
        i = 0

        # We loop through the tables repeatedly, and whenever we find one, which has all
        # referenced tables already in ordered, we move it from tables to ordered.
        while tables and i < 100:
            i += 1
            for table in list(tables.keys()):
                if all((ref[1] in ordered) or ref[1] == table for ref in tables[table].foreign_keys):
                    # All referenced tables are already created (or self-referential).
                    ordered[table] = tables.pop(table)
                    break
        if tables:  # pragma: no cover
            raise ValueError('there seem to be cyclic dependencies between the tables')

        return list(ordered.values())


def translate(
        d: t.Dict[str, TableTranslation],
        table: str,
        col: t.Optional[str] = None) -> str:
    """
    Translate a db object name.

    :param d: `dict` mapping table urls to `TableTranslation` instances.
    :param table: The table name of the object to be translated.
    :param col: Column name to be translated or `None` - so `table` will be translated.
    :return: Translated name.
    """
    if col:
        if table in d and col in d[table].columns:
            # A simple, translateable column name.
            return d[table].columns[col]
        if '_' in col:
            t, _, c = col.partition('_')
            if t in table and t in d and c in d[t].columns:
                # A generated column name of an association table.
                return '_'.join([d[t].name or t, d[t].columns[c]])
        return col
    if "__" in table:
        tables, context = table.split("__")
        table_a, table_b = tables.split("_")
        return "__".join((translate(d, tables), translate(d, table_a, context)))
    return '_'.join([(d[t].name or t) if t in d else t for t in table.split('_')])


# Reproduce the functionality of the super class, just swap out our
# `TableSpec.schema` for `pycldf.db.schema == pycldf.db.TableSpec.schema` and
# add more translations.
class Database(pycldf.db.Database):
    def init_schema(self, tg: csvw.TableGroup) -> None:
        self.tg = tg
        self.tables = TableSpec.schema(self.tg) if self.tg else []

    def __init__(self, dataset: pycldf.Dataset, **kw) -> None:
        self.dataset = dataset
        self._retranslate = t.DefaultDict[t.Any, t.Dict[t.Any, t.Any]](dict)
        self._source_cols = ['id', 'genre'] + BIBTEX_FIELDS
        self._duplicate_relationship_separator = ";\t"

        infer_primary_keys = kw.pop('infer_primary_keys', False)

        # We create a derived TableGroup, adding a table for the sources.
        tg = csvw.TableGroup.fromvalue(dataset.metadata_dict)

        # Assemble the translation function:
        translations = {}
        for table in dataset.tables:
            translations[table.local_name] = TableTranslation()
            try:
                tt = dataset.get_tabletype(table)
                if tt:
                    # Translate table URLs to CLDF component names:
                    translations[table.local_name].name = tt
            except (KeyError, ValueError):
                # If no table type can be determined, there's nothing to translate.
                pass
            for col in table.tableSchema.columns:
                if col.propertyUrl and col.propertyUrl.uri in TERMS.by_uri:
                    # Translate local column names to local names of CLDF Ontology terms, prefixed
                    # with `cldf_`:
                    col_name = 'cldf_{0.name}'.format(TERMS.by_uri[col.propertyUrl.uri])
                    translations[table.local_name].columns[col.header] = col_name
                    self._retranslate[table.local_name][col_name] = col.header

        # Add source table:
        for src in self.dataset.sources:
            for key in src:
                key = clean_bibtex_key(key)
                if key not in self._source_cols:
                    self._source_cols.append(key)

        tg.tables.append(csvw.Table.fromvalue({
            'url': self.source_table_name,
            'tableSchema': {
                'columns': [dict(name=n) for n in self._source_cols],
                'primaryKey': 'id'
            }
        }))
        tg.tables[-1]._parent = tg

        # Add foreign keys to source table:
        for table in tg.tables[:-1]:
            if not table.tableSchema.primaryKey and infer_primary_keys:
                for col in table.tableSchema.columns:
                    if col.name.lower() in PRIMARY_KEY_NAMES:
                        table.tableSchema.primaryKey = [col.name]
                        break
            for col in table.tableSchema.columns:
                if col.propertyUrl and col.propertyUrl.uri == TERMS['source'].uri:
                    table.tableSchema.foreignKeys.append(csvw.ForeignKey.fromdict({
                        'columnReference': [col.header],
                        'reference': {
                            'resource': self.source_table_name,
                            'columnReference': 'id'
                        }
                    }))
                    if translations[table.local_name].name:
                        tl = translations[table.local_name]
                        translations['{0}_{1}__{2}'.format(
                            table.local_name,
                            self.source_table_name,
                            col.header)] = TableTranslation(
                                name='{0}_{1}__cldf_source'.format(tl.name, self.source_table_name),
                                columns={'{0}_{1}'.format(
                                    table.local_name, table.tableSchema.primaryKey[0],
                                ): '{0}_{1}'.format(
                                    tl.name, tl.columns[table.tableSchema.primaryKey[0]],
                                )})
                    break

        # FIXME: There is something wrong with translations
        # print(translations)
        # Make sure `base` directory can be resolved:
        tg._fname = dataset.tablegroup._fname
        csvw.db.Database.__init__(
            self, tg, translate=functools.partial(translate, translations), **kw)

    def association_table_context(self, table, column, fkey):
        """
        Context for association tables is created calling this method.

        Note: If a custom value for the `context` column is created by overwriting this method,
        `select_many_to_many` must be adapted accordingly, to make sure the custom
        context is retrieved when reading the data from the db.

        :param table:
        :param column:
        :param fkey:
        :return: a pair (foreign key, context)
        """
        # The default implementation takes the column name as context:
        if '[' in fkey:
            assert fkey.endswith(']')
            fkey, _, rem = fkey.partition('[')
            return fkey, rem[:-1]
        return fkey, None


    def write(self, *, _force=False, _exists_ok=False, skip_extra=False, **items):
        """
        Creates a db file with the core schema.

        :param force: If `True` an existing db file will be overwritten.
        """
        if self.fname and self.fname.exists():
            if _force:
                self.fname.unlink()
            elif _exists_ok:
                pass
            else:
                raise ValueError('db file already exists, use _force=True to overwrite')

        with self.connection() as db:
            for table in self.tables:
                db.execute(table.sql(translate=self.translate))

            db.execute('PRAGMA foreign_keys = ON;')
            db.commit()

            refs = defaultdict(lambda: defaultdict(list))  # collects rows in association tables.
            for t in self.tables:
                if t.name not in items:
                    continue
                rows, keys = [], []
                cols = {c.name: c for c in t.columns}
                for i, row in enumerate(items[t.name]):
                    pk = row[t.primary_key[0]] \
                        if t.primary_key and len(t.primary_key) == 1 else None
                    values = []
                    for column, value in row.items():
                        if column in t.many_to_many:
                            assert pk
                            at = t.many_to_many[column]
                            atkey = tuple([at.name] + [c.name for c in at.columns])
                            if len(atkey) == 4:
                                for subvalue in value:
                                    fkey, context = self.association_table_context(t, column, subvalue)
                                    refs[atkey][pk, fkey].append(context)
                            elif len(atkey) == 3:
                                for subvalue in value:
                                    fkey, context = self.association_table_context(t, column, subvalue)
                                    assert context is None
                                    refs[atkey][pk, fkey] = None
                            else:
                                raise ValueError(
                                    f"Table {table.name} is not an association table")
                        else:
                            if column not in cols:
                                if skip_extra:
                                    continue
                                else:
                                    raise ValueError(
                                        'unspecified column {0} found in data'.format(column))
                            col = cols[column]
                            if isinstance(value, list):
                                # Note: This assumes list-valued columns are of datatype string!
                                value = (col.separator or ';').join(
                                    col.convert(vv) for vv in value)
                            else:
                                value = col.convert(value) if value is not None else None
                            if i == 0:
                                keys.append(col.name)
                            values.append(value)
                    rows.append(tuple(values))
                insert(db, self.translate, t.name, keys, *rows)

            for atkey, rows in refs.items():
                insert(db, self.translate, atkey[0], atkey[1:],
                       *[[key1, key2] + (
                           [self._duplicate_relationship_separator.join([
                               v for v in values if v])]
                           if values else [])
                         for (key1, key2), values in rows.items()])
            db.commit()

    def select_many_to_many(
            self,
            db,  # Why does it need this argument? Can't we just `with self.connection() as db:`?
            table: TableSpec,
            _=None
    ) -> t.Dict[str, t.List[t.Tuple[str, t.Optional[str]]]]:
        if len(table.columns) == 2:
            context = False
            context_sql = 'null'
        elif len(table.columns) == 3:
            context = True
            context_column = table.columns[-1]
            assert context_column.name not in table.primary_key
            context_column_name = quoted(context_column.name)
            context_sql = f"group_concat(COALESCE({context_column_name}, ''), '||')"
        else:
            raise ValueError(
                f"Table {table.name} is not an association table")
        sql = """\
SELECT {0}, group_concat({1}, ' '), {3}
FROM {2} GROUP BY {0}""".format(
                quoted(self.translate(table.name, table.columns[0].name)),
                quoted(self.translate(table.name, table.columns[1].name)),
                quoted(self.translate(table.name)),
                context_sql)
        cu = db.execute(sql)
        if context:
            return {
                key: ["{:}[{:}]".format(k, v) if v else k
                      for k, v in zip(vals.split(), contexts.split('||'))]
                for key, vals, contexts in cu.fetchall()}
        else:
            return {
                key: [v for v in val.split()]
                for key, val, _ in cu.fetchall()}

