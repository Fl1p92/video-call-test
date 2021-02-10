import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

from jinja2 import Environment, FileSystemLoader, select_autoescape


env = Environment(
    loader=FileSystemLoader('.'),
    autoescape=select_autoescape(['html', 'xml'])
)

template = env.get_template('index_template.html')

rendered_page = template.render(
    signaling_ip=os.environ.get('BACKEND_IP', 'localhost'),
    signaling_port=os.environ.get('BACKEND_PORT', '8080'),
)

with open('index.html', 'w', encoding="utf8") as file:
    file.write(rendered_page)


server = HTTPServer(('0.0.0.0', int(os.environ.get('CLIENT_PORT', 7000))), SimpleHTTPRequestHandler)
server.serve_forever()
