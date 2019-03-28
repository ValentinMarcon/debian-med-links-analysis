# ##########################################################################
# IMPORT ###################################################################

import json
import requests
from owlready2 import get_ontology
from datetime import datetime
import re
import dictdiffer
import copy
import yaml

# ##########################################################################
# FILES ####################################################################

# -- File : From debian ----------------------------------------------------
# File created with PSQL request from Andreas Tille
# (member of the debian team)
print('loading debian data, please wait...')
# debian_med_metadata = json.load(open('edam.json'))
# debian_med_metadata = json.load(open('resultsSQLfile.json'))
debian_med_metadata = json.load(open('edamv2.json'))
# --------------------------------------------------------------------------


# -- File : From biotools --------------------------------------------------
# File created requesting all the web pages of bio.tools
print('loading bio.tools data, please wait...')
biotools_metadata_list = json.load(open('biotools.json'))
# --------------------------------------------------------------------------


# -- File : EDAM ontology --------------------------------------------------
# File with the last EDAM ontology
# V1.21 Released on 07/31/2018
onto = get_ontology("EDAM_1.21.xrdf")
onto.load()
# --------------------------------------------------------------------------


# -- File : Log.txt --------------------------------------------------------
# File that show problems on Debian EDAM structure
log_file = open("Log.txt", "w")
log_file.write("/!\\(1) EDAM operation not find on edam ontology\n"
               "/!\\(2) Bad typo for the function in edam.json\n"
               "/!\\(3) Bad typo for the topic in edam.json\n"
               "/!\\(4) Problem on DOI format\n"
               "/!\\(5) DOi unrecognized\n"
               "/!\\(6) Two entry of the package on edam.json\n"
               "/!\\(7) Biotools ID on edam.json but no correspondence on bio.tools\n"
               "/!\\(8) Debian package exist on Biotools but don't have BiotoolsID\n"
               "__________________________________________________________________\n\n")
# --------------------------------------------------------------------------

# ##########################################################################
# FUNCTIONS ################################################################

# -- Function is_set() --------------------------------------------------
# Check if an entry exist and is not empty on the json
def is_set(value, entry):
    if value in entry:
        return entry[value] is not None
    else:
        return False
# --------------------------------------------------------------------------


# -- Function get_value() --------------------------------------------------
# Return the value from a dict if it's exist
def get_value(value, entry):
    if is_set(value, entry):
        return entry[value]
    else:
        return None
# --------------------------------------------------------------------------


# -- Function advertisement() -----------------------------------------------
# Announce something on stdout and log.txt
def advertisement(text):
    print(text)
    log_file.write(text + "\n")
# --------------------------------------------------------------------------


# -- Function search_owl () ------------------------------------------------
# Search an uri from EDAM ontology file in a specified category
def search_owl(onto_term, debian_entry, onto_category):
    operation = dict(term=None, uri=None)
    my_onto = onto.search_one(label=onto_term, iri="*" + onto_category + "*")
    if not my_onto:
        advertisement("\n/!\\(1) package \"" + debian_entry['package']
                      + "\", no EDAM " + onto_category + " for \"" + onto_term
                      + "\" found on http://bioportal.bioontology.org/ontologies/EDAM version 1.21")
    else:
        operation['term'] = onto_term
        operation['uri'] = my_onto.iri
        return operation
# --------------------------------------------------------------------------


