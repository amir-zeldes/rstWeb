#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Functions for reading .rs3 and text files during document import
Author: Amir Zeldes
"""

import codecs
import re
import collections
from xml.dom import minidom
from xml.parsers.expat import ExpatError
from modules.rstweb_classes import *
from modules.whitespace_tokenize import tokenize


def read_rst(filename, rel_hash, do_tokenize=False):

	f = codecs.open(filename, "r", "utf-8")
	try:
		xmldoc = minidom.parseString(codecs.encode (f.read(), "utf-8"))
	except ExpatError:
		message = "Invalid .rs3 file"
		return message

	nodes = []
	ordered_id = {}
	schemas = []
	default_rst = ""

	# Get relation names and their types, append type suffix to disambiguate
	# relation names that can be both RST and multinuc
	item_list = xmldoc.getElementsByTagName("rel")
	for rel in item_list:
		relname = re.sub(r"[:;,]","",rel.attributes["name"].value)
		if rel.hasAttribute("type"):
			rel_hash[relname+"_"+rel.attributes["type"].value[0:1]] = rel.attributes["type"].value
			if rel.attributes["type"].value == "rst" and default_rst=="":
				default_rst = relname+"_"+rel.attributes["type"].value[0:1]
		else:  # This is a schema relation
			schemas.append(relname)


	item_list = xmldoc.getElementsByTagName("segment")
	if len(item_list) < 1:
		return '<div class="warn">No segment elements found in .rs3 file</div>'

	id_counter = 0
	total_toks = 0

	# Get hash to reorder EDUs and spans according to the order of appearance in .rs3 file
	for segment in item_list:
		id_counter += 1
		ordered_id[segment.attributes["id"].value] = id_counter
	item_list = xmldoc.getElementsByTagName("group")
	for group in item_list:
		id_counter += 1
		ordered_id[group.attributes["id"].value] = id_counter
	all_node_ids = set(range(1,id_counter+1))  # All non-zero IDs in documents, which a signal may refer back to
	ordered_id["0"] = 0

	element_types={}
	node_elements = xmldoc.getElementsByTagName("segment")
	for element in node_elements:
		element_types[element.attributes["id"].value] = "edu"
	node_elements = xmldoc.getElementsByTagName("group")
	for element in node_elements:
		element_types[element.attributes["id"].value] = element.attributes["type"].value

	id_counter = 0
	item_list = xmldoc.getElementsByTagName("segment")
	for segment in item_list:
		id_counter += 1
		if segment.hasAttribute("parent"):
			parent = segment.attributes["parent"].value
		else:
			parent = "0"
		if segment.hasAttribute("relname"):
			relname = segment.attributes["relname"].value
		else:
			relname = default_rst

		# Tolerate schemas, but no real support yet:
		if relname in schemas:
			relname = "span"

			relname = re.sub(r"[:;,]","",relname) #remove characters used for undo logging, not allowed in rel names
		# Note that in RSTTool, a multinuc child with a multinuc compatible relation is always interpreted as multinuc
		if parent in element_types:
			if element_types[parent] == "multinuc" and relname+"_m" in rel_hash:
				relname = relname+"_m"
			elif relname !="span":
				relname = relname+"_r"
		else:
			if not relname.endswith("_r") and len(relname)>0:
				relname = relname+"_r"
		edu_id = segment.attributes["id"].value
		if len(segment.childNodes) > 0:  # Check the node is not empty
			contents = segment.childNodes[0].data.strip()
			if len(contents) == 0:
				continue
		else:
			continue

		# Check for invalid XML in segment contents
		if "<" in contents or ">" in contents or "&" in contents:
			contents = contents.replace('>','&gt;')
			contents = contents.replace('<', '&lt;')
			contents = re.sub(r'&([^ ;]* )', r'&amp;\1', contents)
			contents = re.sub(r'&$', r'&amp;', contents)
		if do_tokenize:
			contents = tokenize(contents)
			contents = " ".join(contents.strip().split("\n"))

		total_toks += contents.strip().count(" ") + 1
		nodes.append([str(ordered_id[edu_id]), id_counter, id_counter, str(ordered_id[parent]), 0, "edu", contents, relname])

	item_list = xmldoc.getElementsByTagName("group")
	for group in item_list:
		if group.attributes.length == 4:
			parent = group.attributes["parent"].value
		else:
			parent = "0"
		if group.attributes.length == 4:
			relname = group.attributes["relname"].value
			# Tolerate schemas by treating as spans
			if relname in schemas:
				relname = "span"
				
			relname = re.sub(r"[:;,]","",relname)  # Remove characters used for undo logging, not allowed in rel names
			# Note that in RSTTool, a multinuc child with a multinuc compatible relation is always interpreted as multinuc
			if parent in element_types:
				if element_types[parent] == "multinuc" and relname+"_m" in rel_hash:
					relname = relname+"_m"
				elif relname !="span":
					relname = relname+"_r"
			else:
				relname = ""
		else:
			relname = ""
		group_id = group.attributes["id"].value
		group_type = group.attributes["type"].value
		contents = ""
		nodes.append([str(ordered_id[group_id]),0,0,str(ordered_id[parent]),0,group_type,contents,relname])

	# Collect discourse signal annotations if any are available
	item_list = xmldoc.getElementsByTagName("signal")
	signals = []
	for signal in item_list:
		source = signal.attributes["source"].value
		# This will crash if signal source refers to a non-existing node:
		source = ordered_id[source]
		if source not in all_node_ids:
			raise IOError("Invalid source node ID for signal: " + str(source) + " (from XML file source="+signal.attributes["source"].value+"(\n")
		type = signal.attributes["type"].value
		subtype = signal.attributes["subtype"].value
		tokens = signal.attributes["tokens"].value
		if tokens != "":
			# This will crash if tokens contains non-numbers:
			token_list = [int(tok) for tok in tokens.split(",")]
			max_tok = max(token_list)
			if max_tok > total_toks:
				raise IOError("Signal refers to non-existent token: " + str(max_tok))
		signals.append([str(source),type,subtype,tokens])

	elements = {}
	for row in nodes:
		elements[row[0]] = NODE(row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],"")

	for element in elements:
		if elements[element].kind == "edu":
			get_left_right(element, elements,0,0,rel_hash)

	return elements, signals


def read_text(filename,rel_hash,do_tokenize=False):
	id_counter = 0
	nodes = {}
	f = codecs.open(filename, "r", "utf-8")

	# Add some default relations if none have been supplied (at least 1 rst and 1 multinuc)
	if len(rel_hash) < 2:
		rel_hash["elaboration_r"] = "rst"
		rel_hash["joint_m"] = "multinuc"

	rels = collections.OrderedDict(sorted(rel_hash.items()))

	for line in f:
		contents = line.strip()
		if len(contents) > 0:
			id_counter += 1
			# Check for invalid XML in segment contents
			if "<" in contents or ">" in contents or "&" in contents:
				contents = contents.replace('>','&gt;')
				contents = contents.replace('<', '&lt;')
				contents = re.sub(r'&([^ ;]* )', r'&amp;\1', contents)
				contents = re.sub(r'&$', r'&amp;', contents)
			if do_tokenize:
				contents = tokenize(contents)
				contents = " ".join(contents)

			nodes[str(id_counter)] = NODE(str(id_counter),id_counter,id_counter,"0",0,"edu",contents,list(rels.keys())[0],list(rels.values())[0])

	return nodes


def read_relfile(filename):
	f = codecs.open(filename, "r", "utf-8")
	rels = {}
	for line in f:
		if line.find("\t") > 0:
			rel_data = line.split("\t")
			if rel_data[1].strip() == "rst":
				rels[rel_data[0].strip()+"_r"] = "rst"
			elif rel_data[1].strip() == "multinuc":
				rels[rel_data[0].strip()+"_m"] = "multinuc"

	return rels
