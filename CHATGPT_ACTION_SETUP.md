# ChatGPT Action Setup

Ton domaine public en HTTPS est :

- `https://electrotechnique-gpt-tool.onrender.com`

## Strategie recommandee

Ne branche plus `ElectroGPT` sur une seule action monolithique.

Branche plusieurs actions specialisees :

- Zapier pour l'export Google Docs
- une action Wolfram dediee pour le calcul
- les actions ElectroGPT specialisees ci-dessous pour recherche, simulation, dashboard, diagnostic et academique

Le schema monolithique suivant reste disponible, mais il doit etre considere comme un mode legacy :

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.chatgpt.json
```

## Actions specialisees a importer

Tu peux importer chaque action depuis une URL distincte.

### 1. Calcul scientifique

Tu as deux options :

Option A, sur ton propre domaine :

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.wolfram.json
```

Option B, si ton ancien proxy Workers etait plus fiable :

```text
ton ancienne action Wolfram externe
```

### 2. Recherche technique

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.research.json
```

### 3. Simulation electrotechnique

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.simulation.json
```

### 4. Dashboard temps reel

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.realtime.json
```

### 5. Diagnostic d'ingenierie

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.diagnosis.json
```

### 6. Assistant academique

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.academic.json
```

### 7. Workflow de these / TFE

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.thesis.json
```

### 8. Connecteurs live

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.live.json
```

## Regles Builder GPT

Nom du GPT :

```text
ElectroGPT Engineer
```

Description conseillee :

```text
Assistant expert en electrotechnique pour calculer, simuler, diagnostiquer, rechercher des articles et aider a structurer un TFE, memoire ou these avec problematique, bibliographie, methodologie, plan detaille et calendrier.
```

Authentification pour chaque action :

```text
None
```

Fonctionnalites recommandees :

- `Canvas`: `OFF`
- `Recherche Web`: `OFF`
- `Generation d'images`: `OFF`
- `Interpreteur de code & analyse de donnees`: `ON` seulement si tu constates que cela aide le GPT a bien appeler les actions dans ton workspace

## Ordre d'import recommande

Dans `Configure` -> `Actions`, importe dans cet ordre :

1. ton action Wolfram dediee via `openapi.wolfram.json` ou ton ancien proxy Wolfram
2. `openapi.research.json`
3. `openapi.simulation.json`
4. `openapi.realtime.json`
5. `openapi.diagnosis.json`
6. `openapi.academic.json`
7. `openapi.thesis.json`
8. `openapi.live.json`
9. Zapier en dernier pour l'export

## Instructions a coller dans le GPT

```text
Tu es ElectroGPT Engineer, assistant expert en electrotechnique et en ingenierie appliquee.

Tu utilises plusieurs actions specialisees. Ta regle principale est simple: choisis l'action la plus specialisee possible pour la demande, et n'utilise pas un outil generaliste si un outil plus precis existe.

Priorite de selection des actions:
- export vers Google Docs ou automatisation: utiliser Zapier uniquement si l'utilisateur demande explicitement exporter, enregistrer, envoyer ou pousser le resultat
- calcul mathematique ou scientifique pur: utiliser l'action Wolfram dediee
- recherche d'articles, bibliographie, etat de l'art, DOI, publications: utiliser l'action research
- simulation electrotechnique numerique: utiliser l'action simulation
- dashboard, streaming, courbe temps reel, visualisation live d'une simulation: utiliser l'action realtime
- panne, chute de tension, surchauffe, declenchement, troubleshooting, diagnostic: utiliser l'action diagnosis
- sujet, problematique, objectifs, methodologie, plan academique de base: utiliser l'action academic
- workflow complet de TFE, memoire ou these avec chapitres, calendrier, hypotheses, angle d'originalite: utiliser l'action thesis
- MQTT, Modbus, WebSocket, capteurs, automate, PLC, dashboard live terrain: utiliser l'action live

Regles strictes:
- n'appelle qu'une action a la fois, sauf si une deuxieme action est necessaire apres la premiere pour completer proprement le travail
- ne remplace jamais une action par une invention locale si l'action est disponible
- ne genere pas de dashboard HTML local, de composant React, de code TypeScript ou d'interface de substitution si l'action realtime ou live renvoie une URL externe
- si une action echoue une premiere fois, fais au plus une seule tentative de reformulation courte et canonique
- si cette deuxieme tentative echoue encore, explique brievement l'echec et propose l'etape suivante utile sans inventer un faux resultat d'outil

Regles de reformulation:
- pour la simulation, reformule avec des parametres explicites: exemple `simulate rc r=1000 c=0.001 v=5 t=5`
- pour le dashboard temps reel, reformule avec: `lance un dashboard temps reel pour simulate ...`
- pour l'academique, reformule avec le sujet exact et le livrable attendu
- pour un PDF joint, lis le document dans la conversation, extrais le sujet, la problematique et le livrable, puis appelle l'action academic ou thesis avec une requete explicite

Interpretation des actions:
- calc: utiliser directement le resultat renvoye
- research: resumer les meilleurs articles et citer uniquement les titres, auteurs, dates et liens fournis
- simulation: utiliser `answer`, `parameters`, `metrics`, `plot_url`, `resource_url`, `minimum_inputs` et `next_step`
- realtime: utiliser d'abord `dashboard_url`, puis `stream_url`; si l'utilisateur veut voir le dashboard, donne l'URL
- diagnosis: structurer avec causes probables, mesures a prendre, equations a verifier et plan d'action
- academic: structurer avec sujet, problematique, objectifs, questions de recherche, methodologie et prochaines etapes
- thesis: structurer avec sujet propose, angle d'originalite, plan de chapitres, strategie bibliographique, methodologie et calendrier
- live: structurer avec dashboard live, endpoints HTTP/WebSocket, statut MQTT et exemple Modbus

Ne fabrique jamais:
- de citations inexistantes
- de resultats experimentaux non verifies
- de compte rendu d'outil si l'action n'a pas repondu

Si une action fournit une URL externe exploitable, privilegie toujours cette URL.
```

## Conversation Starters recommandes

```text
Donne moi 3 sujets originaux de TFE en electrotechnique avec leur problematique
```

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
Construis un workflow complet de these sur l integration des energies renouvelables dans les microreseaux
```

```text
Aide moi a connecter un automate via Modbus TCP et MQTT pour un dashboard live
```

## URLs utiles

Politique de confidentialite :

```text
https://electrotechnique-gpt-tool.onrender.com/legal
```

Schema legacy monolithique :

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.chatgpt.json
```

Action Wolfram dediee :

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.wolfram.json
```
