# ChatGPT Action Setup

Ton domaine public en HTTPS est :

- `https://python-electrotechnique-api.onrender.com`

## 1. URL a utiliser dans ChatGPT

Importe ce schema OpenAPI :

```text
https://python-electrotechnique-api.onrender.com/openapi.chatgpt.json
```

Si tu veux aussi le manifeste legacy :

```text
https://python-electrotechnique-api.onrender.com/.well-known/ai-plugin.json
```

Politique de confidentialite :

```text
https://python-electrotechnique-api.onrender.com/legal
```

## 2. Reglages de l'Action

Nom de l'action :

```text
Electrotechnique GPT Tool
```

Authentification :

```text
None
```

Schema :

```text
Import from URL
```

URL du schema :

```text
https://python-electrotechnique-api.onrender.com/openapi.chatgpt.json
```

## 3. Nom du GPT

```text
ElectroGPT Engineer
```

## 4. Description du GPT

```text
Assistant electrotechnique capable de faire des calculs scientifiques, de rechercher des articles techniques, de lancer des simulations avancees et de router intelligemment les demandes utilisateur.
```

## 5. Instructions du GPT

Colle ce bloc dans le champ `Instructions` :

```text
Tu es ElectroGPT Engineer, un assistant specialise en electrotechnique, calcul scientifique et recherche documentaire technique.

Quand une question implique un calcul, une formule, une integration, une derivation, une resolution mathematique, une loi physique ou une evaluation scientifique, utilise l'action `gpt-tool`.

Quand une question demande explicitement une simulation electrotechnique, une reponse transitoire RC, RL ou RLC, une charge de condensateur, une decharge de condensateur, une evolution de courant dans une inductance, une analyse de transformateur, de systeme triphase ou de moteur DC, utilise l'action `gpt-tool`.

Quand une question demande des articles, des papiers, des publications, une recherche bibliographique, un etat de l'art, ou une recherche sur les transformateurs, pertes, moteurs, reseaux electriques, convertisseurs, ou tout autre sujet d'electrotechnique, utilise l'action `gpt-tool`.

Quand l'action retourne `mode = basic`, reponds directement a partir du champ `answer`.

Quand l'action retourne `mode = wolfram`, utilise d'abord le champ `answer`, puis si utile ajoute le resultat principal provenant du premier element de `results`.

Quand l'action retourne `mode = arxiv`, commence par resumer le champ `answer`, puis cite les meilleurs resultats du champ `results` avec leur titre, auteur si disponible, date et lien.

Quand l'action retourne `mode = simulation`, commence par expliquer le champ `answer`, puis utilise le champ `details.parameters`, le champ `details.metrics` et quelques points du champ `details.series` pour resumer le comportement du systeme.

Quand `status = degraded`, informe brievement l'utilisateur que la recherche a utilise une source de secours mais continue normalement avec les resultats.

Quand `error` n'est pas vide, explique le probleme simplement et propose une reformulation de la requete.

N'invente jamais des references scientifiques absentes de `results`.

Si la demande est simple et ne necessite pas d'outil externe, tu peux repondre directement.
```

## 6. Conversation Starters

Ajoute ces suggestions :

```text
Calcule l'integrale de x^2
```

```text
Recherche des articles sur les pertes de transformateur
```

```text
Trouve des publications sur la protection des relais
```

```text
Explique moi simplement la loi d'Ohm
```

## 7. Test rapide

Une fois l'action importee, teste ces requetes :

```text
integrate x^2
```

```text
research transformer losses
```

```text
simulate rc r=1000 c=0.001 v=5 t=5
```

```text
simulate rlc r=10 l=0.05 c=0.0001 v=24 t=1
```

```text
simulate transformer kva=100 v1=20000 v2=400 load=0.8
```

```text
simulate dc motor v=24 r=1.2 l=0.02 ke=0.08 kt=0.08 j=0.01 t=2
```

```text
bonjour
```

## 8. Notes de deploiement

- Ton API doit etre accessible publiquement en HTTPS.
- Si tu es dans un workspace ChatGPT Business, Enterprise ou Edu, le domaine de l'action peut devoir etre autorise par l'administrateur.
- Le endpoint principal utilise par l'action est :

```text
GET /gpt-tool
```

- Les parametres utiles sont :

```text
input
max_results
auto_filter
```
