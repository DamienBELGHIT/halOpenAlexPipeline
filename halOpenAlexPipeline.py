import streamlit as st
import pandas as pd
import requests as rq
from json import JSONDecodeError 
from datetime import datetime
import re

#API GET Request architecture
def apiGET(urlGET):
    response = rq.get(urlGET)
    if response.status_code == 200:
        print("Success: "+urlGET)
        try:
            return response.json()
        except (JSONDecodeError):
            print("Error: "+ "Not Jsonifiable")
    else:
        print(f"Failed to retrieve data. Status code: {response.status_code}")

#Return OpenAlex API response
def getOAResults(url):
    result = apiGET(url)
    if result and len(result["results"]):
        return result["results"]
    else:
        return -1

#Return 1st id of OpenAlex API responses
def getOAIDs(url):
    result = getOAResults(url)
    if result != -1:
        oa_ids = []
        for cur_author in result:
            oa_ids.append(cur_author['id'].split("/")[-1])
        return oa_ids
    else:
        return -1
    

#Find OpenAlex works not stored in Hal and store the DOIs
def findUniqueWorks(hal, openalex):
    #Récupération des index avec des hal ids identiques
    uniqueDois = []
    halIDs = [publi['docid'] for publi in hal]
    halIDsOA = []

    locationsOA = [publi['locations'] for publi in openalex]
    for locations in locationsOA:
        curhalIDs = []
        for location in locations:
            curhalIDs.append(location['landing_page_url'])
        halIDsOA.append(curhalIDs)

        indexPairs = []
        i = 0
    for id in halIDs:
        ioa = 0
        for idOA in halIDsOA:
            if str(id) in str(idOA):
                indexPairs.append(str(ioa)+"/"+str(i))
                break
            ioa+=1
        i+=1
    st.write("Nombre de publications HAL présentes dans OpenAlex: "+str(len(indexPairs))+"/"+str(len(halIDs))) 
    with st.expander("Voir les publications HAL trouvées"):
        publisHalDF = []
        i=0
        for publiHal in hal:
            publisHalDF.append({"in_OpenAlex":False, "label": publiHal["label_s"], "uri": publiHal["uri_s"], "docid": publiHal['docid']})
            i+=1
        for indexPair in indexPairs:
            publisHalDF[int(indexPair.split("/")[1])]["in_OpenAlex"] = True
        df = pd.DataFrame(publisHalDF, columns=["in_OpenAlex", "label", "uri", "docid"])
        st.dataframe(df)
    st.write("Nombre de publications OpenAlex uniques: "+str(len(openalex)-len(indexPairs))+"/"+str(len(halIDsOA)))
    with st.expander("Voir les publications OpenAlex trouvées"):
        publisOADF = []
        i=0
        for publiOA in openalex:
            publisOADF.append({"in_Hal":False, "id": publiOA['id']})
            i+=1
        for indexPair in indexPairs:
            publisOADF[int(indexPair.split("/")[0])]["in_Hal"] = True
        df = pd.DataFrame(publisOADF, columns=["in_Hal", "id"])
        st.dataframe(df)
    
    #Get list of DOIs from unique works in OpenAlex
    indexToDelete = []
    for indexPair in indexPairs:
        indexToDelete.append(int(indexPair.split("/")[0]))
    uniquePublisOA = publisOpenAlex.copy()
    for index in sorted(indexToDelete, reverse=True):
        del uniquePublisOA[index]

    noDoiDF = []
    for publi in uniquePublisOA:
        if publi['doi']:
            uniqueDois.append(publi['doi'])
        else:
            noDoiDF.append(publi)
    st.session_state.uniqueDois = uniqueDois
    st.write("Nombre de DOIs trouvés: "+ str(len(uniqueDois)) + "/" + str(len(uniquePublisOA)))
    with st.expander("Voir les publications OpenAlex uniques sans DOI"):
        df = pd.DataFrame(noDoiDF, columns=["id"])
        st.table(df)


UbsOaID = "i2802204017"
if 'authorIDs' not in st.session_state:
    st.session_state.authorIDs = []

if 'uniqueDois' not in st.session_state:
    st.session_state.uniqueDois = []

if 'bibTeXs' not in st.session_state:
    st.session_state.bibTeXs = ""

findWorksBtn = False
writeBibTeXBtn = False
downloadFilesBtn = False

st.title("Comparateur Hal OpenAlex")
st.markdown(
    """ 
    Trouve les publications de OpenAlex non présentes dans Hal et les store dans des fichiers BibTeX téléchargeables.
    """
)

left, mid1, mid2, right = st.columns([9, 3, 4, 4])
curYear = int(datetime.today().strftime('%Y'))
with mid2:
    st.number_input("Année de début", min_value=1900, max_value=curYear, key="yearStart", value=2010)
with right:
    st.number_input("Année de fin", min_value=1900, max_value=curYear, key="yearEnd", value=curYear)