# -- Function search_input_output() ----------------------------------------
# Search on debian entry "data" and "format" value
# for the input or the output
def search_input_output(debian_entry, debian_edam_entry, element):
    # 'element' = "input" or "output"
    tab_in_out = []
    if is_set(element, debian_edam_entry):
        db_value_ins_outs = get_value(element, debian_edam_entry)
        for db_value_in_out in db_value_ins_outs:
            # 1) get the format(s) of the of the input/output
            format_term_tab = get_value("formats", db_value_in_out)
            format_tab = []
            if format_term_tab is None:
                advertisement("\n/!\\(2.1) package \"" + debian_entry['package']
                              + "\", the " + element + " \"" + str(db_value_in_out)
                              + "\" is unrecognized "
                              + "(maybe its written 'format' instead of 'formats'?)")
            else:
                for format_term in format_term_tab:
                    format_value = search_owl(format_term, debian_entry, "format")
                    if format_value is not None:
                        format_tab.append(format_value)
            # 2) get the data term (=name) of the input/output
            data_term = get_value("data", db_value_in_out)
            data_value = search_owl(data_term, debian_entry, "data")
            # 3) write the data and format on the input/output dict
            if data_value is not None:
                in_out = dict(data=data_value, format=format_tab)
                tab_in_out.append(in_out)
    return tab_in_out
# --------------------------------------------------------------------------


# -- Function search_function() --------------------------------------------
# Search a function URI from EDAM 1.21
# ==> See search_owl()
def search_function(debian_entry):
    biotools_functions = []
    if is_set("edam_scopes", debian_entry):
        for debian_edam_entry in debian_entry['edam_scopes']:
            biotools_function = dict(operation=[], input=[], output=[], note=None, cmd=None)
            if is_set('function', debian_edam_entry):
                # -- Operation ---------------------------------------------
                operation_tab = []
                if isinstance(debian_edam_entry['function'], list):
                    for function_entry in debian_edam_entry['function']:
                        operation = search_owl(function_entry, debian_entry, "operation")
                        if operation is not None:
                            operation_tab.append(operation)
                else:
                    function_entry = get_value("function", debian_edam_entry)
                    # the field "function" need to be written as a list
                    advertisement("\n/!\\(2.0) package \"" + debian_entry['package']
                                  + "\", the function \"" + function_entry
                                  + "\" is written as a character string and not as a table, in the edam.json,"
                                  + " it should look like this \" 'function': ['" + function_entry + "'] \"")
                    operation = search_owl(function_entry, debian_entry, "operation")
                    if operation is not None:
                        operation_tab.append(operation)
                biotools_function['operation'] = operation_tab
                # -- Input -------------------------------------------------
                biotools_function['input'] = search_input_output(debian_entry, debian_edam_entry, "inputs")
                # -- Output ------------------------------------------------
                biotools_function['output'] = search_input_output(debian_entry, debian_edam_entry, "outputs")
                # ----------------------------------------------------------
            biotools_functions.append(biotools_function)
    return biotools_functions
# --------------------------------------------------------------------------


# -- Function search_topic() -----------------------------------------------
# Search a topic URI from EDAM 1.21
# ==> See search_owl()
def search_topic(debian_entry):
    biotools_topics = []
    if is_set("topics", debian_entry):
        if isinstance(debian_entry['topics'], list):
            for topics_entry in debian_entry['topics']:
                biotools_topics.append(search_owl(topics_entry, debian_entry, "topic"))
        else:
            topics_entry = debian_entry['topics']
            biotools_topics.append(search_owl(topics_entry, debian_entry, "topic"))
            # the field "topics" need to be written as a list
            advertisement("\n/!\\(3) package \"" + debian_entry['package']
                          + "\", the Topic\"" + topics_entry
                          + " is written as a character string and not as a list in the edam.json,"
                          + " it should look like this \" 'topic': ['" + topics_entry + "'] \"")
    return biotools_topics
# --------------------------------------------------------------------------


