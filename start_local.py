#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Script to start localhost server using cherrypy. Meant for local use only, since the user 'local'
is automatically logged in and authentication is skipped. For server installations a web server
such as Apache should be used.
Author: Amir Zeldes
"""

import cherrypy
import os, sys
from api import APIController, create_api_dispatcher, jsonify_error
from open import open_main
from structure import structure_main
from segment import segment_main
from admin import admin_main
from quick_export import quickexp_main

from cherrypy.lib import file_generator
try:
	from StringIO import StringIO
except ImportError:
	from io import BytesIO, StringIO
	from base64 import b64decode

print_out = sys.stdout.write

class Root(object):
	@cherrypy.expose
	def default(self,**kwargs):
		print_out(str(kwargs))
		return '<script>document.location.href="open";</script>'

	@cherrypy.expose
	def open(self,**kwargs):
		print_out(str(kwargs))
		return open_main("local","3","local",**kwargs)

	@cherrypy.expose
	def structure(self,**kwargs):
		print_out(str(kwargs))
		if "current_doc" not in kwargs:
			return '<script>document.location.href="open";</script>'
		elif "screenshot" in kwargs:
			cherrypy.response.headers['Content-Type'] = "image/png"
			cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="' + kwargs["current_doc"] + '.png"'
			if sys.version_info[0] == 2:
				return file_generator(StringIO(structure_main("local", "3", 'local', **kwargs)))
			else:
				return file_generator(BytesIO(b64decode(structure_main("local", "3", 'local', **kwargs))))
		else:
			return structure_main("local","3",'local',**kwargs)

	@cherrypy.expose
	def segment(self,**kwargs):
		print_out(str(kwargs))
		if "current_doc" not in kwargs:
			return '<script>document.location.href="open";</script>'
		else:
			return segment_main("local","3",'local',**kwargs)

	@cherrypy.expose
	def quick_export(self,**kwargs):
		print_out(str(kwargs))
		if "quickexp_doc" not in kwargs:
			return '<script>document.location.href="open";</script>'
		else:
			cherrypy.response.headers['Content-Type'] = "application/download"
			cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="'+kwargs["quickexp_doc"]+'"'
			return quickexp_main("local","3",'local',**kwargs)

	@cherrypy.expose
	def admin(self,**kwargs):
		print_out(str(kwargs))
		return admin_main("local","3",'local',**kwargs)


def CORS():
    """Adds CORS header to response (allows Javascript clients to use the API)."""
    cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"


dispatcher = create_api_dispatcher()

current_dir = os.path.dirname(os.path.realpath(__file__)) + os.sep
conf = {
	'/css': {'tools.staticdir.on': True,'tools.staticdir.dir': os.path.join(current_dir,'css')},
	'/img': {'tools.staticdir.on': True,'tools.staticdir.dir': os.path.join(current_dir,'img')},
	'/script': {'tools.staticdir.on': True,'tools.staticdir.dir': os.path.join(current_dir,'script')}
}

api_conf = {
    '/': {
        'request.dispatch': dispatcher,
        'error_page.default': jsonify_error,
        'tools.CORS.on': True,
        'request.show_tracebacks': True
    }
}
api_conf.update(conf)

cherrypy.tools.CORS = cherrypy.Tool('before_handler', CORS)
cherrypy.tree.mount(root=Root(), config=conf)
cherrypy.tree.mount(root=APIController(), script_name='/api', config=api_conf)

cherrypy.engine.start()
cherrypy.engine.block()
