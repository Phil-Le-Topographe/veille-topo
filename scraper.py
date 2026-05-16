# -*- coding: utf-8 -*-
"""
MOTEUR UNIVERSAL DE SCRAPING ET DE SYNTHÈSE DOCUMENTAIRE XML
Destiné à l'hybridation des flux de veille technologique du BTS MGTMN.
Ce script automatise la conversion de pages HTML statiques en flux RSS standardisés.
"""

import os
import json
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
import urllib.parse

def initialiser_processus_scraping():
    """
    Orchestre le cycle de chargement de la configuration JSON et itère sur
    chaque cible pour commander la génération des flux de données locaux.
    """
    # Algorithme d'ouverture sécurisée du fichier de configuration des cibles
    if not os.path.exists("configuration_scraping.json"):
        print("Erreur critique : Le fichier de configuration JSON est introuvable.")
        return

    with open("configuration_scraping.json", "r", encoding="utf-8") as fichier_config:
        liste_cibles = json.load(fichier_config)

    # Entête de requête HTTP simulé (User-Agent) afin de contourner les dispositifs
    # de sécurité basiques anti-robot (WAF) mis en place par les hébergeurs des sites cibles.
    entetes_requete = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Boucle itérative principale de traitement sur l'ensemble des 14 sites de la liste
    for cible in liste_cibles:
        nom_source = cible["nom"]
        url_cible = cible["url"]
        print(f"Amorçage de la collecte documentaire sur la source : {nom_source}...")

        try:
            # Émission de la requête HTTP GET synchrone avec un timeout de sécurité de 15 secondes
            reponse = requests.get(url_cible, headers=entetes_requete, timeout=15)
            if reponse.status_code != 200:
                print(f"Échec de connexion sur {nom_source} (Code erreur HTTP: {reponse.status_code})")
                continue

            # Initialisation du parseur syntaxique HTML BeautifulSoup4
            parseur_html = BeautifulSoup(reponse.text, "html.parser")
            
            # Appel du sous-module d'analyse et d'extraction de données
            extraire_donnees_et_generer_xml(nom_source, url_cible, parseur_html, cible)

        except Exception as erreur_execution:
            print(f"Exception levée lors du traitement de la source {nom_source} : {str(erreur_execution)}")

def extraire_donnees_et_generer_xml(nom, url_racine, soupe_html, regles_css):
    """
    Analyse la structure géométrique HTML via sélecteurs CSS, extrait les articles,
    et génère de manière descendante un arbre d'éléments XML au format RSS 2.0.
    """
    # Déclaration des nœuds structurels majeurs de la spécification RSS 2.0
    noeud_rss = ET.Element("rss", version="2.0")
    noeud_channel = ET.SubElement(noeud_rss, "channel")
    
    # Injection des métadonnées obligatoires du canal de syndication
    ET.SubElement(noeud_channel, "title").text = nom
    ET.SubElement(noeud_channel, "link").text = url_racine
    ET.SubElement(noeud_channel, "description").text = f"Flux de veille hybride généré automatiquement pour l'entité {nom}."
    ET.SubElement(noeud_channel, "pubDate").text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Algorithme heuristique d'isolation des blocs d'articles (Containers)
    # Tente d'analyser les sélecteurs CSS fournis ou applique des sélecteurs de secours standardisés
    selecteurs_containers = regles_css["container_css"].split(",")
    elements_articles = []
    
    for selecteur in selecteurs_containers:
        elements_articles = soupe_html.select(selecteur.strip())
        if elements_articles:
            break

    compteur_articles = 0
    # Traitement itératif des fiches découvertes, restreint aux 5 articles les plus récents
    for article in elements_articles:
        if compteur_articles >= 5:
            break

        # Recherche de la balise textuelle contenant le Titre de l'article
        texte_titre = "Actualité sans titre explicite"
        selecteurs_titres = regles_css["titre_css"].split(",")
        balise_titre = None
        for sel_t in selecteurs_titres:
            balise_titre = article.select_one(sel_t.strip())
            if balise_titre:
                break
        
        if balise_titre:
            texte_titre = balise_titre.get_text().strip()

        # Recherche et reconstruction de l'hyperlien absolu (URL) de l'article d'origine
        balise_ancre = article.find("a") if not balise_titre else (balise_titre.find("a") or balise_titre if balise_titre.name == "a" else article.find("a"))
        if not balise_ancre or not balise_ancre.has_attr("href"):
            continue
            
        lien_brut = balise_ancre["href"]
        # Résolution mathématique des URLs relatives en URLs absolues stables
        lien_absolu = urllib.parse.urljoin(url_racine, lien_brut)

        # Extraction facultative du paragraphe de résumé
        balise_paragraphe = article.find("p")
        texte_extrait = balise_paragraphe.get_text().strip() if balise_paragraphe else "Consulter la ressource d'origine pour analyser le contenu technique associé."
        if len(texte_extrait) > 250:
            texte_extrait = texte_extrait[:247] + "..."

        # Construction sémantique du nœud d'article individuel <item>
        noeud_item = ET.SubElement(noeud_channel, "item")
        ET.SubElement(noeud_item, "title").text = texte_titre
        ET.SubElement(noeud_item, "link").text = lien_absolu
        ET.SubElement(noeud_item, "description").text = texte_extrait
        ET.SubElement(noeud_item, "pubDate").text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        
        compteur_articles += 1

    # Si le site n'a produit aucun article (sélection CSS infructueuse), écriture d'une fiche palliative de diagnostic
    if compteur_articles == 0:
        noeud_item = ET.SubElement(noeud_channel, "item")
        ET.SubElement(noeud_item, "title").text = f"Analyse en cours d'ajustement structurel pour {nom}"
        ET.SubElement(noeud_item, "link").text = url_racine
        ET.SubElement(noeud_item, "description").text = "Le script est en attente de synchronisation géométrique des classes de styles CSS."
        ET.SubElement(noeud_item, "pubDate").text = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Génération du nom de fichier normalisé (ex: "Theia Land" -> "theia_land.xml")
    nom_fichier_xml = nom.lower().replace(" ", "_").replace("'", "_") + ".xml"
    
    # Sérialisation finale de l'arbre DOM XML vers le disque de la machine virtuelle
    arbre_document = ET.ElementTree(noeud_rss)
    ET.indent(arbre_document, space="  ", level=0) # Indentation pour lisibilité didactique humaine
    arbre_document.write(nom_fichier_xml, encoding="utf-8", xml_declaration=True)
    print(f"--> Fichier XML généré avec succès : {nom_fichier_xml} ({compteur_articles} fiches)")

if __name__ == "__main__":
    initialiser_processus_scraping()
