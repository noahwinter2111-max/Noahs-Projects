import http.server
import os

PORT = 3000
DIR = "/Users/noahwinter/Desktop/Projects/square_root_game"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)
    def log_message(self, format, *args):
        pass

with http.server.HTTPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
