"""Одно SQL-множество доступных предложений для каталога и серии."""

import json
from contextlib import contextmanager
from copy import copy
from dataclasses import dataclass, field, replace
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from django.core.exceptions import EmptyResultSet
from django.db import connection, transaction

from . import filters, schema, serializers
from .choices import Connection, Mount
from .models import CurrencyRate, Variant
from .offer_pricing import PRICE_SQL

UNSET = object()
FIELDS = {
    'height_mm',
    'width_mm',
    'length_mm',
    'depth_mm',
    'axis_mm',
    'sections',
    'tubes',
    'power_w',
    'orientation',
    'connection',
    'mount',
    'thermovalve',
    'article',
    'series_id',
}


@contextmanager
def catalog_query_plan():
    # На выборках по типу и бренду PostgreSQL занижает число предложений.
    # Дорогие nested loop повторно сканируют группы цветов для каждой строки.
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute('SHOW enable_nestloop')
        (previous,) = cursor.fetchone()
        cursor.execute('SET LOCAL enable_nestloop = off')
        yield
        # При ошибке настройка откатится вместе с транзакцией или savepoint.
        # При успехе восстанавливаем её и внутри уже открытой транзакции.
        cursor.execute(
            "SELECT set_config('enable_nestloop', %s, true)", (previous,)
        )


def offer_query(
    variants, *, color=None, rate=UNSET, group_id=None, bulk=False
):
    if rate is UNSET:
        rate = CurrencyRate.latest('RUB')
    try:
        base, params = variants.order_by().query.sql_with_params()
    except EmptyResultSet:
        base, params = variants.model.objects.filter(
            pk__isnull=True
        ).query.sql_with_params()
    group_params = []
    if group_id is not None:
        group_condition = 'g.id=%s'
        group_params = [group_id]
        group_order = 'g.position, g.id'
    elif color == 'any-ral':
        group_condition = 'g.any_ral'
        group_order = 'g.position, g.id'
    elif color and color.startswith('any-'):
        number = color[4:]
        group_condition = 'g.any_ral AND g.id = %s'
        group_params = [int(number) if number.isdigit() else -1]
        group_order = 'g.position, g.id'
    elif color:
        group_condition = """EXISTS (SELECT 1 FROM catalog_colorgroup_colors gc
            JOIN catalog_color c ON c.id=gc.color_id
            WHERE gc.colorgroup_id=g.id AND c.code=%s)"""
        group_params = [color]
        group_order = 'g.position, g.id'
    else:
        group_condition = '(NOT g.any_ral OR g.is_base)'
        group_order = (
            'g.is_base DESC, GREATEST(CEIL(g.percent),0), g.position, g.id'
        )
    if bulk:
        # In the catalogue, pick once per series or restricted variant.
        # Keep the restriction row even when it matches no eligible group.
        group_ctes = f"""
        ranked_groups AS (
          SELECT g.id, g.series_id,
            ROW_NUMBER() OVER (PARTITION BY g.series_id ORDER BY {group_order}) AS priority
          FROM catalog_colorgroup g WHERE {group_condition}
        ), variant_groups AS (
          SELECT DISTINCT ON (vg.variant_id) vg.variant_id, g.id
          FROM catalog_variant_color_groups vg
          JOIN catalog_variant v ON v.id=vg.variant_id
          LEFT JOIN ranked_groups g ON g.id=vg.colorgroup_id AND g.series_id=v.series_id
          ORDER BY vg.variant_id, g.priority NULLS LAST
        ),
        """  # noqa: S608
        group_join = """
        LEFT JOIN variant_groups vg ON vg.variant_id=v.id
        LEFT JOIN ranked_groups sg ON vg.variant_id IS NULL AND sg.series_id=v.series_id AND sg.priority=1
        LEFT JOIN catalog_colorgroup grp ON grp.id=COALESCE(vg.id,sg.id)
        """
        query_params = (*params, *group_params, rate)
    else:
        group_ctes = ''
        group_join = f"""
        LEFT JOIN LATERAL (
          SELECT g.id,g.percent,g.any_ral FROM catalog_colorgroup g WHERE g.series_id=s.id
            AND (NOT EXISTS(SELECT 1 FROM catalog_variant_color_groups vg WHERE vg.variant_id=v.id)
              OR EXISTS(SELECT 1 FROM catalog_variant_color_groups vg WHERE vg.variant_id=v.id AND vg.colorgroup_id=g.id))
            AND {group_condition} ORDER BY {group_order} LIMIT 1
        ) grp ON TRUE
        """  # noqa: S608
        query_params = (*params, rate, *group_params)
    sql = f"""
    WITH base AS ({base}), {group_ctes} prepared AS (
      SELECT v.id AS variant_id, v.series_id, v.article, v.height_mm, v.width_mm,
        v.depth_mm, v.length_mm, v.axis_mm, v.sections, v.tubes, v.power_w, v.attrs,
        v.price AS source_price, v.price_byn AS source_price_byn, v.currency,
        NULLIF(COALESCE(NULLIF(v.orientation,''),NULLIF(s.factory_orientation,'')),'') AS orientation,
        CASE WHEN r.id IS NULL THEN v.connection ELSE r.connection END AS connection,
        NULLIF(CASE WHEN r.id IS NULL THEN v.mount ELSE r.mount END,'') AS mount,
        CASE WHEN r.id IS NULL THEN v.thermovalve ELSE r.thermovalve END AS thermovalve,
        CASE WHEN r.id IS NOT NULL THEN 'kzto-' || r.id::text END AS configuration_key,
        r.label AS configuration_label, r.source_id, r.surcharge_rub, r.base_adjustment_rub,
        s.markup_percent, b.slug AS brand_slug, %s::numeric AS rate,
        grp.id AS selected_group_id, grp.any_ral,
        COALESCE(GREATEST(CEIL(grp.percent),0),0) AS colour_percent,
        EXISTS(SELECT 1 FROM catalog_colorgroup sg WHERE sg.series_id=s.id) AS has_groups
      FROM base v JOIN catalog_series s ON s.id=v.series_id JOIN catalog_brand b ON b.id=s.brand_id
      LEFT JOIN catalog_connectionoption r ON s.offer_mode='configured' AND r.series_id=s.id
        AND r.tubes=v.tubes AND r.allowed_sections @> jsonb_build_array(v.sections)
      {group_join}
      WHERE s.offer_mode='direct' OR r.id IS NOT NULL
    ), offers AS (SELECT prepared.*, {PRICE_SQL} AS price FROM prepared)
    """  # noqa: S608 -- SQL компилятора/статические выражения, значения только параметрами
    return OfferQuery(sql, query_params)


