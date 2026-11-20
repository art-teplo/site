"""Decimal-цена PostgreSQL: те же два округления, что pricing/configurations."""

# Имена — только внутренние поля CTE; пользовательские значения передаются параметрами.
PRICE_SQL = """
CASE WHEN (has_groups AND selected_group_id IS NULL) OR any_ral THEN NULL
 WHEN configuration_key IS NULL THEN
   ROUND(source_price_byn * (100 + colour_percent) / 100, 0)
 WHEN currency != 'RUB' OR surcharge_rub IS NULL THEN NULL
 ELSE ROUND(ROUND(
   (ROUND(source_price * (100 + colour_percent) / 100, 0)
      + surcharge_rub + base_adjustment_rub)
   * rate * (1 + markup_percent / 100), 2), 0)
END
"""
