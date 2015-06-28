#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Basic interface to choose a user file to open. Only the logged-in user's file
is opened and file availability depends on an administrator assigning the document
to the user. Other versions of each document's annotation are visible to those users.
Author: Amir Zeldes
"""


import cgitb
import cgi
import os
import _version

from modules.logintools import login
from modules.configobj import ConfigObj
from modules.pathutils import *
from modules.rstweb_sql import *

thisscript = os.environ.get('SCRIPT_NAME', '')
action = None
scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
userdir = scriptpath + "users" + os.sep
theform = cgi.FieldStorage()
action, userconfig = login(theform, userdir, thisscript, action)
user = userconfig["username"]

cgitb.enable()

config = ConfigObj(userdir + 'config.ini')
templatedir = scriptpath + config['controltemplates'].replace("/",os.sep)
template = "main_header.html"
header = readfile(templatedir+template)
header = header.replace("**page_title**","Open a File for Editing")
header = header.replace("**user**",user)

print "Content-Type: text/html\n\n\n"
print header


importdir = config['importdir']


if "current_doc" in theform:
	current_doc = theform["current_doc"].value
	current_project = theform["current_project"].value
else:
	current_doc = ""
	current_project = ""


edit_bar = "edit_bar.html"
edit_bar = readfile(templatedir+edit_bar)
edit_bar = edit_bar.replace("**doc**",current_doc)
edit_bar = edit_bar.replace("**project**",current_project)
edit_bar = edit_bar.replace("**structure_disabled**",'')
edit_bar = edit_bar.replace("**segment_disabled**",'')
edit_bar = edit_bar.replace("**relations_disabled**",'')
edit_bar = edit_bar.replace("**submit_target**",'structure.py')
edit_bar = edit_bar.replace("**action_type**",'')
edit_bar = edit_bar.replace("**open_disabled**",'disabled="disabled"')
edit_bar = edit_bar.replace("**reset_disabled**",'disabled="disabled"')
edit_bar = edit_bar.replace("**save_disabled**",'disabled="disabled"')
edit_bar = edit_bar.replace("**undo_disabled**",'disabled="disabled"')
edit_bar = edit_bar.replace("**redo_disabled**",'disabled="disabled"')
edit_bar = edit_bar.replace('id="nav_open" class="nav_button"','id="nav_open" class="nav_button nav_button_inset"')


if userconfig["admin"] == "0":
	edit_bar = edit_bar.replace("**admin_disabled**",'disabled="disabled"')
else:
	edit_bar = edit_bar.replace("**admin_disabled**",'')

print edit_bar
help = "help.html"
help = readfile(templatedir+help)
help_match = re.search(r'(<div id="help_open".*?</div>)',help,re.MULTILINE|re.DOTALL)
help = help_match.group(1)
print help

about = "about.html"
about = readfile(templatedir+about)
about = about.replace("**version**", _version.__version__)
print about

print "<h2>Current Documents</h2>"
print '<p>List of documents you are authorized to view:</p>'
docs = get_docs_by_project(user)
if not docs:
	print "<p>No documents have been assigned for user name: <b>" + user + "</b></p>"
else:
	print '<select id="doclist" name="doclist" class="doclist" size="15">\n'
	project_group=""
	for doc in docs:
		if project_group!=doc[1]:
			if project_group !="":
				print '</optgroup>\n'
			project_group = doc[1]
			print '<optgroup label="'+doc[1]+'">\n'
		print '\t<option value="'+doc[1]+"/"+doc[0]+'">'+doc[0]+'</option>\n'

	print '</optgroup>\n</select>\b<br/>'
	print '''<button class="nav_button" onclick="do_open(document.getElementById('doclist').value);">Open file</button>'''


print '''
</body>
</html>
'''