@dataclass(frozen=True)
class OfferQuery:
    cte: str
    params: tuple
    parsed: dict = field(default_factory=dict)
    execution: str | None = None

    def filter(self, parsed):
        return replace(self, parsed={**self.parsed, **parsed})

    def with_execution(self, key):
        return replace(self, execution=key or None)

    def expression(self, source):
        if source == 'price_byn':
            return 'price', []
        if source == 'series__brand__slug':
            return 'brand_slug', []
        if source in FIELDS:
            return source, []
        if source.startswith('attrs__'):
            return '(attrs ->> %s)', [source.removeprefix('attrs__')]
        message = f'Неизвестный источник предложения: {source}'
        raise ValueError(message)

    def _range_condition(self, column, column_args, values):
        clauses, args = [], []
        divisor, low, high = values
        for sign, bound in [('>=', low), ('<=', high)]:
            if bound is not None:
                clauses.append(f'{column} {sign} %s')
                args.extend([*column_args, bound * divisor])
        return clauses, args

    def execution_condition(self):
        clauses, args = [], []
        if self.execution:
            if self.execution.startswith('direct:'):
                parts = self.execution.split(':')
                if (
                    len(parts) != 5
                    or not parts[1].isdigit()
                    or parts[4] not in ('t', 'f', 'u')
                ):
                    clauses.append('FALSE')
                else:
                    clauses.append(
                        'configuration_key IS NULL AND COALESCE(tubes,0)=%s AND connection=%s'
                    )
                    args.extend([int(parts[1]), parts[2]])
                    # Старые ссылки сохраняют монтаж; новые группы all
                    # объединяют реальные артикулы разного монтажа.
                    if parts[3] != 'all':
                        clauses.append("COALESCE(mount,'')=%s")
                        args.append('' if parts[3] == 'u' else parts[3])
                    clauses.append('thermovalve IS NOT DISTINCT FROM %s')
                    args.append({'t': True, 'f': False, 'u': None}[parts[4]])
            else:
                clauses.append('configuration_key=%s')
                args.append(self.execution)
        return clauses, args

    def where(self, *, skip=()):
        clauses, args = [], []
        for key, entry in self.parsed.items():
            if key in skip:
                continue
            kind, source, *values = entry
            if kind == schema.COLORS:
                clauses.append('selected_group_id IS NOT NULL')
                continue
            if kind == 'execution':
                parts = []
                for tubes, conn in values[0]:
                    parts.append(
                        '((tubes=%s OR (tubes IS NULL AND %s=0)) AND connection=%s)'
                    )
                    args.extend([tubes, tubes, conn])
                clauses.append('(' + ' OR '.join(parts) + ')')
                continue
            column, column_args = self.expression(source)
            if kind == schema.RANGE:
                conditions, parameters = self._range_condition(
                    column, column_args, values
                )
                clauses.extend(conditions)
                args.extend(parameters)
            elif kind == schema.LIST:
                chosen = values[0]
                if chosen:
                    clauses.append(
                        f'{column} IN ({",".join(["%s"] * len(chosen))})'
                    )
                    args.extend([*column_args, *chosen])
        conditions, parameters = self.execution_condition()
        clauses.extend(conditions)
        args.extend(parameters)
        return (' AND '.join(clauses) or 'TRUE'), args

    def select(self, columns, *, skip=(), suffix='', args=(), select_args=()):
        where, params = self.where(skip=skip)
        with connection.cursor() as cursor:
            cursor.execute(
                f'{self.cte} SELECT {columns} FROM offers WHERE {where} {suffix}',  # noqa: S608
                [*self.params, *select_args, *params, *args],
            )
            names = [c[0] for c in cursor.description]
            return [
                dict(zip(names, row, strict=True)) for row in cursor.fetchall()
            ]

    def page(self, number, size):
        number = max(1, int(number))
        return self.select(
            '*',
            suffix='ORDER BY height_mm,width_mm,power_w,variant_id,configuration_key LIMIT %s OFFSET %s',
            args=(size, (number - 1) * size),
        )

    def count(self):
        return self.select('COUNT(*) AS n')[0]['n']

    def series_ids(self):
        return [r['series_id'] for r in self.select('DISTINCT series_id')]

    def price_bounds(self):
        row = self.select('MIN(price) AS low, MAX(price) AS high')[0]
        return row['low'], row['high']

    def _facet_data(self, fields):
        """Один расчёт предложений для всех диапазонов и списков.

        FILTER снимает только собственное ограничение. Исходное число
        значений не зависит от текущего выбора покупателя.
        """
        expressions, args = [], []
        fields = [f for f in fields if f.filter and f.kind != schema.COLORS]
        for f in fields:
            col, params = self.expression(f.source)
            expressions.append(
                f"COUNT(DISTINCT NULLIF(({col})::text,'')) AS {f.key}_total"
            )
            args.extend(params)
            expressions.append(
                f"BOOL_OR(NULLIF(({col})::text,'') IS NULL) AS {f.key}_unknown"
            )
            args.extend(params)
            skip = (
                (f.key, 'execution')
                if f.key in ('tubes', 'connection', 'thermovalve')
                else (f.key,)
            )
            query = (
                replace(self, execution=None)
                if self.execution and len(skip) > 1
                else self
            )
            where, where_args = query.where(skip=skip)
            if f.kind == schema.RANGE:
                for aggregate, suffix in [('MIN', 'lo'), ('MAX', 'hi')]:
                    expressions.append(
                        f'{aggregate}({col}) FILTER (WHERE {where}) AS {f.key}_{suffix}'
                    )
                    args.extend([*params, *where_args])
            else:
                expressions.append(
                    f"(SELECT COALESCE(jsonb_agg(jsonb_build_object('value',value,'n',n)),'[]'::jsonb) "  # noqa: S608 -- выражения схемы; значения параметризованы
                    f'FROM (SELECT {col} AS value,COUNT(*) AS n FROM offers '
                    f'WHERE {where} GROUP BY value) available) AS {f.key}_values'
                )
                args.extend([*params, *where_args])
        if not fields:
            return {}
        # Один раз материализуем предложения, а не пересчитываем правила
        # и группы цветов при каждом отдельном скане списка.
        cte = (
            self.cte.replace('offers AS (', 'offers AS MATERIALIZED (')
            if any(f.kind == schema.LIST for f in fields)
            else self.cte
        )
        sources = [f.source for f in fields]
        sources.extend(
            entry[1]
            for entry in self.parsed.values()
            if entry[0] not in (schema.COLORS, 'execution')
        )
        columns = {
            'configuration_key',
            'tubes',
            'connection',
            'mount',
            'thermovalve',
            'selected_group_id',
        }
        for source in sources:
            if source.startswith('attrs__'):
                columns.add('attrs')
            elif source == schema.BRAND_SOURCE:
                columns.add('brand_slug')
            elif source != 'price_byn':
                columns.add(source)
        # Материализуем только поля фасетов: артикулы, исходные цены,
        # служебные подписи правил здесь не нужны.
        cte = cte.replace(
            'SELECT prepared.*,',
            f'SELECT {",".join(sorted(columns))},',
        )
        base = replace(self, cte=cte, parsed={}, execution=None)
        return base.select(','.join(expressions), select_args=args)[0]

    @staticmethod
    def _range_facets(fields, data):
        result = {}
        for f in fields:
            if f.kind != schema.RANGE or not f.filter:
                continue
            low, high = data[f'{f.key}_lo'], data[f'{f.key}_hi']
            digits = Decimal('0.1') if f.divisor != 1 else Decimal(1)

            def value(v, rounding, divisor=f.divisor, precision=digits):
                if v is None:
                    return None
                v = (Decimal(v) / divisor).quantize(
                    precision, rounding=rounding
                )
                return int(v) if v == v.to_integral_value() else float(v)

            result[f.key] = {
                'key': f.key,
                'label': f.label,
                'kind': schema.RANGE,
                'unit': f.unit,
                'min': value(low, ROUND_FLOOR),
                'max': value(high, ROUND_CEILING),
                'total_values': data[f'{f.key}_total'],
                'has_unknown': bool(data[f'{f.key}_unknown']),
            }
        return result

    def range_facets(self, fields):
        fields = [f for f in fields if f.kind == schema.RANGE and f.filter]
        return self._range_facets(fields, self._facet_data(fields))

    def facets(self, fields):
        data = self._facet_data(fields)
        result, ranges = [], self._range_facets(fields, data)
        for f in fields:
            if not f.filter:
                continue
            if f.kind == schema.RANGE:
                facet = ranges[f.key]
                if not facet['total_values'] and f.key not in self.parsed:
                    continue
            elif f.kind == schema.COLORS:
                facet = self.colour_facet(f)
            else:
                rows = [
                    r
                    for r in json.loads(data[f'{f.key}_values'])
                    if r['value'] is not None and r['value'] != ''
                ]

                def code(v):
                    return str(v).lower() if isinstance(v, bool) else str(v)

                counts = {code(r['value']): r['n'] for r in rows}
                labels = filters._value_labels(f, list(counts))  # noqa: SLF001
                values = sorted(counts, key=lambda v: filters._sort_key(f, v))  # noqa: SLF001
                facet = {
                    'key': f.key,
                    'label': f.label,
                    'kind': schema.LIST,
                    'total_values': data[f'{f.key}_total'],
                    'has_unknown': bool(data[f'{f.key}_unknown']),
                    'values': [
                        {
                            'value': v,
                            'label': labels.get(v, v),
                            'count': counts[v],
                        }
                        for v in values
                    ],
                }
            if (
                f.kind == schema.RANGE
                or facet['values']
                or f.key in self.parsed
            ):
                result.append(facet)
        return result

    def colour_facet(self, f):
        # Предложения считаются отдельно; один цвет в нескольких группах не дублируется.
        # Считаем по ID, NULL обозначает «Любой RAL». Подписи нужны только итоговым строкам.
        where, params = self.where(skip=(f.key, 'price'))
        price_sql = (
            PRICE_SQL.replace('selected_group_id', 'g.id')
            .replace('colour_percent', 'GREATEST(CEIL(g.percent),0)')
            .replace('any_ral', 'g.any_ral')
        )
        price_entry = self.parsed.get('price')
        if price_entry:
            conditions, values = self._range_condition(
                f'({price_sql})', [], price_entry[2:]
            )
            where += ' AND ' + ' AND '.join(conditions) if conditions else ''
            params.extend(values)
        sql = f"""{self.cte}, palette AS (
            SELECT colorgroup_id,color_id FROM catalog_colorgroup_colors
            UNION ALL
            SELECT g.id,NULL
            FROM catalog_colorgroup g WHERE g.any_ral
          ), colour_counts AS (
            SELECT color_id,COUNT(*) AS n FROM (
              SELECT DISTINCT o.variant_id,o.configuration_key,p.color_id
              FROM offers o JOIN catalog_colorgroup g ON g.series_id=o.series_id
              JOIN palette p ON p.colorgroup_id=g.id
              WHERE {where}
               AND (NOT EXISTS(SELECT 1 FROM catalog_variant_color_groups vg WHERE vg.variant_id=o.variant_id)
                 OR EXISTS(SELECT 1 FROM catalog_variant_color_groups vg WHERE vg.variant_id=o.variant_id AND vg.colorgroup_id=g.id))
            ) matched GROUP BY color_id
          )
          SELECT COALESCE(c.code,'any-ral') AS code,
            COALESCE(c.name,'Любой RAL — по запросу'),
            COALESCE(c.hex,'conic-gradient(var(--color-accent), var(--color-cream-paper), var(--color-near-black), var(--color-accent))'),
            counts.n
          FROM colour_counts counts LEFT JOIN catalog_color c ON c.id=counts.color_id
          ORDER BY code"""  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, [*self.params, *params])
            values = [
                {'value': c, 'label': n, 'hex': h, 'count': count}
                for c, n, h, count in cursor.fetchall()
            ]
        return {
            'key': f.key,
            'label': f.label,
            'kind': schema.COLORS,
            'values': values,
        }


