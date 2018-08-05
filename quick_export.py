#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This script generates an rs3 format export for a given document. Intended to be used for quick
export from the web interface using an AJAX call.
Author: Amir Zeldes
"""


import cgitb
import codecs
import sys
import cgi
import os
from modules.configobj import ConfigObj
from modules.logintools import login
from modules.rstweb_sql import get_export_string

def quickexp_main(user, admin, mode, **kwargs):

	scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
	userdir = scriptpath + "users" + os.sep
	theform = kwargs

	UTF8Writer = codecs.getwriter('utf8')
	sys.stdout = UTF8Writer(sys.stdout)

	cgitb.enable()

	###GRAPHICAL PARAMETERS###
	top_spacing = 20
	layer_spacing = 60

	config = ConfigObj(userdir + 'config.ini')
	templatedir = scriptpath + config['controltemplates'].replace("/",os.sep)

	if "quickexp_doc" in theform:
		current_doc = theform["quickexp_doc"]
		current_project = theform["quickexp_project"]
	else:
		current_doc = ""
		current_project = ""


	cpout = ""
	if mode == "server":
		cpout += "Content-Type: application/download\n"
		cpout += "Content-Disposition: attachment; filename=" + current_doc + "\n\n"
	else:
		#cpout += "Content-Type: application/download\n\n\n"
		pass

	cpout += get_export_string(current_doc,current_project,user)
	if mode == "server":
		return cpout
	else:
		return bytes(cpout.encode('utf-8'))

# Main script when running from Apache
def quickexp_main_server():
	thisscript = os.environ.get('SCRIPT_NAME', '')
	action = None
	theform = cgi.FieldStorage()
	scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
	userdir = scriptpath + "users" + os.sep
	action, userconfig = login(theform, userdir, thisscript, action)
	user = userconfig["username"]
	admin = userconfig["admin"]
	kwargs={}
	for key in theform:
		kwargs[key] = theform[key].value

	print(quickexp_main(user, admin, 'server', **kwargs))


scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
userdir = scriptpath + "users" + os.sep
config = ConfigObj(userdir + 'config.ini')
if "/" in os.environ.get('SCRIPT_NAME', ''):
	mode = "server"
else:
	mode = "local"

if mode == "server":
	quickexp_main_server()