# -- Function search_publication() -----------------------------------------
# Search publication metadata from a doi
def search_publication(debian_entry):
    if is_set('doi', debian_entry):
        doi = debian_entry['doi']
        # Check if the DOI is well written
        # noinspection PyPep8
        m = re.search("(?P<excess>.*doi[^/:]*[/:])(?P<doi>\d+.*$)", doi)
        if m is not None:
            new_doi = m.group('doi')
            excess = m.group('excess')
            advertisement("\n/!\\(4) package \"" + debian_entry['package'] + "\", in edam.json the doi \""
                          + doi + "\" can't be composed of the prefix \"" + excess
                          + " \". It should be like: \"" + new_doi + "\"")
            doi = new_doi
        authors_list = []
        metadata = dict(title="", abstract="", date="", citationCount="", authors=authors_list, journal="")
        publication = dict(doi=doi, pmid=None, pmcid=None, type=None, version=None, metadata=metadata)
        publi_from_doi = requests.get("https://doi.org/" + doi,
                                      headers={'Accept': 'application/vnd.citationstyles.csl+json'})
        # If the DOI is not found/recognized on doi.org
        if publi_from_doi.status_code != 200:
            advertisement("\n/!\\(5) package \"" + debian_entry['package']
                          + "\", in edam.json the doi :\"" + doi + "\" is not recognized by doi.org")
            return None
        publi_json = publi_from_doi.json()

        # Fill the publication dict with all the data from doi.org
        publication['type'] = get_value('type', publi_json)
        metadata['title'] = get_value('title', publi_json)
        metadata['abstract'] = get_value('abstract', publi_json)
        if is_set('indexed', publi_json):
            metadata['date'] = get_value('date-time', publi_json['indexed'])
        metadata['citationCount'] = get_value('is-referenced-by-count', publi_json)
        if is_set('author', publi_json):
            for authors_entry in publi_json['author']:
                author = dict(name='')
                if is_set('family', authors_entry):
                    author['name'] = authors_entry['family'] + " " + authors_entry['given']
                    authors_list.append(author)
                elif is_set('literal', authors_entry):
                    # noinspection PyPep8
                    m = re.search("(?P<given>.*)\s(?P<family>.*)", authors_entry['literal'])
                    if m is not None:
                        author['name'] = m.group('family') + " " + m.group('given')
                        authors_list.append(author)
        metadata['authors'] = authors_list
        metadata['journal'] = get_value('container-title', publi_json)
        publication['metadata'] = metadata

        return [publication]
    else:
        return []
# --------------------------------------------------------------------------


# -- Function search_interface() -------------------------------------------
# Search the bio.tools "Tool type" from debian "interface" tag
def search_interface(debian_entry):
    interface = get_value('interface', debian_entry)
    if isinstance(interface, list):
        interface = interface[0]    # (If there is multiple value we keep the first)
    # Dict of the link between bt "Tool type" and db "interface"
    interface_link = {
        "commandline": ['Command-line tool'],
        "shell": ['Command-line tool'],
        "x11": ['Desktop application'],
        "3d": ['Desktop application'],
        "web": ['Web application']
    }
    return interface_link.get(interface, [])
# --------------------------------------------------------------------------


# -- Function search_duplicate() -------------------------------------------
# Search duplicate package entry
def search_duplicate(debian_entry, seen_list, duplicate_list):
    package = get_value('package', debian_entry)
# If package have not been seen : add it on the seen list
    if package not in seen_list:
        seen_list.add(package)
# Else, had the package to the duplicate package list
    else:
        duplicate_list.append(package)
        advertisement("\n/!\\(6) package \"" + debian_entry['package']
                      + "\", has two entry into edam.json. Here are the difference")
# And show the differences between the two entry
        second_entry = debian_entry
        first_entry = None
        # Search the first occurrence of the package
        for entry in debian_med_metadata:
            if get_value('package', entry) == package:
                first_entry = entry
                break
        # Announce all the differences
        for diff in list(dictdiffer.diff(first_entry, second_entry)):
            advertisement("-In '" + str(diff[1]) + "' :" + str(diff[2]))
    return seen_list, duplicate_list
# --------------------------------------------------------------------------