def serialize_rows(rows):
    variants = {
        v.pk: v
        for v in Variant.objects.filter(pk__in={r['variant_id'] for r in rows})
        .select_related('series')
        .prefetch_related('color_groups')
    }
    result = []
    for row in rows:
        variant = copy(variants[row['variant_id']])
        for key in ('orientation', 'mount', 'connection', 'thermovalve'):
            setattr(variant, key, row[key])
        data = serializers.row(
            variant, int(row['price']) if row['price'] is not None else None
        )
        if row['configuration_key']:
            data.pop('price_byn', None)
            data.update(
                configuration_key=row['configuration_key'],
                configuration_label=row['configuration_label'],
            )
        result.append(data)
    return result


def query_for_series(series, params, *, variants=None, detail=False):
    variants = (
        Variant.objects.filter(series=series, is_active=True)
        if variants is None
        else variants
    )
    fields = [
        f
        for f in schema.for_category(series.category.slug)
        if f.key != 'brand'
    ]
    parsed = filters.parse(params, fields)
    raw = params.get('color', '').split(',')[0].strip()
    color = (
        raw
        if raw.startswith('any-')
        else (parsed.get('color') or [None, None, [None]])[2][0]
    )
    if detail:
        parsed.pop('color', None)
    elif raw.startswith('any-'):
        parsed['color'] = (schema.COLORS, schema.COLOR_SOURCE, [raw])
    query = offer_query(variants, color=color).filter(parsed)
    key = params.get('execution', '')
    if key.startswith('kzto-') or (key and 'execution' not in parsed):
        query = query.with_execution(key)
    return query, fields


