import json
import requests
from owlready2 import *
from datetime import datetime
import re

############ File : edam.json ####
# File created with edam.sh script
# from Andreas Tille (member of
# the debian team)
# https://salsa.debian.org/blends-team/website/blob/master/misc/sql/edam.sh
debian_med_metadata = json.load(open('edam.json'))

############ File : EDAM_1.21.xrdf ####
# File with the last EDAM ontology
# V1.21 Released on 07/31/2018
onto = get_ontology("EDAM_1.21.xrdf")
onto.load()

############ File : Log.txt ####
# File that show problems on
# Debian EDAM structure
fichier_log = open("Log.txt", "w")



############ Function is_setted() ####
# Check if an entry exist and is not
# empty on the json
def is_setted(value,entry):
    if value in entry:
        return (entry[value] != None)
    else:
        return False

############ Function get_value() ####
# Return the value from a dict if it's
# exist
def get_value(value, entry):
    if (is_setted(value, entry)):
        return entry[value]
    else:
        return None

############ Function announcement() ####
# Announce something on stdout and log.txt
def announcement(text):
    print(text)
    fichier_log.write(text+"\n\n")

############ Functions search_owl () ####
# Search an uri from EDAM ontology file
# in a specified category
def search_owl(entry,debian_entry,category):
    operation = dict(uri=None, term=None)
    myonto = onto.search_one(label=entry,iri="*"+category+"*")
    if not myonto:
        announcement("/!\(1) package \"" + debian_entry['package'] + "\", no EDAM " + category +" for \"" + entry + "\" on http://bioportal.bioontology.org/ontologies/EDAM version 1.21")
    else:
        operation['uri'] = myonto.iri
        operation['term'] = entry
        return operation

############ Functions search_function() ####
# Search a function URI from EDAM 1.21
# ==> See search_owl()
def search_function(debian_entry):
    biotools_functions = []
    if is_setted("edam_scopes", debian_entry):
        for debian_edam_entry in debian_entry['edam_scopes']:
            biotools_function = dict(operation=[], input=[], output=[], note=None, cmd=None)
            if is_setted('function', debian_edam_entry):
                operation_tab = []
                if isinstance(debian_edam_entry['function'], list):
                    for function_entry in debian_edam_entry['function']:
                        operation_tab.append(search_owl(function_entry, debian_entry, "operation"))
                else:
                    announcement("/!\(2) package \"" + debian_entry['package'] + "\", la fonction\"" + function_entry + " est écris sous forme de chaine de caractère et non de tableau dans le edam.json, elle devrait ressembler à \" 'function': ['" + function_entry + "'] \"")
                    function_entry = get_value("function", debian_edam_entry)
                    operation_tab.append(search_owl(function_entry, debian_entry, "operation"))
                biotools_function['operation'] = operation_tab
                biotools_function['input'] = get_value("inputs", debian_edam_entry)      # S'assurer que c'est bien le format attendu
                biotools_function['output'] = get_value("outputs", debian_edam_entry)    # S'assurer que c'est bien le format attendu
            biotools_functions.append(biotools_function)
    return biotools_functions


############ Functions search_topic() ####
# Search a topic URI from EDAM 1.21
# ==> See search_owl()
def search_topic(debian_entry):
    biotools_topics=[]
    if is_setted("topics",debian_entry):
        if isinstance(debian_entry['topics'], list):
            for topics_entry in debian_entry['topics']:
                biotools_topics.append(search_owl(topics_entry, debian_entry,"topic"))
        else:
            topics_entry = debian_entry['topics']
            announcement("/!\(3) package \"" + debian_entry['package'] + "\", le topic\"" + topics_entry + " est écris sous forme de chaine de caractère et non de tableau dans le edam.json, elle devrait ressembler à \" 'function': ['" + topics_entry + "'] \"")
            biotools_topics.append(search_owl(topics_entry, debian_entry,"topic"))
    return biotools_topics