# -- Function check_on_biotools() ------------------------------------------
def check_on_biotools(debian_entry, biotools_list):
    db_biotools_id = get_value('biotoolsID', debian_entry)
    db_package = get_value('name', debian_entry)
    # If debian entry have a biotools ID we search it on biotools list
    if db_biotools_id is not None:
        for biotools_entry in biotools_list:
            if biotools_entry['biotoolsID'].lower() == db_biotools_id.lower():
                biotool_exist_list.append(biotools_entry)
                biotool_exist_with_bt_id_list.append(biotools_entry['biotoolsID'])
                print("Debian BiotoolsID exist on Biotools")
                print("bt_orig :" + biotools_entry[
                    'biotoolsID'] + " | db_bt_id :" + db_biotools_id + " | db_pckg :" + db_package)
                return biotools_entry
        # If we never enter the "if" above its because the package was not found on biotools
        advertisement("\n/!\\(7) package \"" + db_package + "\", has an BiotoolsID (\'"
                      + db_biotools_id + "\')  but where not found in Biotools.")
        return "not_found"
    # If debian entry do not have a biotools ID we search it on biotools with the package name
    elif db_package is not None:
        for biotools_entry in biotools_list:
            if biotools_entry['biotoolsID'].lower() == db_package.lower():
                biotool_exist_list.append(biotools_entry)
                advertisement("\n/!\\(8) Debian entry exist on Biotools but don't have BiotoolsID")
                advertisement("bt_orig :" + biotools_entry['biotoolsID'] + " | db_pckg :" + db_package)
                return biotools_entry
        # If we never enter the "if" above its because the package was not found on biotools
        print("No Biotools entry where found for this package name, creation of a new entry:")
# --------------------------------------------------------------------------