def execution_metadata(query):
    columns = 'COALESCE(tubes,0) AS tubes,connection,CASE WHEN configuration_key IS NULL THEN NULL ELSE mount END AS execution_mount,thermovalve,configuration_key,configuration_label,source_id,COUNT(*) AS n'
    rows = query.select(
        columns,
        suffix='GROUP BY COALESCE(tubes,0),connection,execution_mount,thermovalve,configuration_key,configuration_label,source_id',
    )
    # Неизвестное подключение не подтверждает отдельного исполнения.
    # Рядность при этом остаётся самостоятельной характеристикой.
    rows = [r for r in rows if r['connection'] or r['configuration_key']]
    pairs, duplicate_labels = {}, {}
    for row in rows:
        pair = (row['tubes'], row['connection'])
        pairs[pair] = pairs.get(pair, 0) + 1
        if row['configuration_key']:
            identity = (row['tubes'], row['configuration_label'])
            duplicate_labels.setdefault(identity, set()).add(
                row['execution_mount']
            )
    labels, mounts = dict(Connection.choices), dict(Mount.choices)
    order = list(Connection.values)
    result = []
    for row in rows:
        n, conn = row['tubes'], row['connection']
        key = row['configuration_key'] or f'{n}-{conn}'
        if not row['configuration_key'] and pairs[(n, conn)] > 1:
            valve = (
                'u'
                if row['thermovalve'] is None
                else 't'
                if row['thermovalve']
                else 'f'
            )
            key = f'direct:{n}:{conn}:all:{valve}'
        label = row['configuration_label'] or str(labels.get(conn, conn))
        if not row['configuration_key'] and row['thermovalve'] is not None:
            label += (
                ', со встроенным термоклапаном'
                if row['thermovalve']
                else ', без термоклапана'
            )
        if (
            row['configuration_key']
            and row['execution_mount']
            and len(duplicate_labels[(n, row['configuration_label'])]) > 1
        ):
            label += f', {mounts.get(row["execution_mount"], row["execution_mount"])}'
        result.append(
            {
                'key': key,
                'tubes': n,
                'connection': conn,
                'label': label,
                'count': row['n'],
                'mount': row['execution_mount'],
                'thermovalve': row['thermovalve'],
                'source_id': row['source_id'],
            }
        )
    configured = any(r['configuration_key'] for r in rows)
    result.sort(
        key=lambda e: (
            int(configured and e['connection'] not in ('side', 'bottom_ends')),
            -e['count'],
            -e['tubes'],
            order.index(e['connection'])
            if e['connection'] in order
            else len(order),
            e['key'],
        )
    )
    return result


