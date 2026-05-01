#!/usr/bin/env python3
from http.server import CGIHTTPRequestHandler, HTTPServer
import cgitb
import socket

cgitb.enable()

server_address = ("", 8000)
CGIHTTPRequestHandler.cgi_directories = ["/cgi-bin"]

def get_local_ip():
	try:
		with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
			sock.connect(("8.8.8.8", 80))
			return sock.getsockname()[0]
	except OSError:
		return socket.gethostbyname(socket.gethostname())

httpd = HTTPServer(server_address, CGIHTTPRequestHandler)
local_ip = get_local_ip()
print(f"Server running on http://{local_ip}:8000/")
print(f"CGI directory: http://{local_ip}:8000/cgi-bin/")
httpd.serve_forever()

