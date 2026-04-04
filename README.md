# Python Electrotechnique API

API FastAPI pour rendre un GPT plus puissant en electrotechnique.

Le projet combine :

- calcul scientifique via WolframAlpha
- recherche documentaire technique via arXiv avec fallback Crossref
- simulations RC, RL et RLC pour des reponses transitoires
- simulation de transformateur, systeme triphase et moteur DC
- visualisation SVG des simulations pour courbes, tendances et lecture rapide
- dashboard web temps reel avec streaming SSE des points de simulation
- diagnostic structure de problemes d'ingenierie et d'electrotechnique
- ingestion live de donnees terrain via HTTP, WebSocket, MQTT et Modbus TCP
- assistant academique pour TFE, PFE, memoire et these
- routage intelligent via `/smart-query`
- endpoint stable pour ChatGPT Actions via `/gpt-tool`

## Fonctionnalites

- `GET /wolfram` : calculs, formules, integrales, resultats scientifiques
- `GET /arxiv` : recherche d'articles avec filtre electrotechnique automatique
- `GET /academic-assistant` : plan academique, problematique, objectifs, methode, structure et sources de depart
- `GET /thesis-workflow` : workflow complet pour TFE, memoire ou these avec plan detaille, bibliographie et calendrier
- `GET /connectors-status` : etat des connecteurs live et des canaux telemetry actifs
- `GET /live-connectors` : guide de connexion live pour capteurs, MQTT, Modbus et WebSocket
- `POST /telemetry-ingest` : ingestion HTTP simple de donnees live
- `GET /telemetry-stream` : diffusion SSE des trames live d'un canal
- `GET /live-dashboard` : dashboard web pour visualiser les donnees live d'un canal
- `GET /modbus-read` : lecture Modbus TCP avec injection dans le pipeline telemetry
- `GET /simulate` : simulations RC, RL, RLC, transformateur, triphase et moteur DC
- `GET /simulate-plot` : rendu SVG d'une simulation pour obtenir une courbe ou un tableau visuel
- `GET /simulate-stream` : diffusion progressive d'une simulation via Server-Sent Events
- `GET /realtime-simulation` : configuration JSON pour dashboard et streaming temps reel
- `GET /realtime-dashboard` : dashboard web interactif pour visualiser la simulation en direct
- `GET /engineering-diagnosis` : diagnostic structure d'un probleme technique avec causes probables et plan d'action
- `GET /research` : combine les recherches utiles pour une question technique
- `GET /smart-query` : routeur intelligent riche pour GPT
- `GET /gpt-tool` : endpoint minimal et stable pour ChatGPT Actions
- `GET /openapi.chatgpt.json` : schema OpenAPI dedie a l'action
- `GET /.well-known/ai-plugin.json` : manifeste plugin legacy
- `GET /legal` : page de confidentialite simple

## Structure du projet

- `main.py` : application FastAPI principale
- `requirements.txt` : dependances Python
- `render.yaml` : configuration Render
- `openapi.chatgpt.json` : schema OpenAPI genere pour ChatGPT Actions
- `ai-plugin.json` : manifeste plugin genere
- `CHATGPT_ACTION_SETUP.md` : texte a coller dans le builder GPT
- `RENDER_DEPLOYMENT.md` : guide de deploiement Render

## Installation locale

### 1. Cloner le projet

```bash
git clone <URL_DU_REPO>
cd python-electrotechnique-api
```

### 2. Creer un environnement virtuel

```bash
python -m venv .venv
```

Sous Windows PowerShell :

```bash
.venv\Scripts\Activate.ps1
```

### 3. Installer les dependances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Variables recommandees :

```text
WOLFRAM_APP_ID=<ta_cle_wolframalpha>
CONTACT_EMAIL=lebonmukendi17@gmail.com
ARXIV_DOMAIN_FILTER=electrical engineering
MAX_TELEMETRY_POINTS=600
MQTT_BROKER_HOST=
MQTT_BROKER_PORT=1883
MQTT_TOPIC_PREFIX=electrogpt/telemetry
```

Variables optionnelles :

```text
PLUGIN_LOGO_URL=https://ton-domaine/logo.png
PLUGIN_LEGAL_URL=https://ton-domaine/legal
ALLOWED_ORIGINS=*
```

### 5. Lancer l'API

```bash
uvicorn main:app --reload
```

Puis ouvre :

```text
http://127.0.0.1:8000/docs
```

## Exemples d'utilisation

### Calcul scientifique

```text
GET /gpt-tool?input=integrate x^2
```

Exemple de sortie :

```json
{
  "status": "ok",
  "tool": "gpt-tool",
  "mode": "wolfram",
  "input": "integrate x^2",
  "query_used": "integrate x^2",
  "executed": true,
  "source": "wolframalpha",
  "redirect": "/wolfram?input=integrate+x%5E2",
  "answer": "x^3/3",
  "results": [
    {
      "title": "WolframAlpha Result",
      "snippet": "x^3/3",
      "link": "",
      "published": "",
      "authors": [],
      "provider": "wolframalpha"
    }
  ],
  "error": ""
}
```

### Recherche d'articles

```text
GET /gpt-tool?input=research transformer losses
```