def variant_response(series, variants, params, *, all_limit=500):
    from django.core.paginator import Paginator  # noqa: PLC0415

    query, fields = query_for_series(series, params, variants=variants)
    count = query.count()
    all_rows = params.get('page') == 'all'
    page = (
        1
        if all_rows
        else Paginator(range(count), 20).get_page(params.get('page')).number
    )
    rows = query.page(page, all_limit if all_rows else 20)
    return {
        'count': count,
        'results': serialize_rows(rows),
        'facets': query.facets(fields),
        'price_from': query.price_bounds()[0],
        'count_label': 'конфигурации',
    }


def detail_response(series, variants, params):
    from django.http import Http404  # noqa: PLC0415

    from .pricing import available_groups  # noqa: PLC0415

    query, _ = query_for_series(series, params, variants=variants, detail=True)
    rows = query.select(
        '*',
        suffix="ORDER BY CASE WHEN connection='side' THEN 0 ELSE 1 END,height_mm,width_mm,variant_id LIMIT 1",
    )
    if not rows:
        raise Http404
    result = serialize_rows(rows)[0]
    variant = variants.prefetch_related('color_groups').get(
        pk=rows[0]['variant_id']
    )
    groups = {g.pk: g for g in series.color_groups.all()}
    result['available_groups'] = [
        g.pk for g in available_groups(variant, groups)
    ]
    return result
