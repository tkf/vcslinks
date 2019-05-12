"""
Open relevant pages in GitHub/GitLab/Bitbucket.
"""

import argparse
import shlex
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from typing import List

from .api import analyze
from .weburl import WebURL, parselines


@dataclass
class Application:
    dry_run: bool
    browser: List[str]

    @classmethod
    def run(cls, dry_run, browser, func, **kwargs):
        browser_cmd = shlex.split(browser) if browser else []
        weburl = analyze()
        return func(cls(dry_run=dry_run, browser=browser_cmd), weburl=weburl, **kwargs)

    def open_url(self, url):
        if self.dry_run:
            print("Open:", url)
        elif self.browser:
            subprocess.check_call(self.browser + [url])
        else:
            webbrowser.open(url)


def cli_auto(app: Application, weburl: WebURL):
    """
    Open repository root or a PR submission page (if appropriate).
    """
    if weburl.local_branch.need_pull_request():
        url = weburl.pull_request()
    else:
        url = weburl.rooturl
    app.open_url(url)


def cli_commit(app: Application, weburl: WebURL, revision):
    """
    Open commit page for a <revision>.
    """
    url = weburl.commit(revision)
    app.open_url(url)


def cli_log(app: Application, weburl: WebURL, revision):
    """
    Open log page for a <revision>.
    """
    url = weburl.log(revision)
    app.open_url(url)


def cli_file(app: Application, weburl: WebURL, permalink, lines: str, **kwargs):
    """
    Open file page.
    """
    _permalink = {"auto": None, "yes": True, "no": False}[permalink]
    _lines = parselines(lines)
    url = weburl.file(permalink=_permalink, lines=_lines, **kwargs)
    app.open_url(url)


class CustomFormatter(
    argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
):
    pass


def make_parser(doc=__doc__):
    parser = argparse.ArgumentParser(
        formatter_class=CustomFormatter, description=__doc__
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--browser")

    subparsers = parser.add_subparsers()

    def subp(command, func):
        doc = func.__doc__
        title = None
        for title in filter(None, map(str.strip, (doc or "").splitlines())):
            break
        p = subparsers.add_parser(
            command, formatter_class=CustomFormatter, help=title, description=doc
        )
        p.set_defaults(func=func)
        return p

    p = subp("auto", cli_auto)

    p = subp("commit", cli_commit)
    p.add_argument("revision", nargs="?", default="HEAD")

    p = subp("log", cli_log)
    p.add_argument("revision", nargs="?")

    p = subp("file", cli_file)
    p.add_argument(
        "--permalink",
        default="auto",
        choices=("auto", "yes", "no"),
        help="""
        Resolve <revision> if `yes`.  Use branch name if `no`.  If
        `auto` (default), resolve <revision> if <lines> are specified.
        """,
    )
    p.add_argument(
        "file",
        help="""
        File path.
        """,
    )
    p.add_argument(
        "lines",
        nargs="?",
        help="""
        A number or a pair of number separated by a hyphen `-`.
        """,
    )
    p.add_argument("revision", nargs="?", default="master")

    parser.set_defaults(func=cli_auto)
    return parser


def print_outputs(proc):
    if proc.stdout:
        print("STDOUT:", file=sys.stderr)
        print(proc.stdout, file=sys.stderr)
    if proc.stderr:
        print("STDERR:", file=sys.stderr)
        print(proc.stderr, file=sys.stderr)


def main(args=None):
    parser = make_parser()
    ns = parser.parse_args(args)
    try:
        Application.run(**vars(ns))
    except subprocess.CalledProcessError as err:
        print(err, file=sys.stderr)
        print_outputs(err)
        sys.exit(1)


if __name__ == "__main__":
    main()