from textanalysis_flask import app
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

http_server = HTTPServer(WSGIContainer(app))
http_server.bind(8080)
http_server.start(0)
IOLoop.current().start()