with left:
    st.text_input("*Nom de l'institution", key="institution", placeholder="Institut de Recherche Dupuy de Lôme")
with mid1:
    st.text_input("Sigle Hal", key="halInstitutionCode", placeholder="IRDL")

st.text_input("*Nom des chercheurs (séparés par ',')", key="authors", placeholder="le goff, BOSSARD, Jean Dupont")
st.text_input("Discipline", key="domain", placeholder="")

if st.session_state.institution != "" and st.session_state.authors != "":
    institution = st.session_state.institution
    authors = [item.strip() for item in st.session_state.authors.split(",")]
    if st.button("Vérifier les informations", key="findInfos"):
        st.session_state.authorIDs = []
        st.session_state.authorHALIDs = []
        st.session_state.uniqueDois = []
        st.session_state.bibTeXs = ""
        #Get institution OpenAlex ID
        url = "https://api.openalex.org/institutions?search="+institution
        institutions = getOAResults(url)
        institutionID = -1
        if institutions != -1:
            for institution in institutions:
                for parent_institution in institution["associated_institutions"]:
                    if parent_institution["display_name"] == "Université de Bretagne Sud":
                        institutionID = institution["id"].split("/")[-1]
                        break
                if institutionID != -1:
                    break
        if institutionID != -1:
            st.session_state.institutionOAID = institutionID
            st.write("Institution trouvée dans OpenAlex: https://openalex.org/institutions/" + institutionID)
            found = False
            
            #Get institution Hal
            if st.session_state.halInstitutionCode != "":
                institution = st.session_state.halInstitutionCode.upper() 
                url = "https://api.archives-ouvertes.fr/search/"+institution+"/"
                response = apiGET(url)
                if response and "response" in response and len(response["response"]):
                    st.session_state.institutionHALID = institution
                    st.write("Institution trouvée dans Hal: ", institution)
                    found = True
                else:
                    st.markdown(":red[Erreur: Sigle Hal incorrect]")
            else:
                url = "https://api.archives-ouvertes.fr/ref/structure/?q="+institution
                #"https://api.archives-ouvertes.fr/search/"+institution+"/"
                response = apiGET(url)
                if "response" in response and len(response["response"]):
                    halInstitution = response["response"]['docs'][0]
                    for doc in response["response"]["docs"]:
                        if ("["+ institution.upper() +"]") in doc['label_s']:
                            halInstitution = doc
                            found = True
                            break
                    if not found:
                        if "[" in halInstitution['label_s']:
                            found = True
                        else:
                            i = 1
                            while "[" not in halInstitution['label_s'] and i < len(response["response"]['docs']):
                                halInstitution = response["response"]['docs'][i]
                                found = True
                                i += 1
                if found:
                    st.session_state.institutionHALID = halInstitution['label_s'].split("[")[-1].replace("]", "").split("-")[0].strip()
                    #st.session_state.institutionHALID = institution.upper()
                    st.write("Institution trouvée dans Hal: ", halInstitution['label_s'])
            if found:
                institutionHALID = st.session_state.institutionHALID
                authorIDs =[] 
                #Get authors HalIDs:
                for author in authors:
                    url = "https://api.archives-ouvertes.fr/search/"+institutionHALID+"/?q="+author
                    result = apiGET(url)
                    if result["response"]["numFound"] > 0:
                        st.write("Chercheur trouvé dans Hal "+ institutionHALID +": "+ author )
                    else:
                        st.markdown(":red[Chercheur non trouvé dans Hal "+ institutionHALID  +"]: "+ author)
                #Get authors OpenAlex IDs
                nb_authors_found = 0
                for author in authors:
                    result = []
                    url = "https://api.openalex.org/authors?filter=last_known_institutions.id%3A"+institutionID+",default.search%3A\""+author+"\""
                    cur_authors = getOAIDs(url)
                    if cur_authors != -1:
                        result.extend(cur_authors)
                    url = "https://api.openalex.org/authors?filter=affiliations.institution.id%3A"+institutionID+",default.search%3A\""+author+"\""
                    cur_authors = getOAIDs(url)
                    if cur_authors != -1:
                        result.extend(cur_authors)
                    if len(result) == 0:
                        url = "https://api.openalex.org/authors?filter=affiliations.institution.id%3A"+UbsOaID+",default.search%3A\""+author+"\""
                        result = getOAIDs(url)
                    result = list(dict.fromkeys(result))
                    if len(result) > 0:
                        nb_authors_found += 1
                        for cur_oa_id in result:
                            authorIDs.append(cur_oa_id)
                            st.write("Chercheur trouvé dans OpenAlex: "+ author + " https://openalex.org/authors/"+cur_oa_id)
                    else:
                        st.markdown(":red[Chercheur non trouvé dans OpenAlex]: "+ author)

                if (len(authorIDs) > 0):
                    st.session_state.authorIDs = authorIDs
                    st.write("Chercheurs trouvés dans OpenAlex: "+ str(nb_authors_found) + "/" + str(len(authors)))
                else:
                    st.markdown(":red[Erreur: Aucun chercheur trouvé dans OpenAlex]")
            else:
                st.markdown(":red[Erreur: Institution non trouvée dans Hal]")
        else:
            st.markdown(":red[Erreur: Institution non trouvée dans OpenAlex]")

