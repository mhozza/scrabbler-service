#!/usr/bin/env python
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from scrabbler import scrabbler
from os import path
from glob import glob
import json
import argparse
import traceback
import sys


BASE_DIR = path.dirname(path.dirname(path.abspath(__file__)))
print(BASE_DIR)
SCRABBLER_DICTIONARIES = {
    path.splitext(path.basename(f))[0]: f for f in glob(f"{BASE_DIR}/dict/*.dic")
}

PERMUTATIONS_PATH = "/permutations"
REGEX_PATH = "/regex"
INIT_PATH = "/init"
GET_DICTS_PATH = "/dicts"
MAX_LIMIT = 100


class LazyDict:
    _WORD_LISTS = dict()
    _TRIES = dict()
    _loading = False

    def init_all(self):
        if self._loading:
            return
        self._loading = True
        for fname in SCRABBLER_DICTIONARIES:
            self.get_trie(fname)

    def get_word_list(self, dictionary_name):
        if dictionary_name not in self._WORD_LISTS:
            print(f"Loading wordlist for {dictionary_name}")
            self._WORD_LISTS[dictionary_name] = scrabbler.load_dictionary(
                SCRABBLER_DICTIONARIES[dictionary_name]
            )

        return self._WORD_LISTS[dictionary_name]

    def get_trie(self, dictionary_name):
        if dictionary_name not in self._TRIES:
            print(f"Loading trie for {dictionary_name}")
            self._TRIES[dictionary_name] = scrabbler.build_trie(
                self.get_word_list(dictionary_name)
            )

        return self._TRIES[dictionary_name]


lazy_dict = LazyDict()


class ScrabblerHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()

    def do_GET(self):
        """Respond to a GET request."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip("/")
        query = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}
        output = None
        try:
            if path == PERMUTATIONS_PATH:
                output = self.find_permutations(**query)
            elif path == REGEX_PATH:
                output = self.find_regex(**query)
            elif path == INIT_PATH:
                output = self.init_dicts(**query)
            elif path == GET_DICTS_PATH:
                output = self.get_dicts(**query)
            else:
                self.send_error(404)
                return
        except:
            traceback.print_exc(file=sys.stdout)
            if self.server.debug:
                self.send_error(
                    500,
                    message="Request processing error.",
                    explain=str(traceback.format_exc()),
                )
            self.send_error(500)
            return

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(output).encode("UTF-8"))

    def find_permutations(self, **kwargs):
        word = kwargs["word"]
        dictionary = kwargs["dict"]
        limit = min(int(kwargs.get("limit", 20)), MAX_LIMIT)
        prefix = kwargs.get("prefix", "")
        wildcard = kwargs.get("wildcard", "?")
        use_all_letters = kwargs.get("use_all_letters", "true") == "true"
        return scrabbler.find_permutations(
            word=word,
            trie=lazy_dict.get_trie(dictionary),
            limit=limit,
            prefix=prefix,
            wildcard=wildcard,
            use_all_letters=use_all_letters,
        )

    def find_regex(self, **kwargs):
        word = unquote(kwargs["word"])
        dictionary = kwargs["dict"]
        limit = min(int(kwargs.get("limit", 20)), MAX_LIMIT)
        return scrabbler.find_regex(
            regex=word,
            words=lazy_dict.get_word_list(dictionary),
            limit=limit,
        )

    def init_dicts(self, **kwargs):
        lazy_dict.init_all()
        return "Done"

    def get_dicts(self, **kwargs):
        return list(sorted(SCRABBLER_DICTIONARIES.keys()))


class ScrabblerServer(HTTPServer):
    def __init__(self, server_address, debug=False, *args, **kwargs):
        self.debug = debug
        super().__init__(
            server_address,
            ScrabblerHandler,
            *args,
            **kwargs,
        )


def run(server_class=HTTPServer):
    parser = argparse.ArgumentParser(description="Scrabbler service.")
    parser.add_argument("-p", "--port", type=int, default=9000)
    parser.add_argument(
        "--lazy-init",
        action="store_true",
        help="Don't initialize ditionaries on start.",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Send debug info in response.",
    )

    args = parser.parse_args()

    if not args.lazy_init:
        lazy_dict.init_all()

    server_address = ("", args.port)
    httpd = ScrabblerServer(server_address, debug=args.debug)
    httpd.serve_forever()


if __name__ == "__main__":
    run()