############ Functions search_publication() ####
# Search pulication metadata from a doi
def search_publication(debian_entry):
    if(is_setted('doi',debian_entry)):
        doi = debian_entry['doi']
        m = re.search("(?P<excess>.*doi\.org.*\/)(?P<doi>\d+.*)", doi)
        if m is not None:
            newdoi=m.group('doi')
            excess=m.group('excess')
            announcement("/!\(4) package \"" + debian_entry['package'] + "\", dans le edam.json le doi \"" + doi + "\" ne doit pas comporter l'URL \"" + excess + " \" il devrai être sous cette forme \"" + newdoi + "\"")
            doi=newdoi
        authors_list = []
        metadata = dict(title="", abstract="", date="", citationCount="", authors=authors_list, journal="")
        publication = dict(doi=doi, pmid=None, pmcid=None, type=None, version=None, metadata=metadata)
        publi = requests.get("https://doi.org/"+doi, headers={'Accept': 'application/vnd.citationstyles.csl+json'})
        if (publi.status_code != 200):
            announcement("/!\(5) package \"" + debian_entry['package'] + "\", dans edam.json le doi \"" + doi + "\" n'a pas un format reconnu par doi.org")
            return None
        publi_json = publi.json()
        publication['type'] = get_value('type', publi_json)  # type
        # publication['version'] = get_value('issue', publi_json)  # issue pour la version ??   ==> NON
        metadata['title'] = get_value('title', publi_json)  # metadata.title
        # metadata['abstract']=                              ?? Pas d'abstract dans la requete
        if is_setted('indexed', publi_json):
            metadata['date'] = get_value('date-time', publi_json['indexed'])  # metadata.date
        metadata['citationCount'] = get_value('is-referenced-by-count',publi_json)  # metadata.citationCount   # S'en assurer
        if (is_setted('author', publi_json)):
            for authors_entry in publi_json['author']:  # metadata.authors
                author = dict(name='')
                if is_setted('family', authors_entry):
                    author['name'] = authors_entry['family'] + " " + authors_entry['given']
                    authors_list.append(author)
                elif is_setted('literal', authors_entry):
                    m = re.search("(?P<given>.*)\s(?P<family>.*)", authors_entry['literal'])
                    if m is not None:
                        author['name'] = m.group('family') + " " + m.group('given')
                        authors_list.append(author)
        metadata['authors'] = authors_list  # metadata.authors
        metadata['journal'] = get_value('container-title', publi_json)  # metadata.journal
        publication['metadata'] = metadata                    #metadata
        return publication
    else:
        return None

#################################################################################
# START

start_datetime=datetime.now()
print(str(start_datetime))
print('Starting analyses, please wait...\n')

i=0 #debug 10 lines

for debian_entry in debian_med_metadata:

    print(i)
    if i<830  :#debug pass X lines
        print(get_value('doi',debian_entry))
        i += 1
        continue
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry = dict(name='', description='', homepage='', biotoolsID='', biotoolsCURIE='', version=[], otherID=[],
                          function=[], toolType=[], topic=[], operatingSystem=[], language=[], license='',
                          collectionID=[], maturity='', cost='', accessibility=[], elixirPlatform=[], elixirNode=[],
                          link=[], download=[], documentation=[], publication=[], credit=[], owner='', additionDate='',
                          lastUpdate='', editPermission=None, validated='', homepage_status='')
    #-----------------------------------------------------------------------------------------------------------------------
    biotools_entry['name'] = get_value('package',debian_entry)
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['description'] = get_value('description', debian_entry)
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['homepage'] = get_value('homepage', debian_entry)
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['biotoolsID'] = get_value('bio.tools', debian_entry)
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['biotoolsCURIE'] = None
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['version'] = get_value('version', debian_entry)
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['otherID'] = []  # debian_entry['']  ????
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['function'] = search_function(debian_entry)
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['toolType'] = [] # debian_entry[''] ???
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['topic'] = search_topic(debian_entry)
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['operatingSystem'] = ["Linux"]
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['language'] = []
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['license'] = None
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['collectionID'] = []
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['maturity'] = None
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['cost'] = None
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['accessibility'] = []
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['elixirPlatform'] = []
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['elixirNode'] = []
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['link'] = []
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['download'] = []
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['documentation'] = ""  # debian_entry['']  A RETRAVAILLER
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['publication'].append(search_publication(debian_entry))
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['credit'] = ""  # debian_entry['']  A RETRAVAILLER
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['owner'] = None
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['additionDate'] = None
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['lastUpdate'] = None
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['editPermission'] = None
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['validated'] = None
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['homepage_status'] = None
    # -----------------------------------------------------------------------------------------------------------------------

    biotools_file = "JSONresult/" + debian_entry['package'] + ".json"
    print(biotools_file) ##
    #json.dump(biotools_entry,open(biotools_file,'w'))
    print(biotools_entry) ##

    i += 1  # debug 10 lines
    #if i==10 : break    #debug 10 lines


print('\ndone!')

end_datetime=datetime.now()
announcement("start    : " + str(start_datetime))
announcement("end      : " + str(end_datetime))
announcement("duration : " + str(end_datetime-start_datetime))
fichier_log.close()