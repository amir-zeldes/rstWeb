#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Basic classes to contain rstWeb objects and methods to calculate their attributes
Author: Amir Zeldes
"""

class NODE:
	def __init__(self, id, left, right, parent, depth, kind, text, relname, relkind, secedges):

		"""Basic class to hold all nodes (EDU, span and multinuc) in structure.py and while importing"""

		self.id = id
		self.parent = parent
		self.left = left
		self.right = right
		self.depth = depth
		self.kind = kind #edu, multinuc or span node
		self.text = text #text of an edu node; empty for spans/multinucs
		self.relname = relname
		self.relkind = relkind #rst (a.k.a. satellite), multinuc or span relation
		self.sortdepth = depth
		self.secedges = secedges


class SEGMENT:
	def __init__(self, id, text):
		""" Class used by segment.py to represent EDUs, NOT used by the structurer in structure.py"""
		self.id = id
		self.text = text
		self.tokens = text.split(" ")

def get_depth(orig_node, probe_node, nodes, doc=None, project=None, user=None):
	"""
	Calculate graphical nesting depth of a node based on the node list graph.
    Note that RST parentage without span/multinuc does NOT increase depth.
    """
	if probe_node.parent != "0":
		try:
			parent = nodes[probe_node.parent]
		except KeyError:
			# Parent node does not exist, set parent to 0
			from modules.rstweb_sql import update_parent
			if doc is not None and project is not None and user is not None:
				update_parent(probe_node.id,"0",doc,project,user)
				return
			else:
				raise KeyError("Node ID " + probe_node.id + " has non existing parent " + probe_node.parent + " and user not set in function\n")
		if parent.kind != "edu" and (probe_node.relname == "span" or parent.kind == "multinuc" and probe_node.relkind =="multinuc"):
			orig_node.depth += 1
			orig_node.sortdepth +=1
		elif parent.kind == "edu":
			orig_node.sortdepth += 1
		get_depth(orig_node, parent, nodes, doc=doc, project=project, user=user)


def get_left_right(node_id, nodes, min_left, max_right, rel_hash):
	"""
	Calculate leftmost and rightmost EDU covered by a NODE object. For EDUs this is the number of the EDU
	itself. For spans and multinucs, the leftmost and rightmost child dominated by the NODE is found recursively.
	"""
	if nodes[node_id].parent != "0" and node_id != "0":
		parent = nodes[nodes[node_id].parent]
		if min_left > nodes[node_id].left or min_left == 0:
			if nodes[node_id].left != 0:
				min_left = nodes[node_id].left
		if max_right < nodes[node_id].right or max_right == 0:
			max_right = nodes[node_id].right
		if nodes[node_id].relname == "span":
			if parent.left > min_left or parent.left == 0:
				parent.left = min_left
			if parent.right < max_right:
				parent.right = max_right
		elif nodes[node_id].relname in rel_hash:
			if parent.kind == "multinuc" and rel_hash[nodes[node_id].relname] =="multinuc":
				if parent.left > min_left or parent.left == 0:
					parent.left = min_left
				if parent.right < max_right:
					parent.right = max_right
		get_left_right(parent.id, nodes, min_left, max_right, rel_hash)