# -- Function compare_with_bt() --------------------------------------------
# Search if the entry created for biotools is new or add a value to an existing entry
# noinspection PyTypeChecker,PyPep8
def compare_with_bt(debian_entry, new_bt_entry, biotools_list):
    # Check on biotools_list if the debian entry exist on biotools
    existing_biotools_entry = check_on_biotools(new_bt_entry, biotools_list)
    # ---------------------------------------------
    # If the debian entry have a biotools ID and exist on bio.tools
    if existing_biotools_entry is not None and existing_biotools_entry != "not_found":
        bool_add = False
        list_change = "|Modif| \t\t|Label|\t\t|Bio.tools / Debian|\n"
        new_entry = copy.deepcopy(existing_biotools_entry)
        # Search the difference between the two entry
        for diff in list(dictdiffer.diff(existing_biotools_entry, new_bt_entry)):
            # In this case (:"add") we just manage differences that add a value to an existing biotools ID
            if str(diff[0]) == "add":
                # Do not manage authors diff
                if re.search("authors", str(diff[1])) is not None:
                    continue
                bool_add = True
                print("|Modif| \t\t|Label|\t\t|Bio.tools / Debian|")
                print(str(diff[0]) + "\t\t'" + str(diff[1]) + "'\t\t:" + str(diff[2]))
                list_change += (str(diff[0]) + "\t\t'" + str(diff[1]) + "'\t\t:" + str(diff[2]) + "\n")
                diff_tab = re.sub('[[\]\'\s]', '', str(diff[1])).split(',')
                # noinspection PyTypeChecker
                diff_tab.append(None)

                # #### Make it recursive ??
                new = []
                append = []
                if diff_tab[1] is not None:
                    if diff_tab[2] is not None:
                        if diff_tab[3] is not None:
                            if diff_tab[4] is not None:
                                if diff_tab[5] is not None:
                                    print("This case is not managed ...")
                                    exit(1)
                                else:
                                    new = new_entry[diff_tab[0]][int(diff_tab[1])][diff_tab[2]][int(diff_tab[3])][diff_tab[4]]
                                    append = new_bt_entry[diff_tab[0]][int(diff_tab[1])][diff_tab[2]][int(diff_tab[3])][diff_tab[4]]
                            else:
                                new = new_entry[diff_tab[0]][int(diff_tab[1])][diff_tab[2]][int(diff_tab[3])]
                                append = new_bt_entry[diff_tab[0]][int(diff_tab[1])][diff_tab[2]][int(diff_tab[3])]
                        else:
                            new = new_entry[diff_tab[0]][int(diff_tab[1])][diff_tab[2]]
                            append = new_bt_entry[diff_tab[0]][int(diff_tab[1])][diff_tab[2]]
                    else:
                        new = new_entry[diff_tab[0]][int(diff_tab[1])]
                        append = new_bt_entry[diff_tab[0]][int(diff_tab[1])]
                else:
                    new = new_entry[diff[1]]
                    append = new_bt_entry[diff[1]]
                if isinstance(append, list):
                    for a in append:
                        bool_append = True
                        if new:
                            # Be sure to not copy an existing value
                            for n in new:
                                if a == n:
                                    bool_append = False
                                    break

                        if bool_append:
                            new.append(a)
                else:
                    print("This case is not managed ...")
                    exit(1)
                # ##########################

        # "new" is linked to "new entry" so the change have been made in "new entry" too
        new_bt_entry = new_entry
        # Some logs:
        if bool_add:
            biotool_modif_list.append(new_bt_entry)
            biotools_file = "NEWresult/Modif_" + debian_entry['package'] + ".json"
            biotools_file_change_name = "NEWresult/Modif_" + debian_entry['package'] + "_log.txt"
            biotools_file_change = open(biotools_file_change_name, "w")
            biotools_file_change.write("\nChanges:\n" + list_change)
            biotools_file_change.write("\nOrigin :\n" + str(existing_biotools_entry))
            biotools_file_change.write("\nChanged:\n" + str(new_bt_entry))
            if is_set('bio.tools', debian_entry):
                biotools_file_change.write("\n\n(?) Link was made using the biotoolsIDs: DB: "
                                           + get_value('bio.tools', debian_entry) + " BT: "
                                           + get_value('biotoolsID', existing_biotools_entry))
            else:
                biotools_file_change.write("\n\n(?) Link was made between the package name "
                                           + get_value('package', debian_entry) + " and the entry name on biotools: "
                                           + get_value('biotoolsID', existing_biotools_entry))
            biotools_file_change.close()
            print("Debian entry have value (listed before) that we can add to the corresponding biotools entry. "
                  "See the corresponding log file " + biotools_file_change_name + " and the json file created:")
            return biotools_file, new_bt_entry
        else:
            print(
                "No added value from debian entry, we keep the biotools entry with no change "
                "(No file will be created)")
            biotool_keep_list.append(existing_biotools_entry)
            print("bt:    " + str(new_bt_entry))
            return "keep_bt_entry", new_bt_entry
    # ---------------------------------------------
    # If the debian entry have a biotools ID but have not been found in bio.tools
    elif existing_biotools_entry == "not_found":
        biotool_not_found_list.append(new_bt_entry)
        biotools_file = "NEWresult/NOTFOUND_" + debian_entry['package'] + ".json"
        return biotools_file, debian_entry
    # ---------------------------------------------
    # If the debian entry do not exist on biotools
    else:
        biotool_new_list.append(new_bt_entry)
        biotools_file = "NEWresult/NEW_" + debian_entry['package'] + ".json"
        return biotools_file, debian_entry
# --------------------------------------------------------------------------


# -- Function create_new_bt_file() -----------------------------------------
def create_new_bt_file(debian_entry, new_bt_entry, biotools_list):
    # Search if the entry created for biotools is new or add a value to an existing entry
    biotools_file, biotools_entry = compare_with_bt(debian_entry, new_bt_entry, biotools_list)
    # If there is a interest to create a new entry or modify an entry on biotools
    if biotools_file != "keep_bt_entry":    # keep_bt_entry = keep the biotool entry, do not create a new one
        print(biotools_file)
        json.dump(biotools_entry, open(biotools_file, 'w'))
# --------------------------------------------------------------------------


