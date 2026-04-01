import http.server, os
os.chdir('/Users/noahwinter/Desktop/Projects/square_root_game')
http.server.test(HandlerClass=http.server.SimpleHTTPRequestHandler, port=5500, bind='127.0.0.1')
