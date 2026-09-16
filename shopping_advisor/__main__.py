"""The product entry point; each layer owns its arguments and behavior."""

import argparse
import importlib
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='shopping_advisor',
        description='Shopping Advisor: evidence-backed shopping research.')
    parser.add_argument('command',
                        choices=('study', 'analysis', 'run', 'maintenance'),
                        help='study: check, save and verify research; '
                             'analysis: compare product evidence; '
                             'run: inspect and replay acquisition; '
                             'maintenance: run the verification gate')
    parser.add_argument('arguments', nargs=argparse.REMAINDER,
                        help='arguments for the selected command; use --help '
                             'after its name for details')
    args = parser.parse_args(argv)
    module_name = {'study': '.study.__main__',
                   'analysis': '.analysis.__main__', 'run': '.run',
                   'maintenance': '.maintenance.__main__'}[args.command]
    module = importlib.import_module(module_name, package='shopping_advisor')
    return module.main(args.arguments)


if __name__ == '__main__':
    sys.exit(main())
