#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This module is called from structure.py to take a screenshot of the RST graph.
It needs to call the rstviewer main.py script via a subprocess in make_img_via_temp,
since rendering of jsPlumb javascript fails if selenium/PhantomJS is invoked
directly under cherrypy.

Author: Amir Zeldes
"""

import tempfile, os, sys
import subprocess
import base64
from modules.rstweb_sql import get_export_string

def make_img_via_temp(input_text, command_params, mode="local",workdir=""):
	temp = tempfile.NamedTemporaryFile(delete=False)
	image = tempfile.NamedTemporaryFile(delete=False,suffix=".png")
	exec_out = ""
	try:
		temp.write(input_text.encode("utf8"))
		temp.close()

		command_params = [x if x != 'tempfilename' else temp.name for x in command_params]
		command_params = [x if x != 'imagefilename' else image.name for x in command_params]
		if workdir == "":
			proc = subprocess.Popen(command_params, stdout=subprocess.PIPE,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
			(stdout, stderr) = proc.communicate()
		else:
			proc = subprocess.Popen(command_params, stdout=subprocess.PIPE,stdin=subprocess.PIPE,stderr=subprocess.PIPE,cwd=workdir)
			(stdout, stderr) = proc.communicate()

	except Exception as e:
		print(e)
	finally:
		os.remove(temp.name)
		if mode == "server":
			#return image
			img = open(image.name, "rb").read()
			image.close()
			os.remove(image.name)
			return img

		else:
			with open(image.name, "rb") as imageFile:
				img_str = base64.b64encode(imageFile.read())
			image.close()
			os.remove(image.name)

			if sys.version_info[0] == 2:
				return base64.b64decode(img_str)
			else:
				return img_str


def get_png(current_doc, current_project, user, mode="local"):

	rs3 = get_export_string(current_doc, current_project, user)
	viewer_path = os.path.dirname(os.path.realpath(__file__))+os.sep + "modules" + os.sep + "viewer" + os.sep + "main" + os.sep + "main.py"
	cmd = ["python", viewer_path, "tempfilename","imagefilename"]
	png_str = make_img_via_temp(rs3,cmd,mode,os.path.dirname(os.path.realpath(__file__))+os.sep + "modules" + os.sep + "viewer" + os.sep + "main" + os.sep)
	return png_str
