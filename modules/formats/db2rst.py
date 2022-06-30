import re


def db2rst(rels, nodes, signals):
	rst_out = [
		"<rst>",
		"\t<header>",
		"\t\t<relations>"
	]

	for rel in rels:
		relname_string = re.sub(r'_[rm]$', '', rel[0])
		rst_out.append('\t\t\t<rel name="' + relname_string + '" type="' + rel[1] + '"/>')

	rst_out.append("\t\t</relations>")
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

	if len(signals) > 0:
		rst_out.append("\t\t<signals>")
		for signal in signals:
			source, signal_type, signal_subtype, tokens = signal
			rst_out.append('\t\t\t<signal source="' + source + '" type="' + signal_type + '" subtype="' + signal_subtype + '" tokens="' + tokens + '"/>')
		rst_out.append("\t\t</signals>")
	rst_out.append("\t</body>")
	rst_out.append("</rst>")
	return '\n'.join(rst_out) + '\n'
