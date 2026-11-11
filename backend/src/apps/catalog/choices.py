from django.db import models


class Connection(models.TextChoices):
    SIDE = 'side', 'боковое'
    DIAGONAL = 'diagonal', 'диагональное'
    BOTTOM_LEFT = 'bottom_left', 'нижнее левое'
    BOTTOM_RIGHT = 'bottom_right', 'нижнее правое'
    BOTTOM_UNIVERSAL = 'bottom_universal', 'нижнее, слева или справа'
    BOTTOM_ENDS = 'bottom_ends', 'нижнее по краям'
    BOTTOM_CENTER = 'bottom_center', 'нижнее центральное'
    ELECTRIC_LEFT = 'electric_left', 'под электрику слева'
    ELECTRIC_RIGHT = 'electric_right', 'под электрику справа'


class Orientation(models.TextChoices):
    HORIZONTAL = 'h', 'горизонтальный'
    VERTICAL = 'v', 'вертикальный'


class Mount(models.TextChoices):
    WALL = 'wall', 'настенный'
    FLOOR = 'floor', 'напольный'


class Currency(models.TextChoices):
    BYN = 'BYN', 'BYN'
    RUB = 'RUB', 'RUB'
    EUR = 'EUR', 'EUR'
    USD = 'USD', 'USD'


class Heating(models.TextChoices):
    WATER = 'water', 'водяной'
    ELECTRIC = 'electric', 'электрический'
    COMBINED = 'combined', 'комбинированный'


class Finish(models.TextChoices):
    MATTE = 'matte', 'матовая'
    GLOSS = 'gloss', 'глянцевая'
