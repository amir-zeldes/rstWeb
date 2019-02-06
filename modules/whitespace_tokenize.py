#!/usr/bin/python
# -*- coding: utf-8 -*-

########################################################################
#                                                                      #
#  tokenization script for tagger preprocessing                        #
#  Adapted from TreeTagger tokenizer in Perl by:                       #
#          Helmut Schmid, IMS, University of Stuttgart                 #
#          Serge Sharoff, University of Leeds                          #
#  Description:                                                        #
#  - splits input text into tokens (one token per line)                #
#  - cuts off punctuation, parentheses etc.                            #
#  - disambiguates periods                                             #
#  - preserves SGML markup                                             #
#                                                                      #
#  - Ported to Python and adapted by Amir Zeldes                       #
########################################################################


from argparse import ArgumentParser
import io, sys, re

PY3 = sys.version_info[0] >2

# characters which have to be cut off at the beginning of a word
PChar=r"""[¿¡{(`"‚„†‡‹‘’“”•'–—›«"""

# characters which have to be cut off at the end of a word
FChar=r"""'\]}'`"),;:!?%‚„…†‡‰‹‘’“”•–—›'»"""

# character sequences which have to be cut off at the beginning of a word
PClitic=''

# character sequences which have to be cut off at the end of a word
FClitic = ""


def tokenize(text,abbr=None,add_sents=False):

	output = ""
	if add_sents:
		lines = []
		raw_lines = text.split("\n")
		for line in raw_lines:
			if len(line.strip())>0:
				lines.append("<s>" + line + "</s>")
	else:
		lines = text.split("\n")

	# Read the list of abbreviations and words
	Token = set([])
	if abbr is not None:
		abbr_lines = io.open(abbr,encoding="utf8").read().replace("\r","").strip().split("\n")
		for line in abbr_lines:
			Token.add(line)

	for line in lines:
		# replace newlines and tab characters with blanks
		line = line.replace("\t"," ").replace("\n"," ")

		# replace blanks within SGML tags
		sep1 = "□"
		sep2 = "■"

		if not PY3:
			sep1 = sep1.decode("utf8")
			sep2 = sep2.decode("utf8")

		find_tag_space = r'(<[^<> ]*) ([^<>]*>)'
		while re.search(find_tag_space,line) is not None:
			line = re.sub(find_tag_space,'\1'+sep1+'\2',line)

		# replace whitespace with a special character
		line = line.replace(" ",sep2)

		# restore SGML tags
		line = line.replace(sep1," ")
		line = line.replace(sep2,sep1)

		# prepare SGML-Tags for tokenization

		line = re.sub(r'(<[^<>]*>)',sep1 + "\\1" + sep1,line)
		line = re.sub(r'^' + sep1,"",line)
		line = re.sub(sep1 + r'$',"",line)
		line = re.sub(sep1*3 +"*",sep1,line)

		units = line.split(sep1)
		for i, unit in enumerate(units):
			if re.match(r"<.*>$",unit) is not None:
				# SGML tag
				output += unit + "\n"
			else:
				#add a blank at the beginning and the end of each segment
				if i==45:
					a=5
				email = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
				url = r'https?://(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&/=]*)'

				# insert missing blanks after punctuation if not an abbreviation
				if unit not in Token and re.search(email,unit) is None and re.search(url,unit) is None:
					unit = " " + unit + " "
					unit = re.sub(r'\.\.\.'," ... ",unit)
					unit = re.sub(r'([;!?])([^ ])',r'\1 \2', unit)
					unit = re.sub(r'([.,:])([^ 0-9.])', r'\1 \2',unit)
				else:
					unit = " " + unit + " "

				subunits = unit.split()
				for subunit in subunits:
					suffix=""

					# separate punctuation and parentheses from words
					while True:
						finished = True
						# cut off preceding punctuation
						m = re.match(r'(['+PChar+'])(.)',subunit)
						if m is not None:
							m1 = m.group(1)
							subunit = re.sub('(['+PChar+'])(.)',r'\2',subunit)
							output += m1 + "\n"
							finished = 0
						# cut off trailing punctuation
						m = re.search(r'(.)(['+FChar+'])$',subunit)
						if m is not None:
							m2 = m.group(2)
							subunit = re.sub(r'(.)(['+FChar+'])$',r'\1',subunit)
							suffix = m2 + "\n" + suffix
							finished = 0

						# cut off trailing periods if punctuation precedes
						m = re.search(r'(['+FChar+'])\.$',subunit)
						if m is not None:
							subunit = re.sub(r'(['+FChar+'])\.$','',subunit,count=1)
							suffix = ".\n" + suffix
							if subunit == "":
								subunit = m.group(1)
							else:
								suffix = m.group(1) + "\n" + suffix
							finished = False
						if finished:
							break

					# handle explicitly listed tokens
					if subunit in Token:
						output += subunit + "\n" + suffix
						continue

					# abbreviations of the form A. or U.S.A.
					if re.match(r'([A-Za-z-]\.)+$',subunit) is not None:
						output += subunit + "\n" + suffix
						continue

					# e-mail addresses
					if re.search(email,subunit) is not None or re.search(url,subunit) is not None:
						output += subunit + "\n" + suffix
						continue

					# disambiguate periods
					m = re.match(r'(..*)\.$',subunit)
					if m is not None and subunit != "...":
						subunit = m.group(1)
						suffix = ".\n" + suffix
						if subunit in Token:
							output += subunit + "\n" + suffix
							continue

					# cut off clitics
					while re.match(r'(--)(.)',subunit) is not None:
						m = re.match(r'(--)(.)',subunit)
						subunit = re.sub(r'(--)(.)',r'\2',subunit)
						output += m.group(1) + "\n"

					if PClitic != '':
						while re.match(r'('+PClitic+')(.)',subunit) is not None:
							m = re.match(r'('+PClitic+')(.)',subunit)
							subunit = re.sub(r'('+PClitic+')(.)',r'\2',subunit)
							output += m.group(1) + "\n"

					while re.search(r'(.)(--)$',subunit) is not None:
						m = re.match(r'(.)(--)$',subunit)
						subunit = re.sub(r'(.)(--)$',r'\1',subunit)
						suffix = m.group(2) + "\n" + suffix

					if FClitic != "":
						while re.search(r'(.)('+FClitic+')$',subunit) is not None:
							m = re.search(r'(.)('+FClitic+')$',subunit)
							subunit = re.sub(r'(.)('+FClitic+')$',r"\1")
							suffix = m.group(2) + "\n" + suffix
					output+=subunit + "\n" + suffix
	return output


if __name__ == "__main__":

	p = ArgumentParser()
	p.add_argument("infile")
	p.add_argument("-a","--abbreviations",action="store",default=None,help="File name for list of abbreviations and other tokens to leave alone")

	opts = p.parse_args()

	input_text = io.open(opts.infile,encoding="utf8").read().replace("\r","").strip()
	output = tokenize(input_text,opts.abbreviations)
	print(output)
