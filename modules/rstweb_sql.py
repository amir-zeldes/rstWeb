#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Data access functions to read from and write to the SQLite backend.
Author: Amir Zeldes
"""


import sqlite3
from modules.rstweb_reader import *
import codecs
import os
import re
import json
import sys

try:
	basestring
except NameError:
	basestring = str


def setup_db():
	dbpath = os.path.dirname(os.path.realpath(__file__)) + os.sep +".."+os.sep+"rstweb.db"

	conn = sqlite3.connect(dbpath)

	cur = conn.cursor()

	# Drop tables if they exist
	cur.execute("DROP TABLE IF EXISTS rst_nodes")
	cur.execute("DROP TABLE IF EXISTS rst_signals")
	cur.execute("DROP TABLE IF EXISTS rst_signal_types")
	cur.execute("DROP TABLE IF EXISTS rst_relations")
	cur.execute("DROP TABLE IF EXISTS docs")
	cur.execute("DROP TABLE IF EXISTS perms")
	cur.execute("DROP TABLE IF EXISTS users")
	cur.execute("DROP TABLE IF EXISTS projects")
	cur.execute("DROP TABLE IF EXISTS logging")
	cur.execute("DROP TABLE IF EXISTS settings")
	conn.commit()

	# Create tables
	cur.execute('''CREATE TABLE IF NOT EXISTS rst_nodes
	             (id text, left real, right real, parent text, depth real, kind text, contents text, relname text, doc text, project text, user text, UNIQUE (id, doc, project, user) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS rst_signals
	             (source text, type text, subtype text, tokens text, doc text, project text, user text, UNIQUE (source, type, subtype, tokens, doc, project, user) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS rst_signal_types
	             (majtype text, subtype text, doc text, project text, UNIQUE (majtype, subtype, doc, project) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS rst_relations
	             (relname text, reltype text, doc text, project text, UNIQUE (relname, reltype, doc, project) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS docs
	             (doc text, project text, user text,  UNIQUE (doc, project, user) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS users
	             (user text, timestamp text, UNIQUE (user) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS projects
	             (project text, guideline_url text, validations text, UNIQUE (project) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS logging
	             (doc text, project text, user text, actions text, mode text, timestamp text)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS settings
	             (setting text, svalue text, UNIQUE (setting) ON CONFLICT REPLACE)''')

	conn.commit()
	conn.close()

	initialize_settings()


def update_schema():
	dbpath = os.path.dirname(os.path.realpath(__file__)) + os.sep +".."+os.sep+"rstweb.db"
	conn = sqlite3.connect(dbpath)
	cur = conn.cursor()

	# Create tables
	cur.execute('''CREATE TABLE IF NOT EXISTS rst_nodes
	             (id text, left real, right real, parent text, depth real, kind text, contents text, relname text, doc text, project text, user text, UNIQUE (id, doc, project, user) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS rst_relations
	             (relname text, reltype text, doc text, project text, UNIQUE (relname, reltype, doc, project) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS rst_signals
	             (source text, type text, subtype text, tokens text, doc text, project text, user text, UNIQUE (source, type, subtype, tokens, doc, project, user) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS rst_signal_types
	             (majtype text, subtype text, doc text, project text, UNIQUE (majtype, subtype, doc, project) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS docs
	             (doc text, project text, user text,  UNIQUE (doc, project, user) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS users
	             (user text, timestamp text, UNIQUE (user) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS projects
	             (project text, guideline_url text, UNIQUE (project) ON CONFLICT REPLACE)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS logging
	             (doc text, project text, user text, actions text, mode text, timestamp text)''')
	cur.execute('''CREATE TABLE IF NOT EXISTS settings
	             (setting text, svalue text, UNIQUE (setting) ON CONFLICT REPLACE)''')


	schema = get_schema()
	if schema < 2:  # versions below 2 do not have guideline_url
		if not generic_query("SELECT * from pragma_table_info('projects') where name='guideline_url';", ()):
			cur.execute('ALTER TABLE projects ADD COLUMN guideline_url text')
	if schema < 4:  # versions below 4 do not have last save timestamp to prevent resubmit on browser refresh
		if not generic_query("SELECT * from pragma_table_info('users') where name='timestamp';", ()):
			cur.execute('ALTER TABLE users ADD COLUMN timestamp text')
	if schema < 5:  # versions below 5 do not validations
		if not generic_query("SELECT * from pragma_table_info('projects') where name='validations';", ()):
			cur.execute('ALTER TABLE projects ADD COLUMN validations text')
	if schema < 6:
		initialize_signal_types_on_existing_docs(cur)

	conn.commit()
	conn.close()


	initialize_settings()


def initialize_signal_types_on_existing_docs(cur):
	types = read_signals_file()
	for doc, project in get_all_docs_by_project():
		for majtype in types:
			for subtype in types[majtype]:
				cur.execute("INSERT INTO rst_signal_types VALUES(?,?,?,?)", (majtype, subtype, doc, project))


def get_schema():
	dbpath = os.path.dirname(os.path.realpath(__file__)) + os.sep +".."+os.sep+"rstweb.db"
	conn = sqlite3.connect(dbpath)
	with conn:
		cur = conn.cursor()
		cur.execute('PRAGMA user_version')
		return cur.fetchall()[0][0]


def set_schema(version):
	dbpath = os.path.dirname(os.path.realpath(__file__)) + os.sep +".."+os.sep+"rstweb.db"
	conn = sqlite3.connect(dbpath)
	with conn:
		cur = conn.cursor()
		pragma_stmt = 'PRAGMA user_version=' +str(version)
		cur.execute(pragma_stmt)


def initialize_settings():
	# Initialize settings to default values
	save_setting("logging", "off")
	save_setting("signals", "False")
	save_setting("signals_file", "default.json")
	save_setting("use_span_buttons", "True")
	save_setting("use_multinuc_buttons", "True")
	set_schema('6')


def check_refresh(user, timestamp):

	schema = get_schema()
	if schema < 4:
		return False

	if timestamp == "":
		return False
	else:
		last_stamp = generic_query("select timestamp from users where user=?",(user,))
		if len(last_stamp) < 1:
			return False
		else:
			last_stamp = last_stamp[0][0]
			if last_stamp == "":
				return False
			else:
				if last_stamp == timestamp:
					return True
	return False


def set_timestamp(user, timestamp):
	schema = get_schema()
	if schema >= 4:
		if timestamp != "" and user != "":
			# Remove potentially non UTF-8 trailing timezone specifications in brackets
			timestamp = re.sub(r'\([^)]+\)','', timestamp)
			timestamp = timestamp.strip()
			generic_query("INSERT or REPLACE INTO users ('user','timestamp') VALUES (?,?)",(user,timestamp))


def get_project_validations(project):
	schema = get_schema()
	if schema < 5:
		update_schema()
	if len(project):
		validation_row = generic_query("SELECT validations FROM projects WHERE project = ?",(project,))
	else:
		return ""
	if len(validation_row) == 0:
		validations = ""
	else:
		validations = validation_row[0][0]
	if validations is None:
		validations = ""
	return validations


def set_project_validations(project,validations):
	generic_query("UPDATE projects SET validations=? WHERE project=?;",(validations,project))


def read_signals_file():
	fname = get_setting('signals_file') or 'default.json'
	path = 'signals' + os.sep + fname
	try:
		with open(path, 'r') as f:
			return json.load(f)
	except IOError:
		return {}

def import_document(filename, project, user, do_tokenize=False):
	dbpath = os.path.dirname(os.path.realpath(__file__)) + os.sep +".."+os.sep+"rstweb.db"
	conn = sqlite3.connect(dbpath)

	cur = conn.cursor()

	doc=os.path.basename(filename)

	rel_hash = {}

	schema = get_schema()
	if schema < 6:  # Schemas below 6 do not support importing signals
		update_schema()

	rst_nodes, rst_signals = read_rst(filename, rel_hash, do_tokenize=do_tokenize)
	if isinstance(rst_nodes,basestring):
		return rst_nodes

	# First delete any old copies of this document, if they are already imported
	delete_document(doc,project)

	for key in rst_nodes:
		node = rst_nodes[key]
		cur.execute("INSERT INTO rst_nodes VALUES(?,?,?,?,?,?,?,?,?,?,?)", (node.id,node.left,node.right,node.parent,node.depth,node.kind,node.text,node.relname,doc,project,user)) #user's instance
		cur.execute("INSERT INTO rst_nodes VALUES(?,?,?,?,?,?,?,?,?,?,?)", (node.id,node.left,node.right,node.parent,node.depth,node.kind,node.text,node.relname,doc,project,"_orig")) #backup instance

	for signal in rst_signals:
		cur.execute("INSERT INTO rst_signals VALUES(?,?,?,?,?,?,?)", (signal[0],signal[1],signal[2],signal[3],doc,project,user)) #user's instance
		cur.execute("INSERT INTO rst_signals VALUES(?,?,?,?,?,?,?)", (signal[0],signal[1],signal[2],signal[3],doc,project,"_orig")) #backup instance

	signal_types = read_signals_file()
	for majtype, subtypes in signal_types.items():
		for subtype in subtypes:
			cur.execute("INSERT INTO rst_signal_types VALUES(?,?,?,?)",
			(majtype, subtype, doc, project))

	for key in rel_hash:
		rel_name = key
		rel_type = rel_hash[key]
		cur.execute("INSERT INTO rst_relations VALUES(?,?,?,?)", (rel_name, rel_type, doc, project))

	cur.execute("INSERT INTO docs VALUES (?,?,?)", (doc,project,user))
	cur.execute("INSERT INTO docs VALUES (?,?,'_orig')", (doc,project))

	conn.commit()
	conn.close()


def import_plaintext(filename, project, user, rel_hash, do_tokenize=False):

	dbpath = os.path.dirname(os.path.realpath(__file__)) + os.sep +".."+os.sep+"rstweb.db"
	conn = sqlite3.connect(dbpath)

	cur = conn.cursor()

	doc=os.path.basename(filename)

	rst_nodes = read_text(filename, rel_hash, do_tokenize=do_tokenize)

	for key in rst_nodes:
		node = rst_nodes[key]
		generic_query("INSERT INTO rst_nodes VALUES(?,?,?,?,?,?,?,?,?,?,?)", (node.id,node.left,node.right,node.parent,node.depth,node.kind,node.text,node.relname,doc,project,user)) #user's instance
		generic_query("INSERT INTO rst_nodes VALUES(?,?,?,?,?,?,?,?,?,?,?)", (node.id,node.left,node.right,node.parent,node.depth,node.kind,node.text,node.relname,doc,project,"_orig")) #backup instance

	for key in rel_hash:
		rel_name = key
		rel_type = rel_hash[key]
		generic_query("INSERT INTO rst_relations VALUES(?,?,?,?)", (rel_name, rel_type, doc, project))

	signal_types = read_signals_file()
	for majtype, subtypes in signal_types.items():
		for subtype in subtypes:
			cur.execute("INSERT INTO rst_signal_types VALUES(?,?,?,?)",
			(majtype, subtype, doc, project))

	conn.commit()
	conn.close()

	generic_query("INSERT INTO docs VALUES (?,?,?)", (doc,project,user))


def get_rst_doc(doc,project,user):
	dbpath = os.path.dirname(os.path.realpath(__file__)) + os.sep +".."+os.sep+"rstweb.db"
	conn = sqlite3.connect(dbpath)

	with conn:
		cur = conn.cursor()
		cur.execute("SELECT id, left, right, parent, depth, kind, contents, relname, doc, project, user FROM rst_nodes WHERE doc=? and project=? and user=? ORDER BY CAST(id AS int)", (doc,project,user))

		rows = cur.fetchall()
		return rows


def get_def_rel(relkind, doc, project):
	rel_row = generic_query("SELECT relname FROM rst_relations WHERE reltype = ? and doc=? and project=? ORDER BY relname",(relkind,doc,project))
	if len(rel_row) == 0:
		if relkind == "rst":
			return "--_r"
		else:
			return "--_m"
	else:
		return rel_row[0][0]


def get_rst_rels(doc,project):
	dbpath = os.path.dirname(os.path.realpath(__file__)) + os.sep +".."+os.sep+"rstweb.db"
	conn = sqlite3.connect(dbpath)

	with conn:
		cur = conn.cursor()
		cur.execute("SELECT relname, reltype FROM rst_relations WHERE doc=? and project=? ORDER BY relname", (doc,project))

		rows = cur.fetchall()
		return rows


def get_docs_by_project(user):
	return generic_query("SELECT doc, project, user FROM docs WHERE user=? ORDER BY project, doc COLLATE NOCASE",(user,))


def get_all_docs_by_project():
	return generic_query("SELECT DISTINCT doc, project FROM docs ORDER BY project, doc COLLATE NOCASE",())


def add_node(node_id,left,right,parent,rel_name,text,node_kind,doc,project,user):
	generic_query("INSERT INTO rst_nodes VALUES(?,?,?,?,?,?,?,?,?,?,?)", (node_id,left,right,parent,0,node_kind,text,rel_name,doc,project,user))


def get_all_projects():
	return generic_query("SELECT DISTINCT project FROM projects ORDER BY project",())


def create_project(project_name):
	generic_query("INSERT OR IGNORE INTO projects (project) VALUES (?)",(project_name,))


def update_parent(node_id,new_parent_id,doc,project,user):
	prev_parent = get_parent(node_id,doc,project,user)
	generic_query("UPDATE rst_nodes SET parent=? WHERE id=? and doc=? and project=? and user=?",(new_parent_id,node_id,doc,project,user))
	if new_parent_id == "0":
		update_rel(node_id,get_def_rel("rst",doc,project),doc,project,user)
	if new_parent_id != "0":
		if get_kind(new_parent_id,doc,project,user) =="multinuc":
			multi_rel = get_multirel(new_parent_id,node_id,doc,project,user)
			update_rel(node_id, multi_rel,doc,project,user)
		elif get_rel(node_id,doc,project,user)=="span" and get_kind(new_parent_id,doc,project,user) !="span": # A span child was just attached to a non-span
			update_rel(node_id, get_def_rel("rst",doc,project),doc,project,user)
	if prev_parent:
		if not count_children(prev_parent,doc,project,user)>0 and not prev_parent =="0": # Parent has no more children, delete it
			delete_node(prev_parent,doc,project,user)
		elif get_kind(prev_parent,doc,project,user)=="span" and count_span_children(prev_parent,doc,project,user)==0: # Span just lost its last span child, delete it
			delete_node(prev_parent,doc,project,user)
		elif get_kind(prev_parent,doc,project,user)=="multinuc" and count_multinuc_children(prev_parent,doc,project,user)==0: # Multinuc just lost its last multinuc child, delete it
			delete_node(prev_parent,doc,project,user)


def get_multirel(node_id,exclude_child,doc,project,user):
	"""
	Returns the multinuclear relation with which a multinuc is currently dominating its children
	"""

	rel_row = generic_query("SELECT rst_nodes.relname FROM rst_nodes JOIN rst_relations ON rst_nodes.relname = rst_relations.relname and rst_nodes.doc = rst_relations.doc and rst_nodes.project = rst_relations.project WHERE rst_relations.reltype = 'multinuc' and rst_nodes.parent=? and not rst_nodes.id=? and rst_nodes.doc=? and rst_nodes.project=? and rst_nodes.user=?",(node_id,exclude_child,doc,project,user))
	if len(rel_row) > 0:
		return rel_row[0][0]
	else:
		return get_def_rel("multinuc",doc,project)


def get_parent(node_id,doc,project,user):
	parent_row = generic_query("SELECT parent FROM rst_nodes WHERE id=? and doc=? and project=? and user=?",(node_id,doc,project,user))
	return parent_row[0][0]


def get_rel(node_id,doc,project,user):
	rel_row = generic_query("SELECT relname FROM rst_nodes WHERE id=? and doc=? and project=? and user=?",(node_id,doc,project,user))
	return rel_row[0][0]


def get_kind(node_id,doc,project,user):
	if node_id == "0":
		return "none"
	else:
		rel_row = generic_query("SELECT kind FROM rst_nodes WHERE id=? and doc=? and project=? and user=?",(node_id,doc,project,user))
		return rel_row[0][0]


def update_rel(node_id,new_rel,doc,project,user):
	parent_id = get_parent(node_id,doc,project,user)
	if get_kind(parent_id,doc,project,user)=="multinuc":
		new_rel_type = get_rel_type(new_rel,doc,project)
		if new_rel_type == "rst":
			# Check if the last multinuc child of a multinuc just changed to rst
			if count_multinuc_children(parent_id,doc,project,user) == 1 and get_rel_type(get_rel(node_id,doc,project,user),doc,project) == "multinuc":
				new_rel = get_def_rel("rst",doc,project)
				children = get_children(parent_id,doc,project,user)
				for child in children:
					update_parent(child[0],"0",doc,project,user)
			generic_query("UPDATE rst_nodes SET relname=? WHERE id=? and doc=? and project=? and user=?",(new_rel,node_id,doc,project,user))
		else: # New multinuc relation for a multinuc child, change all children to this relation
			generic_query("UPDATE rst_nodes SET relname=? WHERE id=? and doc=? and project=? and user=?",(new_rel,node_id,doc,project,user))
			children = get_children(parent_id,doc,project,user)
			for child in children:
				if get_rel_type(get_rel(child[0],doc,project,user),doc,project) == "multinuc":
					generic_query("UPDATE rst_nodes SET relname=? WHERE id=? and doc=? and project=? and user=?",(new_rel,child[0],doc,project,user))
	else:
		generic_query("UPDATE rst_nodes SET relname=? WHERE id=? and doc=? and project=? and user=?",(new_rel,node_id,doc,project,user))


def count_children(node_id,doc,project,user):
	count = generic_query("SELECT count(*) FROM rst_nodes WHERE parent=? and doc=? and project=? and user=?",(node_id,doc,project,user))
	return int(count[0][0])


def count_multinuc_children(node_id,doc,project,user):
	count = generic_query("SELECT count(rst_nodes.id) FROM rst_nodes JOIN rst_relations ON rst_nodes.relname = rst_relations.relname and rst_nodes.doc = rst_relations.doc and rst_nodes.project = rst_relations.project WHERE reltype = 'multinuc' and parent=? and rst_nodes.doc=? and rst_nodes.project=? and user=?",(node_id,doc,project,user))
	return int(count[0][0])


def get_multinuc_nodes_data(cur,doc,project,user):
	nodes_data = cur.execute("SELECT id, parent, left, right FROM rst_nodes JOIN rst_relations ON rst_nodes.relname = rst_relations.relname and rst_nodes.doc = rst_relations.doc and rst_nodes.project = rst_relations.project WHERE reltype = 'multinuc' and rst_nodes.doc=? and rst_nodes.project=? and user=?",(doc,project,user)).fetchall()
	return nodes_data


def count_span_children(node_id,doc,project,user):
	count = generic_query("SELECT count(id) FROM rst_nodes WHERE relname = 'span' and parent=? and rst_nodes.doc=? and rst_nodes.project=? and user=?",(node_id,doc,project,user))
	return int(count[0][0])


def node_exists(node_id,doc,project,user):
	count = generic_query("SELECT count(*) FROM rst_nodes WHERE id=? and doc=? and project=? and user=?",(node_id,doc,project,user))
	return int(count[0][0])>0


def get_rel_type(relname,doc,project):
	if relname=="span" or relname=="":
		return "span"
	else:
		return generic_query("SELECT reltype from rst_relations WHERE relname=? and doc=? and project=?",(relname,doc,project))[0][0]

def get_doc_relname_to_reltype(cur,doc,project):
	rels = cur.execute("SELECT relname, reltype from rst_relations WHERE doc=? and project=?",(doc,project)).fetchall()
	res = {
		"span": "span",
		"": "span"
	}
	for rel in rels:
		res[rel[0]] = rel[1]
	return res


def delete_node(node_id,doc,project,user):
	if node_exists(node_id,doc,project,user):
		parent = get_parent(node_id,doc,project,user)
		if not get_kind(node_id,doc,project,user) == "edu": # If it's not an EDU, it may be deleted
			# If there are still any children, such as rst relations to a deleted span or multinuc, set their parent to 0
			old_children = get_children(node_id,doc,project,user)
			for child in old_children:
				if len(child[0])>0:
					update_parent(child[0],"0",doc,project,user)
			generic_query("DELETE FROM rst_nodes WHERE id=? and doc=? and project=? and user=?",(node_id,doc,project,user))
			generic_query("DELETE FROM rst_signals WHERE source=? and doc=? and project=? and user=?",(node_id,doc,project,user))
		if not parent=="0":
			if not count_children(parent,doc,project,user)>0:
				delete_node(parent,doc,project,user)
			elif get_kind(parent,doc,project,user)=="span" and count_span_children(parent,doc,project,user)==0: # Span just lost its last span child, delete it
				delete_node(parent,doc,project,user)
			elif get_kind(parent,doc,project,user)=="multinuc" and count_multinuc_children(parent,doc,project,user)==0: # Multinuc just lost its last multinuc child, delete it
				delete_node(parent,doc,project,user)


def insert_parent(node_id,new_rel,node_kind,doc,project,user):
	lr = get_node_lr(node_id,doc,project,user)
	old_parent = get_parent(node_id,doc,project,user)
	old_rel = get_rel(node_id,doc,project,user)
	new_parent = str(get_max_node_id(doc,project,user) + 1)
	add_node(new_parent,lr[0],lr[1],old_parent,old_rel,"",node_kind,doc,project,user)
	update_parent(node_id,new_parent,doc,project,user)
	update_rel(node_id,new_rel,doc,project,user)


def reset_rst_doc(doc,project,user):
	generic_query("DELETE FROM rst_nodes WHERE doc=? and project=? and user=?",(doc,project,user))
	generic_query("""INSERT INTO rst_nodes (id, left, right, parent, depth, kind, contents, relname, doc, project, user)
	              SELECT id, left, right, parent, depth, kind, contents, relname, doc, project, '""" + user + "' FROM rst_nodes WHERE doc=? and project=? and user='_orig'""",(doc,project))
	generic_query("DELETE FROM rst_signals WHERE doc=? and project=? and user=?",(doc,project,user))
	generic_query("""INSERT INTO rst_signals (source, type, subtype, tokens, doc, project, user)
	              SELECT source, type, subtype, tokens, doc, project, '""" + user + "' FROM rst_signals WHERE doc=? and project=? and user='_orig'""",(doc,project))


def get_children(parent,doc,project,user):
	return generic_query("SELECT id from rst_nodes WHERE parent=? and doc=? and project=? and user=?",(parent,doc,project,user))


def get_max_node_id(doc,project,user):
	return generic_query("SELECT max(CAST (id as decimal)) as max_id from rst_nodes WHERE doc=? and project=? and user=?",(doc,project,user))[0][0]


def get_max_right(doc,project,user):
	return generic_query("SELECT max(right) as max_right from rst_nodes WHERE doc=? and project=? and user=?",(doc,project,user))[0][0]


def get_users(doc,project):
	return generic_query("SELECT user from rst_nodes WHERE doc=? and project=? and not user='_orig'",(doc,project))


def generic_query(sql,params):
	dbpath = os.path.dirname(os.path.realpath(__file__)) + os.sep +".."+os.sep+"rstweb.db"
	conn = sqlite3.connect(dbpath)

	with conn:
		cur = conn.cursor()
		cur.execute(sql,params)
		rows = cur.fetchall()
		return rows


def export_document(doc, project,exportdir):
	doc_users = get_users(doc,project)
	for user in doc_users:
		this_user = user[0]
		rst_out = get_export_string(doc, project, this_user)
		filename = project + "_" + doc + "_" + this_user + ".rs3"
		f = codecs.open(exportdir + filename, 'w','utf-8')
		f.write(rst_out)


def get_export_string(doc, project, user):
	rels = get_rst_rels(doc,project)
	nodes = get_rst_doc(doc,project,user)
	signals = get_signals(doc,project,user)
	rst_out = '''<rst>
\t<header>
\t\t<relations>
'''
	for rel in rels:
		relname_string = re.sub(r'_[rm]$','',rel[0])
		rst_out += '\t\t\t<rel name="' + relname_string + '" type="' + rel[1] + '"/>\n'

	rst_out += '''\t\t</relations>
\t</header>
\t<body>
'''
	for node in nodes:
		if node[5] == "edu":
			if len(node[7]) > 0:
				relname_string = re.sub(r'_[rm]$','',node[7])
			else:
				relname_string = ""
			if node[3] == "0":
				parent_string = ""
				relname_string = ""
			else:
				parent_string = 'parent="'+node[3]+'" '
			if len(relname_string) > 0:
				relname_string = 'relname="' + relname_string+'"'
			contents = node[6]
			# Handle XML escapes
			contents = re.sub(r'&([^ ;]*) ',r'&amp;\1 ',contents)
			contents = re.sub(r'&$','&amp;',contents)
			contents = contents.replace(">","&gt;").replace("<","&lt;")
			rst_out += '\t\t<segment id="'+node[0]+'" '+ parent_string + relname_string+'>'+contents+'</segment>\n'
	for node in nodes:
		if node[5] != "edu":
			if len(node[7]):
				relname_string = re.sub(r'_[rm]$','',node[7])
				relname_string = 'relname="'+relname_string+'"'
			else:
				relname_string = ""
			if node[3] == "0":
				parent_string = ""
				relname_string = ""
			else:
				parent_string = 'parent="'+node[3]+'"'
			if len(relname_string) > 0:
				parent_string += ' '
			rst_out += '\t\t<group id="'+node[0]+'" type="'+node[5]+'" ' + parent_string + relname_string+'/>\n'

	if len(signals) > 0:
		rst_out += "\t\t<signals>\n"
		for signal in signals:
			source, signal_type, signal_subtype, tokens = signal
			rst_out += '\t\t\t<signal source="' + source + '" type="' + signal_type + '" subtype="' + signal_subtype + '" tokens="' + tokens + '"/>\n'
		rst_out += "\t\t</signals>\n"
	rst_out += '''\t</body>
</rst>'''
	return rst_out


def delete_document(doc,project):
	generic_query("DELETE FROM rst_nodes WHERE doc=? and project=?",(doc,project))
	generic_query("DELETE FROM rst_relations WHERE doc=? and project=?",(doc,project))
	generic_query("DELETE FROM rst_signals WHERE doc=? and project=?",(doc,project))
	generic_query("DELETE FROM docs WHERE doc=? and project=?",(doc,project))


def delete_project(project):
	generic_query("DELETE FROM rst_nodes WHERE project=?",(project,))
	generic_query("DELETE FROM rst_relations WHERE project=?",(project,))
	generic_query("DELETE FROM rst_signals WHERE project=?",(project,))
	generic_query("DELETE FROM docs WHERE project=?",(project,))
	generic_query("DELETE FROM projects WHERE project=?",(project,))


def insert_seg(token_num, doc, project, user):
	tok_seg_map = get_tok_map(doc,project,user)
	seg_to_split = tok_seg_map[token_num]
	push_up(int(seg_to_split),doc,project,user)
	parts = get_split_text(token_num,doc,project,user)
	update_seg_contents(seg_to_split,parts[0].strip(),doc,project,user)
	add_seg(str(int(seg_to_split)+1),parts[1].strip(),doc,project,user)

def get_tok_map(doc,project,user):
	rows = generic_query("SELECT id, contents FROM rst_nodes WHERE kind='edu' and doc=? and project=? and user=? ORDER BY CAST(id AS int)",(doc,project,user))
	all_tokens = {}
	token_counter = 0
	for row in rows:
		edu_text = row[1].strip()
		edu_tokens = edu_text.split(" ")
		for token in edu_tokens:
			token_counter += 1
			all_tokens[token_counter] = row[0]

	return all_tokens


def push_up(push_above_this_seg,doc,project,user):
	ids_above_push = generic_query("SELECT id from rst_nodes WHERE CAST(id as int) > ? and doc=? and project=? and user=? ORDER BY CAST(id as int) DESC",(push_above_this_seg,doc,project,user))
	for row in ids_above_push: #Do this row-wise to avoid sqlite unique constraint behavior
		id_to_increment = row[0]
		generic_query("UPDATE rst_nodes set id = CAST((CAST(id as int) + 1) as text) WHERE id=? and doc=? and project=? and user=?",(id_to_increment,doc,project,user))
		generic_query("UPDATE rst_signals set source = CAST((CAST(source as int) + 1) as text) WHERE source=? and doc=? and project=? and user=?",(id_to_increment,doc,project,user))
	generic_query("UPDATE rst_nodes set parent = CAST((CAST(parent as int) + 1) as text) WHERE CAST(parent as int)>? and doc=? and project=? and user=?",(push_above_this_seg,doc,project,user))
	generic_query("UPDATE rst_nodes set left = left + 1 WHERE left>? and doc=? and project=? and user=?",(push_above_this_seg,doc,project,user))
	generic_query("UPDATE rst_nodes set right = right + 1 WHERE right>? and doc=? and project=? and user=?",(push_above_this_seg,doc,project,user))


def push_down(push_above_this_seg,doc,project,user):
	ids_above_push = generic_query("SELECT id from rst_nodes WHERE CAST(id as int) > ? and doc=? and project=? and user=? ORDER BY CAST(id as int)",(push_above_this_seg,doc,project,user))
	for row in ids_above_push: #Do this row-wise to avoid sqlite unique constraint behavior
		id_to_decrement = row[0]
		generic_query("UPDATE rst_nodes set id = CAST((CAST(id as int) - 1) as text) WHERE id=? and doc=? and project=? and user=?",(id_to_decrement,doc,project,user))
		generic_query("UPDATE rst_signals set source = CAST((CAST(source as int) - 1) as text) WHERE source=? and doc=? and project=? and user=?",(id_to_decrement,doc,project,user))
	generic_query("UPDATE rst_nodes set parent = CAST((CAST(parent as int) - 1) as text) WHERE CAST(parent as int)>? and doc=? and project=? and user=?",(push_above_this_seg,doc,project,user))
	generic_query("UPDATE rst_nodes set left = left - 1 WHERE left>? and doc=? and project=? and user=?",(push_above_this_seg,doc,project,user))
	generic_query("UPDATE rst_nodes set right = right - 1 WHERE right>? and doc=? and project=? and user=?",(push_above_this_seg,doc,project,user))


def get_split_text(tok_num,doc,project,user):
	rows = generic_query("SELECT id, contents FROM rst_nodes WHERE kind='edu' and doc=? and project=? and user=? ORDER BY CAST(id AS int)",(doc,project,user))
	token_counter = 0
	do_return = False
	final = []
	part1 = ""
	part2 = ""
	for row in rows:
		if do_return:
			do_return = False
			final = [part1.strip(),part2.strip()]
		else:
			part1 = ""
			part2 = ""
		edu_text = row[1].strip()
		edu_tokens = edu_text.split(" ")
		for token in edu_tokens:
			token_counter += 1
			if do_return == False:
				part1+=token + " "
			else:
				part2+=token + " "
			if tok_num == token_counter:
				do_return = True
	if do_return:
		final = [part1.strip(),part2.strip()]

	return final


def update_seg_contents(id,contents,doc,project,user):
	generic_query("UPDATE rst_nodes set contents=? WHERE id=? and doc=? and project=? and user=?",(contents,id,doc,project,user))


def get_seg_contents(id,doc,project,user):
	return generic_query("SELECT contents from rst_nodes WHERE id=? and doc=? and project=? and user=?",(id,doc,project,user))[0][0]


def add_seg(id,contents,doc,project,user):
	generic_query("INSERT INTO rst_nodes VALUES(?,?,?,?,?,?,?,?,?,?,?)", (id,id,id,"0","0","edu",contents,get_def_rel("rst",doc,project),doc,project,user))


def merge_seg_forward(last_tok_num,doc,project,user):
	tok_seg_map = get_tok_map(doc,project,user)
	seg_to_merge_forward = tok_seg_map[last_tok_num]
	part1 = get_seg_contents(str(seg_to_merge_forward),doc,project,user)
	part2 = get_seg_contents(str(int(seg_to_merge_forward)+1),doc,project,user)
	update_seg_contents(seg_to_merge_forward,part1+" "+part2,doc,project,user)

	### TODO: WE need to unlink not just the EDU, but also anybody who has a parent or ancestor of that should have parent=0

	#delete_node(get_parent(str(int(seg_to_merge_forward)+1),doc,project,user),doc,project,user)
	#unlink_children(str(int(seg_to_merge_forward)+1),doc,project,user)
	#unlink the edu marked for deletion
	update_parent(str(int(seg_to_merge_forward)+1),"0",doc,project,user)
	children = get_children(str(int(seg_to_merge_forward)+1),doc,project,user)
	#unlink its children
	for child in children:
		update_parent(child[0],"0",doc,project,user)
	#remove it from the database
	generic_query("DELETE FROM rst_nodes WHERE id=? and doc=? and project=? and user=?",(str(int(seg_to_merge_forward)+1),doc,project,user))
	generic_query("DELETE FROM rst_signals WHERE source=? and doc=? and project=? and user=?",(str(int(seg_to_merge_forward)+1),doc,project,user))
	push_down(int(seg_to_merge_forward),doc,project,user)


def copy_doc_to_user(doc, project, user):
	doc_to_copy = generic_query("SELECT id, left, right, parent, depth, kind, contents, relname, doc, project FROM rst_nodes WHERE doc=? and project=? and user='_orig'", (doc,project))
	copy = []
	for row in doc_to_copy:
		row += (user,)
		copy += (row,)

	dbpath = os.path.dirname(os.path.realpath(__file__)) + os.sep +".."+os.sep+"rstweb.db"
	conn = sqlite3.connect(dbpath)
	cur = conn.cursor()
	cur.executemany('INSERT INTO rst_nodes VALUES(?,?,?,?,?,?,?,?,?,?,?)', copy)
	cur.execute("INSERT INTO docs VALUES (?,?,?)", (doc,project,user))
	conn.commit()

	signals_to_copy = generic_query("SELECT source, type, subtype, tokens, doc, project FROM rst_signals WHERE doc=? and project=? and user='_orig'", (doc,project))
	copy = []
	for row in signals_to_copy:
		row += (user,)
		copy += (row,)

	if len(copy)>0:
		dbpath = os.path.dirname(os.path.realpath(__file__)) + os.sep +".."+os.sep+"rstweb.db"
		conn = sqlite3.connect(dbpath)
		cur = conn.cursor()
		cur.executemany('INSERT INTO rst_signals VALUES(?,?,?,?,?,?,?)', copy)
		conn.commit()


def get_assigned_users():
	return generic_query("SELECT DISTINCT user from docs where not user = '_orig' ORDER BY user COLLATE NOCASE",())


def get_assignments(user):
	return generic_query("SELECT DISTINCT doc, project from docs where user=? ORDER BY user COLLATE NOCASE",(str(user),))


def delete_doc_user_version(doc,project,user):
	generic_query("DELETE FROM rst_nodes WHERE doc=? and project=? and user=?",(doc,project,user))
	generic_query("DELETE FROM rst_signals WHERE doc=? and project=? and user=?",(doc,project,user))
	generic_query("DELETE FROM docs WHERE doc=? and project=? and user=?",(doc,project,user))


def get_node_lr(node_id,doc,project,user):
	left =  generic_query("SELECT left FROM rst_nodes WHERE id=? and doc=? and project=? and user=?",(node_id,doc,project,user))[0][0]
	right =  generic_query("SELECT right FROM rst_nodes WHERE id=? and doc=? and project=? and user=?",(node_id,doc,project,user))[0][0]
	return [left,right]


def delete_docs_for_user(user):
	generic_query("DELETE FROM rst_nodes WHERE user=?",(user,))
	generic_query("DELETE FROM rst_signals WHERE user=?",(user,))
	generic_query("DELETE FROM docs WHERE user=?",(user,))


def update_log(doc,project,user,logging,mode,time):
	actions = logging.split(";")
	for action in actions:
		if len(action) > 1:
			generic_query("INSERT INTO logging VALUES (?,?,?,?,?,?)",(doc,project,user,action,mode,time))


def get_setting(setting):
	schema = get_schema()
	if schema > 1:
		try:
			return generic_query("SELECT svalue FROM settings where setting=?",(setting,))[0][0]
		except IndexError:
			return ""
	else:
		return ""


def save_setting(setting, svalue):
	schema = get_schema()
	if schema > 1:
		generic_query("INSERT INTO settings VALUES (?,?)",(setting,svalue))


def set_guidelines_url(project,guideline_url):
	generic_query("UPDATE projects SET guideline_url=? where project=?",(guideline_url,project))


def get_guidelines_url(project):
	schema = get_schema()
	if schema < 2 or project == "":
		return ""
	else:
		guidelines =  generic_query("select guideline_url FROM projects where project=?",(project,))[0][0]
		if guidelines is None:
			return ""
		else:
			return guidelines


def clean_floating_nodes(doc, project, user):
	sql = """SELECT id FROM rst_nodes
