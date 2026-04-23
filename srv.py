import sys, os, socketserver, http.server
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
os.chdir("/Users/noahwinter/Desktop/Projects/square_root_game")
Handler = http.server.SimpleHTTPRequestHandler
Handler.log_message = lambda *a: None
with socketserver.TCPServer(("", port), Handler) as s:
    s.serve_forever()
