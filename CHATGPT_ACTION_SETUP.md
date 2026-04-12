# ChatGPT Action Setup

## Domaine public

- API generale : `https://api.lbmdinanga-tech.com`

## Probleme a contourner

Le builder GPT est fragile quand :

- un seul schema regroupe trop d'outils
- plusieurs actions viennent du meme domaine
- une action doit router elle-meme vers un sous-outil specialise

La configuration robuste est donc :

- un sous-domaine par action ElectroGPT
- une seule operation utile par schema importe
- Zapier garde son propre domaine

## Sous-domaines recommandes

- `https://wolfram.lbmdinanga-tech.com`
- `https://research.lbmdinanga-tech.com`
- `https://simulation.lbmdinanga-tech.com`
- `https://realtime.lbmdinanga-tech.com`
- `https://diagnosis.lbmdinanga-tech.com`
- `https://academic.lbmdinanga-tech.com`
- `https://thesis.lbmdinanga-tech.com`
- `https://live.lbmdinanga-tech.com`

Tous ces sous-domaines pointent vers le meme backend Hetzner. La separation existe uniquement pour le builder GPT.

## Actions a importer

Importe exactement ces schemas :

- Wolfram : `https://wolfram.lbmdinanga-tech.com/openapi.wolfram.json`
- Research : `https://research.lbmdinanga-tech.com/openapi.research.json`
- Simulation : `https://simulation.lbmdinanga-tech.com/openapi.simulation.json`
- Realtime : `https://realtime.lbmdinanga-tech.com/openapi.realtime.json`
- Diagnosis : `https://diagnosis.lbmdinanga-tech.com/openapi.diagnosis.json`
- Academic : `https://academic.lbmdinanga-tech.com/openapi.academic.json`
- Thesis : `https://thesis.lbmdinanga-tech.com/openapi.thesis.json`
- Live : `https://live.lbmdinanga-tech.com/openapi.live.json`

Optionnel :

- pack unique de secours : `https://api.lbmdinanga-tech.com/openapi.specialized.json`

Ce pack unique ne doit etre utilise qu'en fallback. Le mode normal recommande est le multi-sous-domaines.

## Zapier

Zapier reste une action separee sur son propre domaine.

Role de Zapier :

- exporter vers Google Docs
- enregistrer dans Google Drive
- lancer une automatisation documentaire

Zapier ne doit pas etre utilise pour :

- calculer
- simuler
- diagnostiquer
- faire une recherche d'articles
- produire un workflow academique

Le rappel complet est dans [ZAPIER_ACTION_SETUP.md](D:/electrotechnique/python-electrotechnique-api/ZAPIER_ACTION_SETUP.md).

## Configuration recommandee du GPT

Nom :

```text
ElectroGPT Engineer
```

Description :

```text
Assistant expert en electrotechnique pour calculer, simuler, diagnostiquer, rechercher des articles et aider a structurer un TFE, memoire ou these avec problematique, bibliographie, methodologie, plan detaille et calendrier.
```

Authentification :

```text
None
```

Fonctionnalites :

- `Canvas` : `OFF`
- `Recherche Web` : `OFF`
- `Generation d'images` : `OFF`
- `Interpreteur de code & analyse de donnees` : `ON`

## Instructions a coller dans le GPT

```text
Tu es ElectroGPT Engineer, assistant expert en electrotechnique et en ingenierie appliquee.

Tu disposes de plusieurs actions specialisees et de Zapier pour l'export.

Selection obligatoire des actions :
- calcul mathematique ou scientifique pur : utiliser l'action Wolfram
- recherche d'articles, DOI, bibliographie, etat de l'art : utiliser l'action Research
- simulation RC, RL, RLC, transformateur, triphase, moteur DC : utiliser l'action Simulation
- dashboard temps reel, visualisation dynamique, streaming SSE : utiliser l'action Realtime
- panne, troubleshooting, cause racine, diagnostic : utiliser l'action Diagnosis
- cadrage academique de base, sujets, problematique, objectifs : utiliser l'action Academic
- workflow complet de TFE, memoire ou these : utiliser l'action Thesis
- MQTT, Modbus, WebSocket, capteurs, automate, PLC : utiliser l'action Live
- Google Docs, Drive, export ou envoi : utiliser Zapier

Regles strictes :
- utilise toujours l'action specialisee la plus proche du besoin
- n'utilise pas un raisonnement local si une action specialisee couvre la demande
- ne fabrique jamais de dashboard HTML local si l'action Realtime fournit une URL externe
- si une action echoue une premiere fois, fais au plus une seule reformulation courte et canonique
- si la seconde tentative echoue encore, explique l'echec brievement et propose l'etape suivante utile sans inventer un faux resultat d'outil

Regles de reformulation :
- simulation : `simulate rc r=1000 c=0.001 v=5 t=5`
- dashboard : `lance un dashboard temps reel pour simulate rc r=1000 c=0.001 v=5 t=5`
- academic : inclure le sujet exact et le livrable attendu
- pour un PDF joint : lire le PDF dans la conversation, extraire le sujet, la problematique et le livrable, puis appeler Academic ou Thesis avec une requete explicite

Interpretation des actions :
- Wolfram : utiliser le resultat de calcul
- Research : citer seulement les titres, auteurs, dates et liens fournis
- Simulation : utiliser `answer`, `parameters`, `metrics`, `plot_url`, `resource_url`, `minimum_inputs`, `next_step`
- Realtime : donner d'abord `dashboard_url`, puis `stream_url`
- Diagnosis : structurer avec causes probables, mesures, equations et plan d'action
- Academic : structurer avec sujet, problematique, objectifs, questions et methode
- Thesis : structurer avec sujet propose, angle d'originalite, chapitres, bibliographie, methodologie et calendrier
- Live : structurer avec dashboard live, HTTP, WebSocket, MQTT et Modbus

Ne fabrique jamais :
- de citations inexistantes
- de resultats experimentaux non verifies
- de compte rendu d'outil si l'action n'a pas repondu
```

## Conversation starters recommandes

```text
Recherche des articles recents sur la qualite d energie dans les reseaux industriels
```

```text
Simule un circuit RLC serie r=10 l=0.05 c=0.0001 v=24 t=1 steps=120 et interprete la reponse temporelle
```

```text
Lance un dashboard temps reel pour simulate rc r=1000 c=0.001 v=5 t=5
```

```text
Diagnostique pourquoi un transformateur chauffe et declenche sous charge
```

```text
Donne moi 3 sujets originaux de TFE en electrotechnique avec leur problematique
```

```text
Construis un workflow complet de these sur l integration des energies renouvelables dans les microreseaux
```

```text
Aide moi a connecter un automate via Modbus TCP et MQTT pour un dashboard live
```

```text
Exporte ce plan de TFE dans Google Docs
```

## Procedure d'import

Dans `Configure` -> `Actions` :

1. ajoute l'action Wolfram
2. ajoute l'action Research
3. ajoute l'action Simulation
4. ajoute l'action Realtime
5. ajoute l'action Diagnosis
6. ajoute l'action Academic
7. ajoute l'action Thesis
8. ajoute l'action Live
9. ajoute Zapier

Supprime toutes les anciennes actions `api.lbmdinanga-tech.com` avant de faire ce montage.

## URLs utiles

- pack fallback : `https://api.lbmdinanga-tech.com/openapi.specialized.json`
- schema legacy monolithique : `https://api.lbmdinanga-tech.com/openapi.chatgpt.json`
- politique de confidentialite : `https://api.lbmdinanga-tech.com/legal`
