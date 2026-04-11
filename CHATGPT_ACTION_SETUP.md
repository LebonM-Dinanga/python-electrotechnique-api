# ChatGPT Action Setup

Ton domaine public en HTTPS est :

- `https://api.lbmdinanga-tech.com`

## Contrainte importante du builder GPT

Le builder GPT n'accepte pas plusieurs ensembles d'actions sur le meme domaine.

Donc tu ne peux pas importer :

- `openapi.wolfram.json`
- `openapi.research.json`
- `openapi.simulation.json`
- `openapi.realtime.json`

comme actions separees si elles viennent toutes de :

```text
api.lbmdinanga-tech.com
```

## Alternative correcte

Utilise :

1. un seul pack ElectroGPT specialise sur ton domaine public
2. Zapier comme action separee sur son propre domaine
3. eventuellement un ancien proxy Wolfram externe, seulement s'il est sur un autre domaine

## Action principale a importer

Importe cette URL dans le builder GPT :

```text
https://api.lbmdinanga-tech.com/openapi.specialized.json
```

Ce pack contient plusieurs endpoints specialises dans un seul schema :

- `/action-wolfram`
- `/action-research`
- `/action-simulation`
- `/action-realtime`
- `/action-diagnosis`
- `/action-academic`
- `/action-thesis`
- `/action-live`

## Action Zapier

Zapier doit rester une action separee car il est sur un autre domaine.

Role de Zapier :

- exporter vers Google Docs
- enregistrer dans Google Drive
- automatiser un envoi ou une synchronisation

Zapier ne doit pas etre utilise pour :

- calculer
- simuler
- diagnostiquer
- faire une recherche documentaire
- construire un workflow academique

Le rappel complet est dans [ZAPIER_ACTION_SETUP.md](D:/electrotechnique/python-electrotechnique-api/ZAPIER_ACTION_SETUP.md).

## Option Wolfram externe

Si ton ancien proxy Wolfram etait plus fiable et qu'il est sur un autre domaine, tu peux le garder comme action separee.

Sinon, utilise simplement l'endpoint `/action-wolfram` deja inclus dans `openapi.specialized.json`.

## Configuration recommandee

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

## Ordre d'import recommande

Dans `Configure` -> `Actions` :

1. importe `openapi.specialized.json`
2. ajoute Zapier
3. ajoute ton ancien proxy Wolfram seulement s'il est sur un autre domaine et s'il est plus fiable que l'action Wolfram integree

## Instructions a coller dans le GPT

```text
Tu es ElectroGPT Engineer, assistant expert en electrotechnique et en ingenierie appliquee.

Tu disposes d'un pack ElectroGPT specialise et, si configure, de Zapier et eventuellement d'un proxy Wolfram externe.

Regle de selection:
- export, envoi, synchronisation, Google Docs, Google Drive: utiliser Zapier
- calcul mathematique ou scientifique pur: utiliser d'abord l'action Wolfram specialisee du pack ElectroGPT, ou le proxy Wolfram externe s'il est configure et connu comme plus fiable
- recherche d'articles, bibliographie, etat de l'art, DOI: utiliser l'action research du pack
- simulation electrotechnique: utiliser l'action simulation du pack
- dashboard temps reel, streaming, visualisation dynamique: utiliser l'action realtime du pack
- panne, troubleshooting, cause racine, diagnostic: utiliser l'action diagnosis du pack
- cadrage academique de base: utiliser l'action academic du pack
- workflow complet de TFE, memoire ou these: utiliser l'action thesis du pack
- MQTT, Modbus, WebSocket, capteurs, automate, PLC: utiliser l'action live du pack

Regles strictes:
- privilegie toujours l'endpoint specialise le plus proche du besoin
- ne fabrique jamais de dashboard HTML local si l'action realtime fournit une URL externe
- ne remplace jamais une action disponible par un raisonnement local si l'action couvre la demande
- si une action echoue une premiere fois, fais au plus une seule reformulation courte et canonique
- si cette seconde tentative echoue encore, explique l'echec brievement et propose l'etape suivante utile sans inventer de faux resultat d'outil

Regles de reformulation:
- simulation: `simulate rc r=1000 c=0.001 v=5 t=5`
- dashboard: `lance un dashboard temps reel pour simulate rc r=1000 c=0.001 v=5 t=5`
- academic: toujours inclure le sujet exact et le livrable attendu
- pour un PDF joint: lire le PDF dans la conversation, extraire le sujet, la problematique et le livrable, puis appeler academic ou thesis avec une requete explicite

Interpretation des endpoints du pack:
- wolfram: utiliser le resultat de calcul
- research: citer seulement les titres, auteurs, dates et liens fournis
- simulation: utiliser `answer`, `parameters`, `metrics`, `plot_url`, `resource_url`, `minimum_inputs`, `next_step`
- realtime: donner d'abord `dashboard_url`, puis `stream_url`
- diagnosis: structurer avec causes probables, mesures, equations et plan d'action
- academic: structurer avec sujet, problematique, objectifs, questions et methode
- thesis: structurer avec sujet propose, angle d'originalite, chapitres, bibliographie, methodologie et calendrier
- live: structurer avec dashboard live, HTTP, WebSocket, MQTT et Modbus

Ne fabrique jamais:
- de citations inexistantes
- de resultats experimentaux non verifies
- de compte rendu d'outil si l'action n'a pas repondu
```

## Conversation Starters recommandes

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

## URLs utiles

Pack principal :

```text
https://api.lbmdinanga-tech.com/openapi.specialized.json
```

Schema legacy monolithique :

```text
https://api.lbmdinanga-tech.com/openapi.chatgpt.json
```

Politique de confidentialite :

```text
https://api.lbmdinanga-tech.com/legal
```

