#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Administration functions and interface to create and delete users, import and export documents,
assign documents to users and set up projects
Author: Amir Zeldes
"""

import cgitb
import cgi
import errno
from os.path import isfile, join
from os import listdir
import _version
from modules.logintools import login, createuser
from modules.rstweb_sql import *
from modules.configobj import ConfigObj
from modules.pathutils import *

thisscript = os.environ.get('SCRIPT_NAME', '')
action = None
scriptpath = os.path.dirname(os.path.realpath(__file__)) + os.sep
userdir = scriptpath + "users" + os.sep
theform = cgi.FieldStorage()
action, userconfig = login(theform, userdir, thisscript, action)
user = userconfig["username"]
config = ConfigObj(userdir + 'config.ini')
exportdir = scriptpath + config['exportdir'].replace("/",os.sep)

cgitb.enable()

import re
def is_email(email):
    pattern = '[\.\w]{1,}[@]\w+[.]\w+'
    if re.match(pattern, email):
        return True
    else:
        return False

config = ConfigObj(userdir + 'config.ini')
templatedir = scriptpath + config['controltemplates'].replace("/",os.sep)
template = "main_header.html"
header = readfile(templatedir+template)
header = header.replace("**page_title**","Administration")
header = header.replace("**user**",user)

importdir = scriptpath + config['importdir'].replace("/",os.sep)
def_relfile = scriptpath + config['default_rels'].replace("/",os.sep)


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
edit_bar = edit_bar.replace("**segment_disabled**",'')
edit_bar = edit_bar.replace("**relations_disabled**",'')
edit_bar = edit_bar.replace("**submit_target**",'admin.py')
edit_bar = edit_bar.replace("**action_type**",'')
edit_bar = edit_bar.replace("**open_disabled**",'')
edit_bar = edit_bar.replace("**reset_disabled**",'disabled="disabled"')
edit_bar = edit_bar.replace("**save_disabled**",'disabled="disabled"')
edit_bar = edit_bar.replace("**undo_disabled**",'disabled="disabled"')
edit_bar = edit_bar.replace("**redo_disabled**",'disabled="disabled"')
edit_bar = edit_bar.replace("**admin_disabled**",'disabled="disabled"')
edit_bar = edit_bar.replace('id="nav_admin" class="nav_button"','id="nav_admin" class="nav_button nav_button_inset"')


if userconfig["admin"] == "0":
	print '<p class="warn">User '+ user+' does not have administrator rights!</p></body></html>'
	sys.exit()
else:
	edit_bar = edit_bar.replace("**admin_disabled**",'')

print edit_bar

help = "help.html"
help = readfile(templatedir+help)
help_match = re.search(r'(<div id="help_admin".*?</div>)',help,re.MULTILINE|re.DOTALL)
help = help_match.group(1)
print help

about = "about.html"
about = readfile(templatedir+about)
about = about.replace("**version**", _version.__version__)
print about

if "wipe" in theform:
	if theform.getvalue("wipe") =="wipe":
		setup_db()

if "create_project" in theform:
	new_project = theform.getvalue("create_project")
	if len(new_project)>0:
		create_project(new_project)

project_list = get_all_projects()

if "doclist" in theform:
	current_doc = theform["doclist"].value
else:
	current_doc = ""

print '''
<div id="control">
<form id="admin_form" name="id_form" action="admin.py" method="post" enctype="multipart/form-data">
	<input type="hidden" name="create_project" id="create_project" value=""/>
	<input type="hidden" name="sel_tab" id="sel_tab" value="project"/>
	<input type="hidden" name="delete" id="delete" value=""/>
	<input type="hidden" name="delete_user" id="delete_user" value=""/>
	<input type="hidden" name="export" id="export" value=""/>
	<input type="hidden" name="wipe" id="wipe" value=""/>
	<input type="hidden" name="imp_project" id="imp_project" value=""/>
	<input type="hidden" name="import_file_type" id="import_file_type" value=""/>
	<input type="hidden" name="doclist" id="doclist" value="'''
print current_doc
print '''"/>
	<input type="hidden" name="userlist" id="userlist" value=""/>
	<input type="hidden" name="assign_doc" id="assign_doc" value=""/>
	<input type="hidden" name="assign_user" id="assign_user" value=""/>
	<input type="hidden" name="unassign_doc" id="unassign_doc" value=""/>
	<input type="hidden" name="unassign_user" id="unassign_user" value=""/>
	<input type="hidden" name="new_user_data" id="new_user_data" value=""/>
	<input type="hidden" name="del_project" id="del_project" value=""/>
	<input id="file" type="file" name="file"/>
</form>
<script src="./script/admin.js"></script>
<script src="./script/jquery-1.11.3.min.js"></script>
<script src="./script/jquery-ui.min.js"></script>
'''


print '''
<div class="tab_btn" id="project_btn" onclick="open_tab('project');">Projects</div><div id="project" class="tab">
<h2>Manage Projects</h2>
<p>Create a new project named: <input id="new_project"/></p>
<button onclick="admin('create_project')">Create Project</button>
'''
#print theform

if "del_project" in theform:
	projects_to_delete = theform.getvalue("del_project").split(";")
	if len(projects_to_delete)>0:
		if isinstance(projects_to_delete,list):
			for project in projects_to_delete:
				delete_project(project)
		else:
			delete_project(projects_to_delete)

all_project_list = get_all_projects()
print '<p>Existing projects:</p>'
if all_project_list:
	print '<select class="doclist" id="del_project_select" size="5" multiple="multiple">\n'
	for project in all_project_list:
		print '\t<option value="' + project[0] +'">' +  project[0] + "</option>"
	print '</select>\n'
else:
	print '<p class="warn">No projects found!</p>'

print '''<p>
	<button onclick="admin('delete_project')">Delete Selected</button></p>
</div>'''




print '''
<div class="tab_btn" id="import_btn" onclick="open_tab('import');">Import</div><div id="import" class="tab">
<h2>Import a Document</h2>
<p>1. Upload .rs3 or plain text file: </p>
<p>2. Choose file type: <select id="import_file_type_select" class="doclist"><option value="rs3">rs3</option><option value="plain">plain text (EDU per line)</option></select> </p>
<p>3. Import document into this project:
'''


if project_list:
	print '<select class="doclist" id="imp_project_select">\n'
	for project in project_list:
		print '\t<option value="' + project[0] +'">' +  project[0] + "</option>"
	print '</select>\n'
else:
	print "<p>No projects found with permissons for user: "+ user + "</p>"
print '''
</p>
<p><button onclick="admin('upload')">Upload</button></p>

'''

fail = 0
if "file" in theform and "imp_project" in theform:
	fileitem = theform['file']
	imp_project = theform.getvalue("imp_project")
	if fileitem.filename and len(imp_project) > 0: # Test if the file was uploaded and a project selection exists
		#  strip leading path from file name to avoid directory traversal attacks
		fn = os.path.basename(fileitem.filename)
		open(importdir + fn, 'wb').write(fileitem.file.read())
		message = 'The file "' + fn + '" was uploaded successfully'
		if theform['import_file_type'].value == "rs3":
			fail = import_document(importdir + fn,imp_project,user)
		elif theform['import_file_type'].value == "plain":
			if len(def_relfile) > 0:
				rel_hash = read_relfile(def_relfile)
			else:
				rel_hash = {}
			fail = import_plaintext(importdir + fn,imp_project,user,rel_hash)
	else:
		message = 'No file was uploaded'

	if isinstance(fail,basestring):
		message = fail
	print """
	<p class="warn">%s</p>
	""" % (message,)

print '</div><div class="tab_btn" id="docs_btn" onclick="open_tab('+"'"+"docs"+"'"+');">Documents</div><div id="docs" class="tab">'
print "<h2>Current Documents</h2>"

if "delete" in theform: #execute delete documents before retrieving doclist
	doclist = theform.getvalue("doclist")
	if len(doclist) > 0 and theform.getvalue("delete") =="delete":
		docs_to_delete = doclist.split(";")

		if len(docs_to_delete) > 0:
			if isinstance(docs_to_delete,list):
				for doc in docs_to_delete:
					delete_document(doc.split("/")[1],doc.split("/")[0])
			else:
				delete_document(docs_to_delete.split("/")[1],docs_to_delete.split("/")[0])
			print '<p class="warn">Deletion complete</p>'


print '<p>List of documents in the database:</p>'
docs = get_all_docs_by_project()
if not docs:
	print "<p>No documents found with permissions for user name: " + user + "</p>"
else:
	print '<select name="doclist_select" id="doclist_select" class="doclist" size="15" multiple="multiple">\n'
	project_group=""
	for doc in docs:
		if project_group!=doc[1]:
			if project_group !="":
				print '</optgroup>\n'
			project_group = doc[1]
			print '<optgroup label="'+doc[1]+'">\n'
		print '\t<option value="'+doc[1]+"/"+doc[0]+'">'+doc[0]+'</option>\n'

	print '</optgroup>\n</select>\n'

print '''
<p>Export selected document(s) to export folder as .rs3 file(s):</p>
<button onclick="admin('export');">Export</button>
<p>Delete selected document(s):</p>
<button onclick="admin('delete_doc');">Delete</button>
'''
if "export" in theform:
	export_doc_list = theform.getvalue("doclist")
	if len(export_doc_list) > 0 and theform.getvalue("export")== "export":
		export_docs = export_doc_list.split(";")
		if isinstance(export_docs,list):
			for doc in export_docs:
				export_document(doc.split("/")[1],doc.split("/")[0],exportdir)
		else:
			export_document(export_docs.split("/")[1],export_docs.split("/")[0],exportdir)
		print '<p class="warn">Export complete</p>'


# Handle user add and delete before showing user list
if "delete_user" in theform:
	if len(theform.getvalue("delete_user")) > 0:
		users_to_delete = theform.getvalue("userlist")
		users = users_to_delete.split(";")
		if isinstance(users,list):
			for user in users:
				try:
					os.remove(userdir+user)
					delete_docs_for_user(user)
					user_del_message = '<p class="warn">Deleted users from selection</p>'
				except OSError as e:
					if e.errno == errno.ENOENT:
						user_del_message = '<p class="warn">File to delete <i>'+user+'</i> not found!</p>'
					else:
						raise
		else:
			try:
				os.remove(userdir+users_to_delete)
				delete_docs_for_user(users_to_delete)
				user_del_message = 'Deleted users from selection'
			except OSError as e:
				if e.errno == errno.ENOENT:
					user_del_message = '<p class="warn">File to delete <i>'+ users_to_delete + '</i> not found!</p>'
				else:
					raise


# Handle user document assignment
if "assign_user" in theform:
	if len(theform.getvalue("assign_user")) > 0:
		users_to_assign = theform.getvalue("assign_user")
		docs_to_assign = theform.getvalue("assign_doc")
		users = users_to_assign.split(";") if ";" in users_to_assign else [users_to_assign]
		docs = docs_to_assign.split(";") if ";" in docs_to_assign else [docs_to_assign]
		for user in users:
			for doc in docs:
				user = user.replace(".ini","")
				copy_doc_to_user(doc.split("/")[1],doc.split("/")[0],user)

if "unassign_user" in theform:
	if len(theform.getvalue("unassign_user")) > 0:
		user_to_unassign = theform.getvalue("unassign_user")
		doc_to_unassign = theform.getvalue("unassign_doc")
		delete_doc_user_version(doc_to_unassign.split("/")[1],doc_to_unassign.split("/")[0],user_to_unassign)

if "new_user_data" in theform:
	if len(theform.getvalue("new_user_data")) >0:
		user_data = theform.getvalue("new_user_data").split("/")
		username = user_data[0]
		realname = user_data[1]
		email = user_data[2]
		RESERVEDNAMES = {'config':1, 'default':1, 'temp':1, 'emails':1, 'pending':1, '_orig':1}
		if username in RESERVEDNAMES:
			user_create_message = '<p class="warn">User name cannot be: "config", "default", "temp", "emails", or "pending"</p>'
		else:
			if len(realname)<1:
				user_create_message = '<p class="warn">The real name cannot be empty!</p>'
			else:
				if not is_email(email):
					user_create_message = '<p class="warn">Invalid e-mail address: <b>'+email+'</b></p>'
				else:
					password = user_data[3]
					if len(password)<5:
						user_create_message = '<p class="warn">Password must be at least 5 characters long</p>'
					else:
						administrator = user_data[4]
						if str(administrator) != "3" and str(administrator) != "0":
							user_create_message = '<p class="warn">Invalid administrator setting value for new user</p>'
						else:
							createuser(userdir, realname, username, email, password, administrator)
							user_create_message = '<p class="warn">Created the user ' + username + '</p>'

print '</div><div class="tab_btn" id="users_btn" onclick="open_tab('+"'"+"users"+"'"+');">Users</div><div id="users" class="tab">'
print '''<h2>User Management</h2>
<table id="doc_assign"><tr><td><p>Users:</p>
<select id="userlist_select" multiple="multiple" size="10" class="doclist">
'''

userfiles = [ f for f in listdir(userdir) if isfile(join(userdir,f)) ]
for userfile in sorted(userfiles):
	if userfile != "config.ini" and userfile != "default.ini" and userfile != "admin.ini" and userfile.endswith(".ini"):
		userfile = userfile.replace(".ini","")
		print '<option value="' + userfile + '.ini">'+userfile+'</option>'
print'''
</select></td><td>
<p>Documents to assign to:</p>'''
docs = get_all_docs_by_project()
if not docs:
	print "<p class='warn'>No documents found with permissions for user name: " + user + "</p>"
else:
	print '<select name="doc_assign_select" id="doc_assign_select" class="doclist" size="10" multiple="multiple">\n'
	project_group=""
	for doc in docs:
		if project_group!=doc[1]:
			if project_group !="":
				print '</optgroup>\n'
			project_group = doc[1]
			print '<optgroup label="'+doc[1]+'">\n'
		print '\t<option value="'+doc[1]+"/"+doc[0]+'">'+doc[0]+'</option>\n'

	print '</optgroup>\n</select>\n'
print '''
</td></tr></table>
<p>Delete selected user files: (annotations will not be deleted)</p>
<button onclick="admin('delete_user')">Delete user(s)</button>
'''
if "delete_user" in theform:
	if len(theform.getvalue("delete_user")) > 0:
		print user_del_message
print '''
<p>Assign selected users to selected documents:</p>
<button onclick="admin('assign_user')">Assign</button>
<p>Delete assignments for user: (annotations will be deleted)</p>
'''

assigned_users = get_assigned_users()
if len(assigned_users)>0:
	print '<select id="assigned_user_sel" name="assigned_user_sel" class="doclist" onchange="update_assignments()">'
	first_user = assigned_users[0][0]
	for user in assigned_users:
		assigned_docs = get_assignments(user[0])
		print '<option value="',# + user[0] +":"
		for doc in assigned_docs:
			print doc[1]+"/"+doc[0]+";",
		print '">'+user[0]+'</option>'
	print '</select>'
	assigned_docs = get_assignments(first_user)
	#print assigned_docs
	print '<select id="assigned_doc_sel" name="assigned_doc_sel" class="doclist">'
	for doc in assigned_docs:
		print '<option value="' + doc[1]+"/"+doc[0] + '">'+doc[1]+"/"+doc[0]+'</option>'
	print '</select>'
	print '''<p><button onclick="admin('unassign_user')">Delete assignment</button></p>'''
else:
	print '<p class="warn">No user assignments found</p>'



print '''<p>Create new user:</p>
<table class="gray_tab">
    <tr><td>User name:</td><td><input name="username" id="username"  type="text" value=""></td></tr>
    <tr><td>Real name:</td><td><input name="realname" id="realname" type="text" value=""></td></tr>
    <tr><td>Email address:</td><td><input name="email" id="email" type="text" value=""></td></tr>
    <tr><td>Password:</td><td><input name="pass" id="pass" type="password">
    <tr><td>Administrator:</td><td><input type="checkbox" id="chk_admin" name="chk_admin">&nbsp;&nbsp;&nbsp;&nbsp;<button onclick="admin('create_user')">Create user</button></td></tr>
    </td></tr>
</table>

'''

if "new_user_data" in theform:
	if len(theform.getvalue("new_user_data")) > 0:
		print user_create_message


print '</div><div class="tab_btn" id="database_btn" onclick="open_tab('+"'"+"database"+"'"+');">Database</div><div id="database" class="tab">'
print '''<h2>Initialize the Database</h2>
<p>Wipe and restore database structure.</p>
<p class="warn">Warning:</p> <p>this will delete all imported documents and all edits from the database.</p>
<button onclick="admin('wipe')">Init DB</button>
'''

if "wipe" in theform:
	if theform.getvalue("wipe") =="wipe":
		print '<p class="warn">Database has been re-initialized</p>'


print '''
</div>
<script>

	open_tab(document.getElementById("sel_tab").value);



</script>'''

if "sel_tab" in theform:
	sel_tab = theform['sel_tab'].value
	print '<script>open_tab("'+sel_tab+'")</script>'

print '''
</div>
</body>
</html>
'''


