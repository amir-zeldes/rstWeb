import re, sys


def db2rst(rels, nodes, secedges, signals, signal_types, doc, project, user):
	def sequential_ids(rst_xml):
		# Ensure no gaps in node IDs and corresponding adjustments to signals and secedges.
		# Assume input xml IDs are already sorted, but with possible gaps
		output = []
		temp = []
		current_id = 1
		id_map = {}
		for line in rst_xml.split("\n"):
			if ' id="' in line:
				xml_id = re.search(r' id="([^"]+)"', line).group(1)
				if ('<segment ' in line or '<group ' in line):
					id_map[xml_id] = str(current_id)
					line = line.replace(' id="'+xml_id+'"',' id="'+str(current_id)+'"')
					current_id += 1
			temp.append(line)

		for line in temp:
			if ' id="' in line:
				if ' parent=' in line and ('<segment ' in line or '<group ' in line):
					parent_id = re.search(r' parent="([^"]+)"', line).group(1)
					new_parent = id_map[parent_id]
					line = line.replace(' parent="'+parent_id+'"',' parent="'+str(new_parent)+'"')
				elif "<secedge " in line:
					xml_id = re.search(r' id="([^"]+)"', line).group(1)
					src, trg = xml_id.split("-")
					line = line.replace(' source="'+src+'"', ' source="'+id_map[src]+'"')
					line = line.replace(' target="' + trg + '"', ' target="' + id_map[trg] + '"')
					line = line.replace(' id="' + xml_id + '"', ' id="' + id_map[src] + '-' + id_map[trg] + '"')
			elif "<signal " in line:
				source = re.search(r' source="([^"]+)"', line).group(1)
				if "-" in source:
					src, trg = source.split("-")
					line = line.replace(' source="' + source + '"', ' source="' + id_map[src] + '-' + id_map[trg] + '"')
				else:
					if source in id_map:
						line = line.replace(' source="' + source + '"', ' source="' + id_map[source] + '"')
					else:  # Zombie signal pointing to no longer existing node
						from ..rstweb_sql import generic_query
						# Repair the database
						generic_query("DELETE from rst_signals WHERE source like ? and doc=? and project=? and user=?",
									  (source, doc, project, user))
						sys.stderr.write("Removed signal with non-existant source " + source + ":\n"+line+"\n")
						continue
			output.append(line)

		return "\n".join(output)

	rst_out = [
		"<rst>",
		"\t<header>",
		"\t\t<relations>"
	]

	for rel in rels:
		relname_string = re.sub(r'_[rm]$', '', rel[0])
		rst_out.append('\t\t\t<rel name="' + relname_string + '" type="' + rel[1] + '"/>')

	rst_out.append("\t\t</relations>")

	if len(signal_types) > 0:
		rst_out.append("\t\t<sigtypes>")
		for major_type in signal_types:
			minor_types = signal_types[major_type]
			minor_types = ";".join(sorted(minor_types))
			rst_out.append('\t\t\t<sig type="'+major_type+'" subtypes="'+minor_types+'"/>')
		rst_out.append("\t\t</sigtypes>")

	rst_out.append("\t</header>")
	rst_out.append("\t<body>")

	for node in nodes:
		if node[5] == "edu":
			if len(node[7]) > 0:
				relname_string = re.sub(r'_[rm]$', '', node[7])
			else:
				relname_string = ""
			if node[3] == "0":
				parent_string = ""
				relname_string = ""
			else:
				parent_string = 'parent="' + node[3] + '" '
			if len(relname_string) > 0:
				relname_string = 'relname="' + relname_string + '"'
			contents = node[6]
			# Handle XML escapes
			contents = re.sub(r'&([^ ;]*) ', r'&amp;\1 ', contents)
			contents = re.sub(r'&$', '&amp;', contents)
			contents = contents.replace(">", "&gt;").replace("<", "&lt;")
			rst_out.append('\t\t<segment id="' + node[
				0] + '" ' + parent_string + relname_string + '>' + contents + '</segment>')
	for node in nodes:
		if node[5] != "edu":
			if len(node[7]):
				relname_string = re.sub(r'_[rm]$', '', node[7])
				relname_string = 'relname="' + relname_string + '"'
			else:
				relname_string = ""
			if node[3] == "0":
				parent_string = ""
				relname_string = ""
			else:
				parent_string = 'parent="' + node[3] + '"'
			if len(relname_string) > 0:
				parent_string += ' '
			rst_out.append('\t\t<group id="' + node[0] + '" type="' + node[
				5] + '" ' + parent_string + relname_string + '/>')

	if len(secedges) > 0:
		rst_out.append("\t\t<secedges>")
		for s in secedges.split(";"):
			if ":" not in s:
				continue
			src_trg, relname = s.split(":",1)
			src, trg = src_trg.split("-")
			if relname.endswith("_r") or relname.endswith("_m"):
				relname = relname[:-2]
			rst_out.append('\t\t\t<secedge id="'+src+"-"+trg+'" source="' + src + '" target="' + trg + '" relname="' + relname + '"/>')
		rst_out.append("\t\t</secedges>")

	if len(signals) > 0:
		rst_out.append("\t\t<signals>")
		for signal in signals:
			source, signal_type, signal_subtype, tokens = signal
			rst_out.append('\t\t\t<signal source="' + source + '" type="' + signal_type + '" subtype="' + signal_subtype + '" tokens="' + tokens + '"/>')
		rst_out.append("\t\t</signals>")
	rst_out.append("\t</body>")
	rst_out.append("</rst>")
	rst_out = '\n'.join(rst_out) + '\n'
	rst_out = sequential_ids(rst_out)

	return rst_out
