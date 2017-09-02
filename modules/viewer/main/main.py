#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
A converter for RST structures which reads RS3 files and writes HTML/Javascript.

This is merely a fork of Amir Zeldes' rstWeb package, a web-based annotation
tool for Rhetorical Structure Theory available here:
https://github.com/amir-zeldes/rstWeb .

The present module is adapted from the version by Arne Neumann at
https://github.com/arne-cl/rstviewer/
"""

import codecs
import os, platform
import sys
import tempfile
import zipfile


class MyZipFile(zipfile.ZipFile):

	def extract(self, member, path=None, pwd=None):
		if not isinstance(member, zipfile.ZipInfo):
			member = self.getinfo(member)

		if path is None:
			path = os.getcwd()

		ret_val = self._extract_member(member, path, pwd)
		#attr = member.external_attr >> 16
		attr = 0755
		os.chmod(ret_val, attr)
		return ret_val

from rstweb_sql import (
	import_document, get_def_rel, get_max_right, get_multinuc_children_lr,
	get_multinuc_children_lr_ids, get_rel_type,
	get_rst_doc, get_rst_rels, setup_db)
from rstweb_classes import NODE, get_depth, get_left_right


def rs3tohtml(rs3_filepath, user='temp_user', project='rstviewer_temp'):

	# TODO: Inject this from structure.py to avoid DRY violation

	setup_db()
	import_document(filename=rs3_filepath, project=project, user=user)

	ROOT_DIR = os.path.dirname(os.path.realpath(__file__)) + os.sep + ".." + os.sep

	UTF8Writer = codecs.getwriter('utf8')
	sys.stdout = UTF8Writer(sys.stdout)

	###GRAPHICAL PARAMETERS###
	top_spacing = 0
	layer_spacing = 60

	templatedir = os.path.join(ROOT_DIR, 'templates')
	script_dir = os.path.join(ROOT_DIR, 'script')

	current_doc = os.path.basename(rs3_filepath)
	current_project = project

	with open(os.path.join(templatedir, 'main.html'), 'r') as template:
		header = template.read()

	header = header.replace("**page_title**","RST Viewer")
	header = header.replace("**doc**",current_doc)
	header = header.replace(
		"**css_dir**", os.path.join(ROOT_DIR, 'css'))
	header = header.replace('**script_dir**', script_dir)

	cpout = ""
	cpout += header

	cpout += '''<div>\n'''

	rels = get_rst_rels(current_doc, current_project)
	def_multirel = get_def_rel("multinuc",current_doc, current_project)
	def_rstrel = get_def_rel("rst",current_doc, current_project)
	multi_options =""
	rst_options =""
	rel_kinds = {}
	for rel in rels:
		if rel[1]=="multinuc":
			multi_options += "<option value='"+rel[0]+"'>"+rel[0].replace("_m","")+'</option>'
			rel_kinds[rel[0]] = "multinuc"
		else:
			rst_options += "<option value='"+rel[0]+"'>"+rel[0].replace("_r","")+'</option>'
			rel_kinds[rel[0]] = "rst"
	multi_options += "<option value='"+def_rstrel+"'>(satellite...)</option>"


	nodes={}
	rows = get_rst_doc(current_doc,current_project,user)
	for row in rows:
		if row[7] in rel_kinds:
			relkind = rel_kinds[row[7]]
		else:
			relkind = "span"
		if row[5] == "edu":
			nodes[row[0]] = NODE(row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],relkind)
		else:
			nodes[row[0]] = NODE(row[0],0,0,row[3],row[4],row[5],row[6],row[7],relkind)

	for key in nodes:
		node = nodes[key]
		get_depth(node,node,nodes)

	for key in nodes:
		if nodes[key].kind == "edu":
			get_left_right(key, nodes,0,0,rel_kinds)

	anchors = {}
	pix_anchors = {}

	# Calculate anchor points for nodes
	# First get proportional position for anchor
	for key in sorted(nodes, key = lambda id: nodes[id].depth, reverse=True):
		node = nodes[key]
		if node.kind=="edu":
			anchors[node.id]= "0.5"
		if node.parent!="0":
			parent = nodes[node.parent]
			parent_wid = (parent.right- parent.left+1) * 100 - 4
			child_wid = (node.right- node.left+1) * 100 - 4
			if node.relname == "span":
				if node.id in anchors:
					anchors[parent.id] = str(((node.left - parent.left)*100)/parent_wid+float(anchors[node.id])*float(child_wid/parent_wid))
				else:
					anchors[parent.id] = str(((node.left - parent.left)*100)/parent_wid+(0.5*child_wid)/parent_wid)
			elif node.relkind=="multinuc" and parent.kind =="multinuc":
				# For multinucs, the anchor is in the middle between leftmost and rightmost of the multinuc children
				# (not including other rst children)
				lr = get_multinuc_children_lr(node.parent,current_doc,current_project,user)
				lr_wid = (lr[0] + lr[1]) /2
				lr_ids = get_multinuc_children_lr_ids(node.parent,lr[0],lr[1],current_doc,current_project,user)
				left_child = lr_ids[0]
				right_child = lr_ids[1]
				if left_child == right_child:
					anchors[parent.id] = "0.5"
				else:
					if left_child in anchors and right_child in anchors: #both leftmost and rightmost multinuc children have been found
						len_left = nodes[left_child].right-nodes[left_child].left+1
						len_right = nodes[right_child].right-nodes[right_child].left+1
						anchors[parent.id] = str(((float(anchors[left_child]) * len_left*100 + float(anchors[right_child]) * len_right * 100 + (nodes[right_child].left - parent.left) * 100)/2)/parent_wid)
					else:
						anchors[parent.id] = str((lr_wid - parent.left+1) / (parent.right - parent.left+1))

			else:
				if not parent.id in anchors:
					anchors[parent.id] = "0.5"

	# Place anchor element to center on proportional position relative to parent
	for key in nodes:
		node = nodes[key]
		pix_anchors[node.id] = str(int(3+node.left * 100 -100 - 39 + float(anchors[node.id])*((node.right- node.left+1) * 100 - 4)))


	for key in nodes:
		node = nodes[key]
		if node.kind != "edu":
			g_wid = str(int((node.right- node.left+1) *100 -4 ))
			cpout += '<div id="lg'+ node.id +'" class="group" style="left: ' +str(int(node.left*100 - 100))+ 'px; width: ' + g_wid + '; top:'+ str(int(top_spacing + layer_spacing+node.depth*layer_spacing)) +'px; z-index:1">\n'
			cpout += '\t<div id="wsk'+node.id+'" class="whisker" style="width:'+g_wid+';"></div>\n</div>\n'
			cpout += '<div id="g'+ node.id +'" class="num_cont" style="position: absolute; left:' + pix_anchors[node.id] +'px; top:'+ str(int(4+ top_spacing + layer_spacing+node.depth*layer_spacing))+'px; z-index:'+str(int(200-(node.right-node.left)))+'">\n'
			cpout += '\t<table class="btn_tb">\n\t\t<tr>'
			cpout += '\n\t\t\t<td rowspan="2"><span class="num_id">'+str(int(node.left))+"-"+str(int(node.right))+'</span></td>\n'
			cpout += '\t</table>\n</div>\n<br/>\n\n'

		elif node.kind=="edu":
			cpout += '<div id="edu'+str(node.id)+'" class="edu" title="'+str(node.id)+'" style="left:'+str(int(node.id)*100 - 100) +'px; top:'+str(int(top_spacing +layer_spacing+node.depth*layer_spacing))+'px; width: 96px">\n'
			cpout += '\t<div id="wsk'+node.id+'" class="whisker" style="width:96px;"></div>'
			cpout += '\n\t<div class="edu_num_cont">'
			cpout += '\n\t\t<table class="btn_tb">\n\t\t\t<tr>'
			cpout += '\n\t\t\t\t<td rowspan="2"><span class="num_id">&nbsp;'+str(int(node.left))+'&nbsp;</span></td>\n'
			cpout += '</table>\n</div>'+node.text+'</div>\n'


	max_right = get_max_right(current_doc,current_project,user)

	cpout += '''<script src="file:///{script_dir}/jquery.jsPlumb-1.7.5-min.js"></script>\n<script>\n'''.format(
		script_dir=script_dir)

	cpout += 'function select_my_rel(options,my_rel){'
	cpout += 'var multi_options = "' + multi_options +'";'
	cpout += 'var rst_options = "' + rst_options +'";'
	cpout += 'if (options =="multi"){options = multi_options;} else {options=rst_options;}'
	cpout += '	  return options.replace("<option value='+"'" +'"' + '+my_rel+'+'"' +"'"+'","<option selected='+"'"+'selected'+"'"+' value='+"'" +'"'+ '+my_rel+'+'"' +"'"+'");'
	cpout += '		  }\n'
	cpout += '''function make_relchooser(id,option_type,rel){
		return $("<select class='rst_rel' id='sel"+id.replace("n","")+"' onchange='crel(" + id.replace("n","") + ",this.options[this.selectedIndex].value);'>" + select_my_rel(option_type,rel) + "</select>");
	}'''
	cpout += '''
			jsPlumb.importDefaults({
			PaintStyle : {
				lineWidth:2,
				strokeStyle: 'rgba(0,0,0,0.5)'
			},
			Endpoints : [ [ "Dot", { radius:1 } ], [ "Dot", { radius:1 } ] ],
			  EndpointStyles : [{ fillStyle:"#000000" }, { fillStyle:"#000000" }],
			  Anchor:"Top",
				Connector : [ "Bezier", { curviness:50 } ]
			})
			 jsPlumb.ready(function() {

	jsPlumb.setContainer(document.getElementById("inner_canvas"));
	'''

	cpout += "jsPlumb.setSuspendDrawing(true);"


	for key in nodes:
		node = nodes[key]
		if node.kind == "edu":
			node_id_str = "edu" + node.id
		else:
			node_id_str = "g" + node.id
		cpout += 'jsPlumb.makeSource("'+node_id_str+'", {anchor: "Top", filter: ".num_id", allowLoopback:false});'
		cpout += 'jsPlumb.makeTarget("'+node_id_str+'", {anchor: "Top", filter: ".num_id", allowLoopback:false});'


	# Connect nodes
	for key in nodes:
		node = nodes[key]
		if node.parent!="0":
			parent = nodes[node.parent]
			if node.kind == "edu":
				node_id_str = "edu" + node.id
			else:
				node_id_str = "g" + node.id
			if parent.kind == "edu":
				parent_id_str = "edu" + parent.id
			else:
				parent_id_str = "g" + parent.id

			if node.relname == "span":
				cpout += 'jsPlumb.connect({source:"'+node_id_str+'",target:"'+parent_id_str+ '", connector:"Straight", anchors: ["Top","Bottom"]});'
			elif parent.kind == "multinuc" and node.relkind=="multinuc":
				cpout += 'jsPlumb.connect({source:"'+node_id_str+'",target:"'+parent_id_str+ '", connector:"Straight", anchors: ["Top","Bottom"], overlays: [ ["Custom", {create:function(component) {return make_relchooser("'+node.id+'","multi","'+node.relname+'");},location:0.2,id:"customOverlay"}]]});'
			else:
				cpout += 'jsPlumb.connect({source:"'+node_id_str+'",target:"'+parent_id_str+'", overlays: [ ["Arrow" , { width:12, length:12, location:0.95 }],["Custom", {create:function(component) {return make_relchooser("'+node.id+'","rst","'+node.relname+'");},location:0.1,id:"customOverlay"}]]});'


	cpout += '''

		jsPlumb.setSuspendDrawing(false,true);


		jsPlumb.bind("connection", function(info) {
		   source = info.sourceId.replace(/edu|g/,"")
		   target = info.targetId.replace(/edu|g/g,"")
		});

		jsPlumb.bind("beforeDrop", function(info) {
			$(".minibtn").prop("disabled",true);

	'''

	cpout += '''
			var node_id = "n"+info.sourceId.replace(/edu|g|lg/,"");
			var new_parent_id = "n"+info.targetId.replace(/edu|g|lg/,"");

			nodes = parse_data();
			new_parent = nodes[new_parent_id];
			relname = nodes[node_id].relname;
			new_parent_kind = new_parent.kind;
			if (nodes[node_id].parent != "n0"){
				old_parent_kind = nodes[nodes[node_id].parent].kind;
			}
			else
			{
				old_parent_kind ="none";
			}

			if (info.sourceId != info.targetId){
				if (!(is_ancestor(new_parent_id,node_id))){
					jsPlumb.select({source:info.sourceId}).detach();
					if (new_parent_kind == "multinuc"){
						relname = get_multirel(new_parent_id,node_id,nodes);
						jsPlumb.connect({source:info.sourceId, target:info.targetId, connector:"Straight", anchors: ["Top","Bottom"], overlays: [ ["Custom", {create:function(component) {return make_relchooser(node_id,"multi",relname);},location:0.2,id:"customOverlay"}]]});
					}
					else{
						jsPlumb.connect({source:info.sourceId, target:info.targetId, overlays: [ ["Arrow" , { width:12, length:12, location:0.95 }],["Custom", {create:function(component) {return make_relchooser(node_id,"rst",relname);},location:0.1,id:"customOverlay"}]]});
					}
					new_rel = document.getElementById("sel"+ node_id.replace("n","")).value;
					act('up:' + node_id.replace("n","") + ',' + new_parent_id.replace("n",""));
					update_rel(node_id,new_rel,nodes);
					recalculate_depth(parse_data());
				}
			}

			$(".minibtn").prop("disabled",false);

		});

	});
</script>

</div>
</body>
</html>
'''
	return cpout


def rs3topng(rs3_filepath, png_filepath=None):

	try:
		from selenium import webdriver
		from selenium.common.exceptions import WebDriverException
	except ImportError:
		raise ImportError('Please install selenium to use images: pip install selenium')

	html_str = rs3tohtml(rs3_filepath)
	html_str = html_str.replace('="C:','="file:///C:')  # Make real file URIs for Windows
	html_str = html_str.replace('<body','<body style="background-color:white"')  # Make white background for PNG

	temp = tempfile.NamedTemporaryFile(suffix='.html', delete=False)
	temp.write(html_str.encode('utf8'))
	print(temp.name)
	temp.close()

	try:
		ver = "-2.1.1"
		if platform.system() == "Linux":
			os_suff = ver + "-linux-x86_64"
		elif platform.system() == "Windows":
			os_suff = ver + "-windows"
		else:
			os_suff = ver + "-macosx"

		ex_path = os.path.dirname(os.path.realpath(
			__file__)) + os.sep + "phantomjs" + os.sep + "phantomjs"  # "bin" + os.sep + os_subdir + os.sep + "phantomjs"
		if not (os.path.isfile(ex_path) or os.path.isfile(ex_path + ".exe")):
			zip_ref = MyZipFile(ex_path + os_suff + ".zip", "r")
			zip_ref.extractall(os.path.dirname(os.path.realpath(__file__)) + os.sep + "phantomjs")
		driver = webdriver.PhantomJS(executable_path=ex_path)
	except OSError as err:
		raise OSError(err.message)
	except WebDriverException as err:
		print('Error with phantomjs executable at modules/viewer/main/phantomjs/\n' + err.msg)
		raise WebDriverException('Error with phantomjs executable at modules/viewer/main/phantomjs/phantomjs\n' + err.msg)

	driver.get("file:///"+temp.name)
	driver.save_screenshot(png_filepath)   ## WORKS ##

if __name__ == '__main__':
	# Entry point when called via subprocess/cli
	# Expects two file path arguments: infile.rs3, outfile.png
	rs3topng(sys.argv[1], sys.argv[2])
	#rs3topng("c:\\uni\\corpora\\gum\\rst\\example_edus.txt", "C:\\uni\\test4.png")

