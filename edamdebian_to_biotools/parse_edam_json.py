import json
import requests
from owlready2 import *
from datetime import datetime
import re
import dictdiffer
import copy

############ File : edam.json ####
# File created with edam.sh script
# from Andreas Tille (member of
# the debian team)
# https://salsa.debian.org/blends-team/website/blob/master/misc/sql/edam.sh
print('loading debian data, please wait...')
debian_med_metadata = json.load(open('edam.json'))

############ File : biotools.json ####
print('loading bio.tools data, please wait...')
biotools_list = json.load(open('biotools.json'))

############ File : EDAM_1.21.xrdf ####
# File with the last EDAM ontology
# V1.21 Released on 07/31/2018
onto = get_ontology("EDAM_1.21.xrdf")
onto.load()

############ File : Log.txt ####
# File that show problems on
# Debian EDAM structure
fichier_log = open("Log.txt", "w")
fichier_log.write("/!\(1) EDAM operation not find on edam onthology\n"
                  "/!\(2) Bad typo for the function in edam.json\n"
                  "/!\(3) Bad typo for the topic in edam.json\n"
                  "/!\(4) Problem on DOI format\n"
                  "/!\(5) DOi unrecognized\n"
                  "/!\(6) Two entry of the package on edam.json\n"
                  "/!\(7) Biotools ID on edam.json but no correspondance on bio.tools\n"
                  "__________________________________________________________________\n\n")

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
    fichier_log.write(text+"\n")

############ Functions search_owl () ####
# Search an uri from EDAM ontology file
# in a specified category
def search_owl(entry,debian_entry,category):
    operation = dict(uri=None, term=None)
    myonto = onto.search_one(label=entry,iri="*"+category+"*")
    if not myonto:
        announcement("\n/!\(1) package \"" + debian_entry['package'] + "\", no EDAM " + category +" for \"" + entry + "\" on http://bioportal.bioontology.org/ontologies/EDAM version 1.21")
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
                    announcement("\n/!\(2) package \"" + debian_entry['package'] + "\", the function \"" + function_entry + "\" is written as a character string and not as a table, in the edam.json, it should look like this \" 'function': ['" + function_entry + "'] \"")
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
            announcement("\n/!\(3) package \"" + debian_entry['package'] + "\", the Topic\"" + topics_entry + " is written as a character string and not as a table in the edam.json, it should look like this \" 'topic': ['" + topics_entry + "'] \"")
            biotools_topics.append(search_owl(topics_entry, debian_entry,"topic"))
    return biotools_topics

############ Functions search_publication() ####
# Search pulication metadata from a doi
def search_publication(debian_entry):
    if(is_setted('doi',debian_entry)):
        doi = debian_entry['doi']
        m = re.search("(?P<excess>.*doi[^/:]*[\/:])(?P<doi>\d+.*$)", doi)
        if m is not None:
            newdoi=m.group('doi')
            excess=m.group('excess')
            announcement("\n/!\(4) package \"" + debian_entry['package'] + "\", in edam.json the doi \"" + doi + "\" can't be composed of the prefix \"" + excess + " \". It should be like: \"" + newdoi + "\"")
            doi=newdoi
        authors_list = []
        metadata = dict(title="", abstract="", date="", citationCount="", authors=authors_list, journal="")
        publication = dict(doi=doi, pmid=None, pmcid=None, type=None, version=None, metadata=metadata)
        publi = requests.get("https://doi.org/"+doi, headers={'Accept': 'application/vnd.citationstyles.csl+json'})
        if (publi.status_code != 200):
            announcement("\n/!\(5) package \"" + debian_entry['package'] + "\", in edam.json the doi :\"" + doi + "\" is not recognized by doi.org")
            return None
        publi_json = publi.json()
        publication['type'] = get_value('type', publi_json)  # type
        metadata['title'] = get_value('title', publi_json)  # metadata.title
        metadata['abstract'] = get_value('abstract', publi_json) # metadata.abstract
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
        return [publication]
    else:
        return []

############ Functions search_duplicate() ####
# Search duplicate package entry
def search_duplicate(debian_entry,seen,double):
    package=get_value('package', debian_entry)
    if package not in seen:
        seen.add(package)
    else:
        announcement("\n/!\(6) package \"" + debian_entry['package'] + "\", has two entry into edam.json. Here are the difference")
        double.append(package)
        second_entry=debian_entry
        first_entry = None
        for debian_entry2 in debian_med_metadata:
            if get_value('package', debian_entry2) == package :
                first_entry = debian_entry2
                break
        for diff in list(dictdiffer.diff(first_entry, second_entry)):
                announcement("-In '"+str(diff[1])+"' :"+str(diff[2]))
    return seen,double