if (len(st.session_state.authorIDs) > 0):
    findWorksBtn = st.button("Trouver les publications uniques", key="findWorks")

if findWorksBtn:
    yearStart = st.session_state.yearStart
    yearEnd = st.session_state.yearEnd
    authorIDs = st.session_state.authorIDs
    params = ""
    for author in authors:
        params += author
        if author != authors[len(authors)-1]:
            params += " OR "
    perPageNb = 200
    curPage = 0
    publisHal = []
    while len(publisHal) == curPage*perPageNb:
        url = "https://api.archives-ouvertes.fr/search/"+st.session_state.institutionHALID+"/?q=("+ params+")&fq=submittedDateY_i:["+ str(yearStart) + " TO " + str(yearEnd) +"]"+"&start="+str(curPage*perPageNb)+"&rows="+str(perPageNb)
        curPage+=1
        publisHal += apiGET(url)["response"]["docs"]
    if (len(publisHal) > 0):
        st.write("Publications Hal trouvées: "+str(len(publisHal)))
    else:
        st.markdown(":red[Aucune publication Hal trouvée]")
    params = ""
    for authorID in authorIDs:
        params += "\""+ authorID + "\""
        if authorID != authorIDs[-1]:
            params += "|"
    perPageNb = 200
    curPage = 0
    publisOpenAlex = []
    while len(publisOpenAlex) == curPage*perPageNb:
        curPage += 1
        #",authorships.institutions.id:"+UbsOaID+"|"+st.session_state.institutionOAID+
        url = "https://api.openalex.org/works?filter=authorships.author.id:"+params+",publication_year:"+str(yearStart)+"-"+str(yearEnd)+"&per-page="+str(perPageNb)+"&page="+str(curPage)
        publisOpenAlex += apiGET(url)["results"]
    if (len(publisOpenAlex) > 0):
        st.write("Publications OpenAlex trouvées: "+str(len(publisOpenAlex)))
        findUniqueWorks(publisHal, publisOpenAlex)
    else:
        st.markdown(":red[Erreur: Aucune publication OpenAlex trouvée]")

if (len(st.session_state.uniqueDois) > 0):
    writeBibTeXBtn = st.button("Générer les données BibTeX", key="writeBibTeX")

if writeBibTeXBtn: 
    st.session_state.bibTeXs = ""
    uniqueDois = st.session_state.uniqueDois
    #Needed Dependencies
    import urllib.request
    import bibtexparser
    from urllib.request import HTTPError
    
    def doiToBib(doi):
        BASE_URL = 'http://dx.doi.org/'
        url = BASE_URL + doi
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/x-bibtex')
        try:
            with urllib.request.urlopen(req) as f:
                bibtex = f.read().decode()
                # The round-trip through bibtexparser adds line endings.
                bibtex = bibtexparser.loads(bibtex)
                bibtex = bibtexparser.dumps(bibtex)
            if st.session_state.domain:
                bibtex = bibtex.split(",")[0] + ",\n domain={" +st.session_state.domain+ "}," + bibtex.partition(",")[2]
            url = f"https://api.crossref.org/works/{doi}"
            response = apiGET(url)
            if response and "message" in response: 
                abstract = apiGET(url)['message'].get('abstract', False)
                if abstract:
                    abstract = re.sub('<.*?>', '', abstract)
                    bibtex = bibtex.split(",")[0] + ",\n abstract={" +abstract+ "}," + bibtex.partition(",")[2]
            return bibtex
        except HTTPError as e:
            if e.code == 404:
                st.markdown(':red[DOI non trouvé: ]', doi)
            else:
                st.markdown(':red[Erreur: Service DoiToBib non disponible.]')
    bibTeXs = []
    for uniqueDoi in uniqueDois:
        bibtex = doiToBib(uniqueDoi)
        bibTeXs.append(bibtex)
        st.write(bibtex)
    st.session_state.bibTeXs = bibTeXs

def listToStr(list):
    result = ""
    for s in list:
        result += s
    return result

if (len(st.session_state.bibTeXs) > 0):
    nbEntries = 50
    downloadFilesBtn = st.container()
    with downloadFilesBtn:
        i = 0
        for i in range(int(len(st.session_state.bibTeXs)/nbEntries)+1):
            st.download_button(("Télécharger fichier BibTeX " + str(i*nbEntries) + "-" + str(i*nbEntries+nbEntries)), 
                key="downloadFiles"+str(i), 
                data=listToStr(st.session_state.bibTeXs[i*nbEntries:min(i*nbEntries+nbEntries, len(st.session_state.bibTeXs))]),
                file_name="bibTeXs"+st.session_state.institutionHALID +".txt",
                type="primary",
                icon=":material/download:")