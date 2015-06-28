#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Interface to segment a document into elementary discourse units (EDUs). These are the basis for
the EDU nodes in the structurer script's layout. Dynamic editing of the segments is handled
by script/segment.js, and once saved this script updates the database and renders the saved
segmentation.
Author: Amir Zeldes
"""

import collections
import _version
import cgitb
from modules.rstweb_sql import *
import codecs
import sys
import re
from modules.configobj import ConfigObj
from modules.pathutils import *
import cgi
import os
from modules.logintools import login

thisscript = os.environ.get('SCRIPT_NAME', '')
action = None
scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
userdir = scriptpath + "users" + os.sep
theform = cgi.FieldStorage()
action, userconfig = login(theform, userdir, thisscript, action)
user = userconfig["username"]

UTF8Writer = codecs.getwriter('utf8')
sys.stdout = UTF8Writer(sys.stdout)

cgitb.enable()

###GRAPHICAL PARAMETERS###
top_spacing = 80
layer_spacing = 60


config = ConfigObj(userdir + 'config.ini')
templatedir = scriptpath + config['controltemplates'].replace("/",os.sep)
template = "main_header.html"
header = readfile(templatedir+template)
header = header.replace("**page_title**","Editor")
header = header.replace("**user**",user)
header = header.replace("**open_disabled**",'')


if userconfig["admin"] == "0":
	header = header.replace("**admin_disabled**",'disabled="disabled"')
else:
	header = header.replace("**admin_disabled**",'')


importdir = config['importdir']


print "Content-Type: text/html\n\n\n"
print header


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
edit_bar = edit_bar.replace("**save_disabled**",'')
edit_bar = edit_bar.replace("**reset_disabled**",'')
edit_bar = edit_bar.replace("**segment_disabled**",'disabled="disabled"')
edit_bar = edit_bar.replace("**submit_target**",'segment.py')
edit_bar = edit_bar.replace("**action_type**",'seg_action')
edit_bar = edit_bar.replace("**open_disabled**",'')
edit_bar = edit_bar.replace('id="nav_segment" class="nav_button"','id="nav_segment" class="nav_button nav_button_inset"')

if userconfig["admin"] == "0":
	edit_bar = edit_bar.replace("**admin_disabled**",'disabled="disabled"')
else:
	edit_bar = edit_bar.replace("**admin_disabled**",'')

print edit_bar

help = "help.html"
help = readfile(templatedir+help)
help_match = re.search(r'(<div.*?help_seg.*?</div>)',help,re.MULTILINE|re.DOTALL)
help = help_match.group(1)
print help

about = "about.html"
about = readfile(templatedir+about)
about = about.replace("**version**", _version.__version__)
print about

if current_doc =="":
	print '<p class="warn">No file found - please select a file to open</p>'
	sys.exit()

print '<input id="undo_log" type="hidden" value=""/>'
print '<input id="redo_log" type="hidden" value=""/>'
print '<input id="undo_state" type="hidden" value=""/>'

print '''<div class="canvas">
<div id="inner_canvas">'''


if "reset" in theform or user=="demo":
	if len(theform.getvalue("reset")) > 1 or user=="demo":
		reset_rst_doc(current_doc,current_project,user)

if "seg_action" in theform:
	if len(theform.getvalue("seg_action")) > 1:
		action_log = theform["seg_action"].value
		if len(action_log) > 0:
			actions = action_log.split(";")
			for action in actions:
				action_type = action.split(":")[0]
				action_params = action.split(":")[1]
				if action_type =="ins":
					insert_seg(int(action_params.replace("tok","")),current_doc,current_project,user)
				elif action_type =="del":
					merge_seg_forward(int(action_params.replace("tok","")),current_doc,current_project,user)

segs={}


rows = get_rst_doc(current_doc,current_project,user)

print '\t<script src="script/segment.js"></script>'
print '<h2>Edit segmentation</h2>'
print '\t<div id="control">'
print '\t<p>Document: <b>'+current_doc+'</b> (project: <i>'+current_project+'</i>)</p>'
print '\t<div id="segment_canvas">'

for row in rows:
	if row[5] =="edu":
		segs[int(row[0])] = SEGMENT(row[0],row[6])

seg_counter=0
tok_counter=0

segs = collections.OrderedDict(sorted(segs.items()))
first_seg = True
for seg_id in segs:
	first_tok = True
	seg = segs[seg_id]
	seg_counter+=1
	if first_seg:
		first_seg = False
	else:
		print '<div class="tok_space" id="tok'+str(tok_counter)+'" style="display:none" onclick="act('+"'ins:"+'tok'+str(tok_counter)+"'"+')">&nbsp;</div>'
		print '\t\t\t<div id="segend_post_tok'+str(tok_counter)+'" class="seg_end" onclick="act('+"'del:"+'tok'+str(tok_counter)+"'"+')">||</div>'
		print '\t\t</div>'
	print '\t\t<div id="seg'+ str(seg_counter) +'" class="seg">'
	for token in seg.tokens:
		tok_counter+=1
		if first_tok:
			first_tok = False
		else:
			print '<div class="tok_space" id="tok'+str(tok_counter-1)+'" onclick="act('+"'ins:"+'tok'+str(tok_counter-1)+"'"+')">&nbsp;</div>'
		print '\t\t\t<div class="token" id="string_tok'+str(tok_counter)+'">' + token + '</div>'
print '\t\t</div>'
print '''\t</div></div>
</body>
</html>

'''