# -- Function mapping_biotools_id() -----------------------------------------
# Search for biotools entry corresponding to the debian biotool ID
def mapping_biotools_id(debian_entry, biotools_list, mapping_list):
    db_biotools_id = get_value('bio.tools', debian_entry)
    db_package = get_value('package', debian_entry)
    # If debian entry have a "bio.tools" id
    if db_biotools_id is not None:
        # Search on the biotools_list the corresponding biotool entry
        for biotools_entry in biotools_list:
            bt_biotools_id = biotools_entry['biotoolsID']
            if bt_biotools_id.lower() == db_biotools_id.lower():
                # Create a table and append the packages found
                if not is_set(bt_biotools_id, mapping_list):
                    mapping_list[bt_biotools_id] = []
                mapping_list[bt_biotools_id].append(db_package)
    return mapping_list
# --------------------------------------------------------------------------


# -- Function create_yaml() ------------------------------------------------
# Write a list into a yaml
def create_yaml(filename, mapping_list):
    with open(filename, 'w') as f:
        yaml.dump(mapping_list, f)
# --------------------------------------------------------------------------

# ##########################################################################
# START ####################################################################

# --------------------------------------------------------------------------
# Tables to search duplicate package entry
package_seen = set()
package_double = []
# Mapping between bio.tools & debian
mapping = dict()
# Lists for stats
biotool_exist_list = []
biotool_exist_with_bt_id_list = []
biotool_new_list = []
biotool_modif_list = []
biotool_keep_list = []
biotool_not_found_list = []
prospective_package_list = []
# --------------------------------------------------------------------------
# Processing time
start_datetime = datetime.now()
print(str(start_datetime))
print('Starting analyses, please wait...\n')
# --------------------------------------------------------------------------

