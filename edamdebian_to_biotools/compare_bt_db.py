import json
from datetime import datetime
import time
import pandas
from pandas.io.json import json_normalize
pandas.set_option('display.max_columns', 100)
pandas.set_option('display.max_rows', 50)

############ File : edam.json ####
# from Andreas Tille (member of
# the debian team)
# https://salsa.debian.org/blends-team/website/blob/master/misc/sql/edam.sh
debian_med_metadata = json.load(open('edam.json'))


############ File : Log.txt ####
# File that show problems on
# Debian EDAM structure
fichier_log = open("Log_compare.txt", "w")

############ File : Merge.csv ####
fichier_merge = open("Merge.csv", "w")

############ Function is_set() ####
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

############ Function advertisement() ####
# Announce something on stdout and log.txt
def announcement(text):
    print(text)
    fichier_log.write(text+"\n")



#################################################################################
# START


start_datetime=datetime.now()
print(str(start_datetime))
# ## Créer fichier biotools.json depuis l'api biotools
# print('retrieving the bio.tools data, please wait...')
# biotools_list = []
# next_biotools_page = '?page=1'
# point="."
# unit="#"
# compte="0"
# while next_biotools_page is not None: #1814
#     page = requests.get('https://bio.tools/api/tool/?format=json&' + next_biotools_page[1:]).json()
#     biotools_list += page['list']
#     next_biotools_page = page.get('next',None)
#     compte += 1
#     print(str(compte)+point)
#     if (len(point)>50):
#         point = unit+"."
#         unit += "#"
#     else:
#         point += "."
# json.dump(biotools_list,open('biotools.json','w'))
# print('done!')
print()

info_util=dict(nb_ent_bt="", nb_ent_db="", nb_ent_filter="")


#### CHARGEMENT BIOOTOOLS.json ####
print('loading bio.tools data, please wait...')
biotools_list=json.load(open('biotools.json'))
biotools_df = json_normalize(biotools_list)
info_util["nb_ent_bt"]=len(biotools_df)
# print(biotools_df.columns)
# lowercase version of bio.tools ID in bio.tools dataframe
biotools_df['bt_id_lc'] = biotools_df['biotoolsID'].str.lower()
print('...')
time.sleep(1)
###########################################

#### CHARGEMENT edam.json ####
print('loading debian data, please wait...')
debian_df = pandas.read_json('edam.json', orient='values')
info_util["nb_ent_db"]=len(debian_df)
# lowercase version of debian ID in debian dataframe
debian_df['db_id_lc'] = debian_df['bio.tools'].str.lower()
# print(debian_df.columns)
print('...')
time.sleep(1)
###########################################

##### SEARCH doi from bio.tools dataframe
print('retrieving doi from biotools data, please wait...')
biotools_citation_df = list(biotools_df['publication'])
i=0
for line in  biotools_citation_df:
    if len(line) != 0:
        biotools_df.at[i,"doi_biotools" ] = line[0]['doi']
    i += 1
print('...')
time.sleep(1)
###########################################

##### TEST Hervé
#merged_df = biotools_df.merge(debian_df, how='right', left_on='bt_id_lc', right_on='db_id_lc', suffixes=('_biotools', '_debian'))
#merged_df = merged_df[['bio.tools','package','doi','publication']]
#merged_filtered_df=merged_df[merged_df.db_id_lc.notnull()][merged_df.biotoolsID.isnull()]
#print(merged_filtered_df)
#print(merged_filtered_df.shape[0])
#fichier_merge.write(str(merged_filtered_df)+"\n\n\n")


##### TEST Valentin
merged_df = biotools_df.merge(debian_df, how='right', left_on='bt_id_lc', right_on='db_id_lc', suffixes=('_biotools', '_debian'))
merged_df = merged_df[['bt_id_lc', 'db_id_lc', 'bio.tools','package','doi','publication','biotoolsID']]
merged_filtered_df=merged_df[merged_df.db_id_lc.notnull()][merged_df.biotoolsID.isnull()]
print(merged_filtered_df)
print(merged_filtered_df.shape[0])
fichier_merge.write(str(merged_filtered_df)+"\n\n\n")
info_util["nb_ent_filter"]=len(merged_filtered_df)
info_util["infos"]="Nombre d'entrée sur debian qui ont un biotoolsID non trouvé"

# ##### TEST de comparaison des Doi
# print('merging debian and bio.tools data, please wait...')
# print('...')
# print("Number of biotools entry (ALL & with DOI)")
# print(len(biotools_df))
# biotools_df = biotools_df[biotools_df.doi_biotools.notnull()]
# print(len(biotools_df))
# print("Number of debian entry (ALL & with DOI)")
# print(len(debian_df))
# debian_df =  debian_df[debian_df.doi.notnull()]
# print(len(debian_df))
# print('...')
# time.sleep(1)
# ## MERGE des df
# merged_df = biotools_df.merge(debian_df, how='inner', left_on='doi_biotools', right_on='doi', suffixes=('_biotools', '_debian'))
# print(merged_df.columns)
# print(len(merged_df))
# print('...')
# time.sleep(1)
# ## SELECTION des colomnes
# merged_df = merged_df[['bt_id_lc', 'db_id_lc','package','doi','doi_biotools', 'bio.tools','biotoolsID']]
# ## FILTRE des données
# merged_filtered_df=merged_df[merged_df.db_id_lc.isnull()]
# #merged_filtered_df=merged_df #nofilter
# #merged_filtered_df=merged_df[merged_df.biotoolsID.isnull()]  #### PAS DE RESULTAT
# print(len(merged_filtered_df))
# info_util["nb_ent_filter"]=len(merged_filtered_df)
# info_util["info"]="Nombre d'entrée sur debian qui ont un doi commun avec une entrée biotools mais le param bio.tools vide"
# ## ECRITURE
# fichier_merge.write(str(merged_filtered_df)+"\n\n\n")
# #print(merged_filtered_df)
# print(merged_filtered_df.shape[0])
# ###########################################

###########################################
print('########## Summary #########')
print(str(info_util))

end_datetime=datetime.now()
announcement("\nstart    : " + str(start_datetime))
announcement("end      : " + str(end_datetime))
announcement("duration : " + str(end_datetime-start_datetime))
print('###########################')
print()
# END
#################################################################################