############ Functions check_on_biotools() ####
def check_on_biotools(debianbt_entry,biotools_list):
    db_biotoolsID=get_value('biotoolsID', debianbt_entry)
    db_package=get_value('name', debianbt_entry)
    if db_biotoolsID != None:
        for biotools_entry in biotools_list:
            if biotools_entry['biotoolsID'].lower() == db_biotoolsID.lower():
                print("Debian BiotoolsID exist on Biotools")
                print("bt_orig :" + biotools_entry['biotoolsID'] +" | db_btid :" + db_biotoolsID +" | db_pckg :" + db_package)
                return(biotools_entry)
        announcement("\n/!\(7) package \"" + db_package + "\", has an BiotoolsID (\'" + db_biotoolsID + "\')  but where not found in Biotools.")
        return("notfound")
    elif db_package != None:
        for biotools_entry in biotools_list:
            if biotools_entry['biotoolsID'].lower() == db_package.lower():
                print("Debian entry exist on Biotools but don't have BiotoolsID")
                print("bt_orig :" + biotools_entry['biotoolsID'] + " | db_pckg :" + db_package)
                return(biotools_entry)
        print("No Biotools entry where found for this package name, creation of a new entry:")

############ Functions compare_with_bt() ####
def compare_with_bt(debianbt_entry,biotools_entry,biotools_list):
    biotoolexist=check_on_biotools(biotools_entry,biotools_list)
    if biotoolexist != None and biotoolexist != "notfound":
        bool_add = False
        list_change = ("|Modif| \t\t|Label|\t\t|Bio.tools / Debian|\n")
        NEW_entry = copy.deepcopy(biotoolexist)
        for diff in list(dictdiffer.diff(biotoolexist,biotools_entry)):
                if (str(diff[0]) == "add"):                                                                         # Pour prendre en compte les ajouts MAIS PAS LES MODIFS......
                    if (re.search("authors", str(diff[1])) != None): #Ne prend pas les différences d'auteurs trouvés par dictdiffer
                        continue
                    bool_add=True
                    print("|Modif| \t\t|Label|\t\t|Bio.tools / Debian|")
                    print(str(diff[0])+"\t\t'"+str(diff[1])+"'\t\t:"+str(diff[2]))
                    list_change+=(str(diff[0])+"\t\t'"+str(diff[1])+"'\t\t:"+str(diff[2]) + "\n")
                    diff_tab=re.sub('[[\]\'\s]', '', str(diff[1])).split(',')
                    diff_tab.append(None)

                    if (diff_tab[0] != None): #Recursif?
                        if (diff_tab[1] != None):
                            if (diff_tab[2] != None):
                                NEW_entry[diff_tab[0]][int(diff_tab[1])][diff_tab[2]]=biotools_entry[diff_tab[0]][int(diff_tab[1])][diff_tab[2]]
                            else:
                                NEW_entry[diff_tab[0]][int(diff_tab[1])] = biotools_entry[diff_tab[0]][int(diff_tab[1])]
                        else:
                            NEW_entry[diff[1]]=biotools_entry[diff[1]]

        biotools_entry=NEW_entry  #Ne prend pas en compte les changements, juste les ajout
        biotool_exist_list.append(biotoolexist)
        if(bool_add):
            biotool_modif_list.append(biotools_entry)
            biotools_file = "NEWresult/Modif_" + debianbt_entry['package'] + ".json"
            biotools_file_change_name = "NEWresult/Modif_" + debianbt_entry['package'] + "_log.txt"
            biotools_file_change = open(biotools_file_change_name, "w")
            biotools_file_change.write("\nChanges:\n" +list_change)
            biotools_file_change.write("\nOrigin :\n" + str(biotoolexist))
            biotools_file_change.write("\nChanged:\n" + str(biotools_entry))
            if(is_setted('bio.tools', debianbt_entry)):
                biotools_file_change.write("\n\n(?) Link was made using the biotoolsIDs: DB: " + get_value('bio.tools', debianbt_entry) + " BT: " + get_value('biotoolsID', biotoolexist))
            else:
                biotools_file_change.write("\n\n(?) Link was made between the package name " + get_value('package', debianbt_entry) + " and the entry name on biotools: " + get_value('biotoolsID', biotoolexist))
            biotools_file_change.close()
            print("Debian entry have value (listed before) that we can we can add to the corresponding biotools entry. See the corresponding log file "+ biotools_file_change_name +" and the json file created:")
            return (biotools_file, debianbt_entry)
        else:
            print("No added value from debian entry, we keep the biotools entry with no change (No file will be created)")
            biotool_keep_list.append(biotoolexist)
            print("bt:    " + str(biotools_entry))
            return ("keepbt", biotools_entry)
    elif biotoolexist == "notfound":
        biotool_notfound_list.append(biotools_entry)
        biotools_file = "NEWresult/NOTFOUND_" + debianbt_entry['package'] + ".json"
        return(biotools_file, debianbt_entry)
    else: # Si l'outil n'a pas d'entrée dans biotools
        biotool_new_list.append(biotools_entry)
        biotools_file = "NEWresult/NEW_" + debianbt_entry['package'] + ".json"
        return(biotools_file, debianbt_entry)

