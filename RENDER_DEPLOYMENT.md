# Render Deployment

## Option la plus simple

Utilise le fichier [render.yaml](D:/electrotechnique/python-electrotechnique-api/render.yaml). Render peut creer le service automatiquement depuis ce blueprint.

## Avant de commencer

- Pousse ce projet sur GitHub ou GitLab.
- Verifie que `main.py`, `requirements.txt` et `render.yaml` sont bien a la racine du repo.
- La configuration Render garde ton email public, mais la cle WolframAlpha doit rester un secret Render.

## Methode 1. Deploiement via Blueprint

1. Connecte ton repo a Render.
2. Dans Render, clique `New` puis `Blueprint`.
3. Selectionne ton repo.
4. Render detectera automatiquement [render.yaml](D:/electrotechnique/python-electrotechnique-api/render.yaml).
5. Renseigne la variable secrete `WOLFRAM_APP_ID` dans Render.
6. Verifie que `CONTACT_EMAIL = lebonmukendi17@gmail.com`.
7. Lance le deploy.

## Methode 2. Deploiement manuel via Web Service

Si tu ne veux pas utiliser `render.yaml`, cree un `Web Service` avec ces valeurs :

- Runtime : `Python`
- Region : `Frankfurt`
- Build Command : `pip install -r requirements.txt`
- Start Command : `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health Check Path : `/health`

Variables d'environnement :

- `WOLFRAM_APP_ID` : obligatoire, a definir comme secret Render
- `CONTACT_EMAIL` : `lebonmukendi17@gmail.com`
- `ARXIV_DOMAIN_FILTER` : `electrical engineering`
- `PLUGIN_LOGO_URL` : optionnel
- `PLUGIN_LEGAL_URL` : optionnel

## Plan Render

- `Free` est pratique pour les tests.
- Si tu veux eviter les cold starts, passe ensuite sur un plan payant.

## URLs a tester apres le deploy

Ton URL publique Render est :

```text
https://python-electrotechnique-api.onrender.com
```

Tests API :

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
https://python-electrotechnique-api.onrender.com/gpt-tool?input=research%20transformer%20losses
```

```text
https://python-electrotechnique-api.onrender.com/gpt-tool?input=simulate%20rc%20r=1000%20c=0.001%20v=5%20t=5
```

```text
https://python-electrotechnique-api.onrender.com/gpt-tool?input=simulate%20transformer%20kva=100%20v1=20000%20v2=400%20load=0.8
```

```text
https://python-electrotechnique-api.onrender.com/gpt-tool?input=simulate%20three%20phase%20vll=400%20i=30%20pf=0.92%20connection=delta
```

Tests ChatGPT Action :

```text
https://python-electrotechnique-api.onrender.com/openapi.chatgpt.json
```

```text
https://python-electrotechnique-api.onrender.com/.well-known/ai-plugin.json
```

```text
https://python-electrotechnique-api.onrender.com/legal
```

## Ce qu'il faut coller dans ChatGPT Actions

Schema OpenAPI :

```text
https://python-electrotechnique-api.onrender.com/openapi.chatgpt.json
```

Authentification :

```text
None
```

## Probleme le plus courant

Si ChatGPT ne voit pas ton action :

- verifie que l'URL est publique en HTTPS
- verifie que `/openapi.chatgpt.json` repond sans erreur
- verifie que `/gpt-tool?input=bonjour` renvoie du JSON
- si tu es dans un workspace gere, demande a l'admin d'autoriser le domaine de l'action

## Note utile

L'URL `legal_info_url` du manifeste pointe automatiquement vers `/legal` si `PLUGIN_LEGAL_URL` n'est pas defini.
