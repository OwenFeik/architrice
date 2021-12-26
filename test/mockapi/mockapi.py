import architrice

import http.server
import os
import threading
import urllib

SILENT = True

DIRECTORY = os.path.join(os.path.dirname(__file__), "web")


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def send_head(self):
        # This is a modified version of the source from
        # https://github.com/python/cpython/blob/main/Lib/http/server.py#L670
        # which allows files named like URL parameters to mimic an API
        #
        # The naming convention for such files is like so:
        # ?owner=Test&ownerexact=true
        # would become
        # owner=Test_ownerexact=true

        path = self.translate_path(self.path)

        f = None

        parts = urllib.parse.urlsplit(self.path)

        query_file = os.path.join(path, parts.query.replace("&", "_"))

        if os.path.isfile(query_file):
            path = query_file
        elif path.endswith("/") and os.path.isfile(path[:-1]):
            # allow trailing /
            path = path[:-1]
        elif os.path.isdir(path):
            if not parts.path.endswith("/"):
                self.send_response(http.server.HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (
                    parts[0],
                    parts[1],
                    parts[2] + "/",
                    parts[3],
                    parts[4],
                )
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None

            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)

        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(http.server.HTTPStatus.NOT_FOUND, "File not found")
            return None

        ctype = self.guess_type(path)
        try:
            fs = os.fstat(f.fileno())
            self.send_response(http.server.HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(fs[6]))
            self.send_header(
                "Last-Modified", self.date_time_string(fs.st_mtime)
            )
            self.end_headers()
            return f
        except:
            f.close()
            raise

    def log_request(self, *args, **kwargs):
        if not SILENT:
            super().log_request(*args, **kwargs)


PORT = 8192

server = http.server.HTTPServer(("", PORT), RequestHandler)

addr, port = server.server_address
URL = f"http://{addr}:{port}/"

thread = threading.Thread(target=server.serve_forever)


def run():
    thread.start()


def stop():
    server.shutdown()
    server.server_close()
    thread.join()

    for source in architrice.sources.sourcelist:
        source.URL_BASE = source._URL_BASE

    architrice.targets.card_info.SCRYFALL_BULK_DATA_URL = (
        architrice.targets.card_info._SCRYFALL_BULK_DATA_URL
    )


def mock():
    # Remap sources
    for source in architrice.sources.sourcelist:
        source._URL_BASE = source.URL_BASE
        source.URL_BASE = URL

    # Remap card_info
    architrice.targets.card_info._SCRYFALL_BULK_DATA_URL = (
        architrice.targets.card_info.SCRYFALL_BULK_DATA_URL
    )
    architrice.targets.card_info.SCRYFALL_BULK_DATA_URL = (
        URL + "bulk-data/default-cards"
    )

    run()