############ Functions create_new_bt_file() ####
def create_new_bt_file(debianbt_entry,biotools_entry,biotools_list):
    biotools_file,biotools_entry=compare_with_bt(debianbt_entry,biotools_entry,biotools_list)
    if(biotools_file!="keepbt"):
        print(biotools_file)
        json.dump(biotools_entry, open(biotools_file, 'w'))


#################################################################################
# START

# tables to search duplicate package entry
package_seen = set()
package_double = []
biotool_exist_list = []
biotool_new_list = []
biotool_modif_list = []
biotool_keep_list = []
biotool_notfound_list = []

# to see processing time
start_datetime=datetime.now()
print(str(start_datetime))
print('Starting analyses, please wait...\n')

i=0 #debug 10 lines

for debianbt_entry in debian_med_metadata:

    # if i<860  :#debug pass X lines
    #     print(get_value('doi',debian_entry))
    #     i += 1
    #     continue

    # -----------------------------------------------------------------------------------------------------------------------
    package_seen, package_double = search_duplicate(debianbt_entry, package_seen, package_double)
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry = dict(name='', description='', homepage='', biotoolsID='', biotoolsCURIE='', version=[], otherID=[],
                          function=[], toolType=[], topic=[], operatingSystem=[], language=[], license='',
                          collectionID=[], maturity='', cost='', accessibility=[], elixirPlatform=[], elixirNode=[],
                          link=[], download=[], documentation=[], publication=[], credit=[], owner='', additionDate='',
                          lastUpdate='', editPermission=None, validated='', homepage_status='')
    #-----------------------------------------------------------------------------------------------------------------------
    biotools_entry['name'] = get_value('package', debianbt_entry)
    print("\n|"+ str(i+1) + " " + biotools_entry['name'])
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['description'] = get_value('description', debianbt_entry)
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['homepage'] = get_value('homepage', debianbt_entry)
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['biotoolsID'] = get_value('bio.tools', debianbt_entry)
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['biotoolsCURIE'] = None
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['version'] = get_value('version', debianbt_entry)
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['otherID'] = []  # debian_entry['']  ????
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['function'] = search_function(debianbt_entry)
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['toolType'] = [] # debian_entry[''] ???
    # -----------------------------------------------------------------------------------------------------------------------
    biotools_entry['topic'] = search_topic(debianbt_entry)
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
    biotools_entry['publication'] = search_publication(debianbt_entry)
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
    biotools_entry['elixir_badge'] = None
    # -----------------------------------------------------------------------------------------------------------------------
    # -----------------------------------------------------------------------------------------------------------------------
    create_new_bt_file(debianbt_entry, biotools_entry, biotools_list)
    # -----------------------------------------------------------------------------------------------------------------------
    #------------------------------------------------------------------------------------------------------------------------

    # biotools_file = "JSONresult/" + debian_entry['package'] + ".json"
    # #json.dump(biotools_entry,open(biotools_file,'w'))
    # print(biotools_entry) ##

    i += 1  # debug 10 lines
    #if i==10 : break    #debug 10 lines


print('\ndone!')

print("Number debian entry:")
print(i)
print("Number biotools package exist:")
print(len(biotool_exist_list))
print("Number biotools package modified:")
print(len(biotool_modif_list))
print("Number new biotools package from debian:")
print(len(biotool_new_list))
print("Number of debian tools with biotoolsID but not found on Biotools:")
print(len(biotool_notfound_list))
print("Number of debian package seen two time in edam.json:")
print(len(package_double))


end_datetime=datetime.now()
announcement("\n" + str(i) + "packages")
announcement("\nstart    : " + str(start_datetime))
announcement("end      : " + str(end_datetime))
announcement("duration : " + str(end_datetime-start_datetime))
fichier_log.close()