# Python Electrotechnique API

API FastAPI pour rendre un GPT plus puissant en electrotechnique.

Le projet combine :

- calcul scientifique via WolframAlpha
- recherche documentaire technique via arXiv avec fallback Crossref
- simulations RC, RL et RLC pour des reponses transitoires
- simulation de transformateur, systeme triphase et moteur DC
- routage intelligent via `/smart-query`
- endpoint stable pour ChatGPT Actions via `/gpt-tool`

## Fonctionnalites

- `GET /wolfram` : calculs, formules, integrales, resultats scientifiques
- `GET /arxiv` : recherche d'articles avec filtre electrotechnique automatique
- `GET /simulate` : simulations RC, RL, RLC, transformateur, triphase et moteur DC
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
https://python-electrotechnique-api.onrender.com/health
```

```text
https://python-electrotechnique-api.onrender.com/docs
```

```text
https://python-electrotechnique-api.onrender.com/gpt-tool?input=integrate%20x^2
```

```text
https://python-electrotechnique-api.onrender.com/gpt-tool?input=simulate%20rc%20r=1000%20c=0.001%20v=5%20t=5
```

Guide detaille :

- [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md)

## Branchement ChatGPT Action

Une fois l'API deployee en HTTPS, utilise :

```text
https://python-electrotechnique-api.onrender.com/openapi.chatgpt.json
```

Dans le builder GPT :

- Action auth : `None`
- Import schema from URL
- URL : `https://python-electrotechnique-api.onrender.com/openapi.chatgpt.json`

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
