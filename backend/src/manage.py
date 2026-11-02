#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')
    from django.core.management import (  # noqa: PLC0415
        execute_from_command_line,
    )

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