### TFE / These

```text
GET /academic-assistant?input=Plan de these sur l integration des energies renouvelables dans les microreseaux
```

```text
GET /thesis-workflow?input=Workflow complet de these sur la protection des relais dans les microreseaux
```

```text
GET /gpt-tool?input=Donner 3 sujets recents et pertinents de TFE en electrotechnique
```

```text
GET /gpt-tool?input=Guide de recherche pour un memoire sur la protection des relais
```

```text
GET /gpt-tool?input=Plan detaille de these sur l integration des energies renouvelables dans les microreseaux
```

### Diagnostic d'ingenierie

```text
GET /engineering-diagnosis?input=Pourquoi mon transformateur chauffe et declenche sous charge
```

```text
GET /gpt-tool?input=Pourquoi mon moteur chauffe et vibre apres quelques minutes
```

### Ingestion live capteurs / automate

```text
GET /live-connectors?input=Je veux connecter un automate via Modbus et MQTT
```

```text
GET /live-dashboard?channel=atelier-ligne-1
```

```bash
curl -X POST "https://electrotechnique-gpt-tool.onrender.com/telemetry-ingest" ^
  -H "Content-Type: application/json" ^
  -d "{\"channel\":\"atelier-ligne-1\",\"source\":\"http-gateway\",\"values\":{\"temperature_c\":46.2,\"current_a\":18.4}}"
```

```text
GET /modbus-read?host=192.168.1.10&port=502&unit_id=1&address=0&count=4&register_type=holding&channel=atelier-ligne-1
```

```text
WebSocket ingest: wss://electrotechnique-gpt-tool.onrender.com/ws/telemetry-ingest/atelier-ligne-1
```

```text
WebSocket watch: wss://electrotechnique-gpt-tool.onrender.com/ws/telemetry-watch/atelier-ligne-1
```

### Simulation electrotechnique

```text
GET /simulate?input=simulate rc r=1000 c=0.001 v=5 t=5 steps=50
```

```text
GET /gpt-tool?input=simulate rl r=10 l=0.2 v=24 t=1 steps=50
```

```text
GET /gpt-tool?input=simulate rlc r=10 l=0.05 c=0.0001 v=24 t=1 steps=80
```

```text
GET /gpt-tool?input=simulate transformer kva=100 v1=20000 v2=400 load=0.8 pf=0.9
```

```text
GET /gpt-tool?input=simulate three phase vll=400 i=30 pf=0.92 connection=delta
```

```text
GET /gpt-tool?input=simulate dc motor v=24 r=1.2 l=0.02 ke=0.08 kt=0.08 j=0.01 b=0.001 tl=0.2 t=2
```

```text
GET /simulate-plot?input=simulate rc r=1000 c=0.001 v=5 t=5 steps=50
```

```text
GET /realtime-simulation?input=simulate rc r=1000 c=0.001 v=5 t=5 steps=50
```

```text
GET /realtime-dashboard?input=simulate rc r=1000 c=0.001 v=5 t=5 steps=50
```

### Reponse directe

```text
GET /gpt-tool?input=bonjour
```

## Deploiement Render

Le projet contient deja un fichier `render.yaml`.

Option rapide :

1. pousse le repo sur GitHub
2. ouvre Render
3. clique `New`
4. choisis `Blueprint`
5. selectionne ton repo
6. renseigne `WOLFRAM_APP_ID` comme secret dans Render
7. verifie que `CONTACT_EMAIL` vaut `lebonmukendi17@gmail.com`
8. lance le deploy

Une fois le service en ligne, teste :

```text
https://electrotechnique-gpt-tool.onrender.com/health
```

```text
https://electrotechnique-gpt-tool.onrender.com/docs
```

```text
https://electrotechnique-gpt-tool.onrender.com/gpt-tool?input=integrate%20x^2
```

```text
https://electrotechnique-gpt-tool.onrender.com/gpt-tool?input=simulate%20rc%20r=1000%20c=0.001%20v=5%20t=5
```

Guide detaille :

- [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md)

## Branchement ChatGPT Action

Une fois l'API deployee en HTTPS, utilise :

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.chatgpt.json
```

Dans le builder GPT :

- Action auth : `None`
- Import schema from URL
- URL : `https://electrotechnique-gpt-tool.onrender.com/openapi.chatgpt.json`

Guide detaille :

- [CHATGPT_ACTION_SETUP.md](./CHATGPT_ACTION_SETUP.md)

## Endpoints utiles apres deploiement

```text
/health
/docs
/gpt-tool?input=integrate x^2
/simulate?input=simulate rc r=1000 c=0.001 v=5 t=5
/gpt-tool?input=research transformer losses
/openapi.chatgpt.json
/.well-known/ai-plugin.json
/legal
```

## Notes utiles

- le plan Render `Free` peut mettre le service en veille apres inactivite
- `/gpt-tool` est l'endpoint le plus stable pour ChatGPT Actions
- si arXiv repond mal, l'API bascule automatiquement sur Crossref
- si tu es sur ChatGPT Business, Enterprise ou Edu, le domaine peut devoir etre autorise par l'administrateur

## Licence

Ajoute ici ta licence si tu veux publier le projet.