WHERE id NOT IN (SELECT parent FROM rst_nodes where not parent = 0 AND doc=? AND project=? AND user=?) AND
NOT kind = 'edu' AND
doc=? AND project=? AND user=?;"""

	floating = generic_query(sql,(doc,project,user,doc,project,user))
	if len(floating) > 0:
		ids_to_del = []
		for floater in floating:
			ids_to_del.append(str(floater[0]))

		id_string = ",".join(ids_to_del)
		del_query = "DELETE from rst_nodes where ID in ("+ id_string +") and doc=? and project=? and user=?;"
		generic_query(del_query,(doc,project,user))
		del_query = "DELETE from rst_signals where source in ("+ id_string +") and doc=? and project=? and user=?;"
		generic_query(del_query,(doc,project,user))


def update_signals(signals_blob, doc, project, user):
	"""
	:param signals_blob: list of strings, each containing a comma separated quadruple of signal specs:
						 example: 45,dm,but,5-6-9   # a signal of type dm, subtype but added to node 45, signaled by tokens 5, 6 and 9
	:return: None
	"""
	params = (doc, project, user)
	generic_query("DELETE from rst_signals WHERE doc=? and project=? and user=?", params)

	for signal in signals_blob:
		source, sig_type, subtype, tokens = signal.split(",")
		tokens = tokens.replace("-",",")
		params = (source, sig_type, subtype, tokens, doc, project, user)
		generic_query("INSERT INTO rst_signals VALUES (?,?,?,?,?,?,?)",params)

def get_signals(doc, project, user):
	schema = get_schema()
	if schema < 6:
		update_schema()
	return generic_query("SELECT source, type, subtype, tokens FROM rst_signals WHERE doc=? and project=? and user=?", (doc,project,user))

def get_signal_types(doc, project):
	return generic_query("SELECT majtype, subtype FROM rst_signal_types WHERE doc=? and project=?", (doc,project))

def get_signal_types_dict(doc, project):
	d = {}
	for majtype, subtype in get_signal_types(doc, project):
		if majtype not in d:
			d[majtype] = []
		d[majtype].append(subtype)

	return d