i = 0
for debian_med_entry in debian_med_metadata:
    i += 1

    # if i<630  :#debug pass X lines
    # #     print(get_value('doi',debian_entry))
    # #     i += 1
    #      continue
    # # if i == 100:
    # #     break

    # ----------------------------------------------------------------------
    print("\n|" + str(i) + " " + get_value('package', debian_med_entry))
    # ----------------------------------------------------------------------
    # Do not manage "prospective" debian packages
    if get_value('distribution', debian_med_entry) == "prospective":
        print("Debian entry is prospective package")
        prospective_package_list.append(debian_med_entry)
        continue
    # ----------------------------------------------------------------------
    # Map the link between bio.tools id and debian biotools ID
    mapping = mapping_biotools_id(debian_med_entry, biotools_metadata_list, mapping)
    # ----------------------------------------------------------------------
    # Search duplicate package entry
    package_seen, package_double = search_duplicate(debian_med_entry, package_seen, package_double)
    # ----------------------------------------------------------------------
    # Define necessary fields to create a biotool entry
    new_biotools_entry = dict(name='', description='', homepage='', biotoolsID='',
                              biotoolsCURIE='', version=[], otherID=[], function=[],
                              toolType=[], topic=[], operatingSystem=[], language=[],
                              license='', collectionID=[], maturity='', cost='',
                              accessibility=[], elixirPlatform=[], elixirNode=[],
                              link=[], download=[], documentation=[], publication=[],
                              credit=[], owner='', additionDate='', lastUpdate='',
                              editPermission=None, validated='', homepage_status='')
    # ----------------------------------------------------------------------
    new_biotools_entry['name'] = get_value('package', debian_med_entry)
    # ----------------------------------------------------------------------
    new_biotools_entry['description'] = get_value('description', debian_med_entry)
    # ----------------------------------------------------------------------
    new_biotools_entry['homepage'] = get_value('homepage', debian_med_entry)
    # ----------------------------------------------------------------------
    new_biotools_entry['biotoolsID'] = get_value('bio.tools', debian_med_entry)
    # ----------------------------------------------------------------------
    new_biotools_entry['biotoolsCURIE'] = None
    # ----------------------------------------------------------------------
    new_biotools_entry['version'] = get_value('version', debian_med_entry)
    # ----------------------------------------------------------------------
    new_biotools_entry['otherID'] = []
    # ----------------------------------------------------------------------
    new_biotools_entry['function'] = search_function(debian_med_entry)
    # ----------------------------------------------------------------------
    new_biotools_entry['toolType'] = search_interface(debian_med_entry)
    # ----------------------------------------------------------------------
    new_biotools_entry['topic'] = search_topic(debian_med_entry)
    # ----------------------------------------------------------------------
    new_biotools_entry['operatingSystem'] = ["Linux"]
    # ----------------------------------------------------------------------
    new_biotools_entry['language'] = get_value('compute_language', debian_med_entry)
    # ----------------------------------------------------------------------
    new_biotools_entry['license'] = None
    # ----------------------------------------------------------------------
    new_biotools_entry['collectionID'] = []
    # ----------------------------------------------------------------------
    new_biotools_entry['maturity'] = None
    # ----------------------------------------------------------------------
    new_biotools_entry['cost'] = None
    # ----------------------------------------------------------------------
    new_biotools_entry['accessibility'] = []
    # ----------------------------------------------------------------------
    new_biotools_entry['elixirPlatform'] = []
    # ----------------------------------------------------------------------
    new_biotools_entry['elixirNode'] = []
    # ----------------------------------------------------------------------
    new_biotools_entry['link'] = []
    # ----------------------------------------------------------------------
    new_biotools_entry['download'] = []
    # ----------------------------------------------------------------------
    new_biotools_entry['documentation'] = ""
    # ----------------------------------------------------------------------
    new_biotools_entry['publication'] = search_publication(debian_med_entry)
    # ----------------------------------------------------------------------
    new_biotools_entry['credit'] = ""
    # ----------------------------------------------------------------------
    new_biotools_entry['owner'] = None
    # ----------------------------------------------------------------------
    new_biotools_entry['additionDate'] = None
    # ----------------------------------------------------------------------
    new_biotools_entry['lastUpdate'] = None
    # ----------------------------------------------------------------------
    new_biotools_entry['editPermission'] = None
    # ----------------------------------------------------------------------
    new_biotools_entry['validated'] = None
    # ----------------------------------------------------------------------
    new_biotools_entry['homepage_status'] = None
    # ----------------------------------------------------------------------
    new_biotools_entry['elixir_badge'] = None
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    # Write the biotools entry dict into a file, according if it exist or
    # not and if its add an information to an existing entry
    create_new_bt_file(debian_med_entry, new_biotools_entry, biotools_metadata_list)
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------

    # if i==10 : break  #debug 10 lines


# --------------------------------------------------------------------------
# Create yaml file from mapping dict that make the ling between bio.tools
# package and debian bio.tools ID
create_yaml("Mapping_db_bt_draft.yaml", mapping)
# --------------------------------------------------------------------------

print('\ndone!')

# ##########################################################################
# SUMMARY ##################################################################

# ----------------------------------------------------------------------
advertisement("\nNumber of debian entry : " + str(len(debian_med_metadata)))
# ----------------------------------------------------------------------
print("Number of db package exist on biotools :", len(biotool_exist_list))
# ----------------------------------------------------------------------
print("Number of db package have a Biotool ID :", len(biotool_exist_with_bt_id_list))
# ----------------------------------------------------------------------
print("Number of db package with biotoolsID but not found on Biotools :", len(biotool_not_found_list))
# ----------------------------------------------------------------------
print("Number of new biotools package from debian :", len(biotool_new_list))
# ----------------------------------------------------------------------
print("Number of biotools package modified :", len(biotool_modif_list))
# ----------------------------------------------------------------------
print("Number of debian package seen two time in edam.json :", len(package_double))
# ----------------------------------------------------------------------
print("Number of package \"prospective\" :", len(prospective_package_list))
# ----------------------------------------------------------------------
end_datetime = datetime.now()
advertisement("\nstart    : " + str(start_datetime))
advertisement("end      : " + str(end_datetime))
advertisement("duration : " + str(end_datetime - start_datetime))
# ----------------------------------------------------------------------

log_file.close()
