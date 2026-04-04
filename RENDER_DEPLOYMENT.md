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
- `PUBLIC_BASE_URL` : `https://electrotechnique-gpt-tool.onrender.com`
- `MQTT_BROKER_HOST` : ton broker MQTT
- `MQTT_BROKER_PORT` : en general `1883`
- `MQTT_TOPIC_PREFIX` : par exemple `electrogpt/telemetry`
- `MQTT_USERNAME` : optionnel
- `MQTT_PASSWORD` : optionnel
- `MAX_TELEMETRY_POINTS` : optionnel, par exemple `600`
- `PLUGIN_LOGO_URL` : optionnel
- `PLUGIN_LEGAL_URL` : optionnel

## Plan Render

- `Free` est pratique pour les tests.
- Si tu veux eviter les cold starts, passe ensuite sur un plan payant.

## URLs a tester apres le deploy

Ton URL publique Render est :

```text
https://electrotechnique-gpt-tool.onrender.com
```

Tests API :

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
https://electrotechnique-gpt-tool.onrender.com/gpt-tool?input=research%20transformer%20losses
```

```text
https://electrotechnique-gpt-tool.onrender.com/gpt-tool?input=simulate%20rc%20r=1000%20c=0.001%20v=5%20t=5
```

```text
https://electrotechnique-gpt-tool.onrender.com/gpt-tool?input=simulate%20transformer%20kva=100%20v1=20000%20v2=400%20load=0.8
```

```text
https://electrotechnique-gpt-tool.onrender.com/gpt-tool?input=simulate%20three%20phase%20vll=400%20i=30%20pf=0.92%20connection=delta
```

Tests ChatGPT Action :

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.chatgpt.json
```

```text
https://electrotechnique-gpt-tool.onrender.com/.well-known/ai-plugin.json
```

```text
https://electrotechnique-gpt-tool.onrender.com/legal
```

## Ce qu'il faut coller dans ChatGPT Actions

Schema OpenAPI :

```text
https://electrotechnique-gpt-tool.onrender.com/openapi.chatgpt.json
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

## Procedure de test bout en bout MQTT -> Render -> Dashboard Live

Objectif :

- publier un message sur un broker MQTT
- laisser Render ingerer automatiquement le message
- visualiser la donnee dans le dashboard live

### 1. Configurer MQTT dans Render

Dans `Environment`, renseigne au minimum :

```text
MQTT_BROKER_HOST=broker.hivemq.com
MQTT_BROKER_PORT=1883
MQTT_TOPIC_PREFIX=electrogpt/telemetry
PUBLIC_BASE_URL=https://electrotechnique-gpt-tool.onrender.com
```

Si ton broker exige un login :

```text
MQTT_USERNAME=<user>
MQTT_PASSWORD=<password>
```

Puis redeploie le service.

### 2. Verifier que le connecteur MQTT est actif

Ouvre :

```text
https://electrotechnique-gpt-tool.onrender.com/connectors-status
```

Tu dois voir :

- `configured: true`
- `library_available: true`
- `connected: true` ou au moins pas d'erreur bloquante si le broker repond

### 3. Ouvrir le dashboard live

Ouvre :

```text
https://electrotechnique-gpt-tool.onrender.com/live-dashboard?channel=atelier-ligne-1
```

Le dashboard est pret a ecouter le canal `atelier-ligne-1`.

### 4. Publier un message MQTT de test

Topic a utiliser :

```text
electrogpt/telemetry/atelier-ligne-1
```

Payload JSON recommande :

```json
{
  "channel": "atelier-ligne-1",
  "values": {
    "temperature_c": 46.2,
    "current_a": 18.4,
    "voltage_v": 398.5,
    "power_factor": 0.91
  },
  "metadata": {
    "machine": "transformer-1",
    "publisher": "mqtt-test"
  }
}
```

### 5. Methode A. Test rapide avec Python

Depuis le repo :

```bash
pip install paho-mqtt
python examples/mqtt_publish.py --host broker.hivemq.com --channel atelier-ligne-1 --count 20
```

### 6. Methode B. Test rapide avec Node.js

Depuis le repo :

```bash
npm install mqtt
node examples/mqtt_publish.mjs
```

### 7. Methode C. Test avec Mosquitto CLI

Si `mosquitto_pub` est installe :

```bash
mosquitto_pub -h broker.hivemq.com -p 1883 -t electrogpt/telemetry/atelier-ligne-1 -m "{\"channel\":\"atelier-ligne-1\",\"values\":{\"temperature_c\":46.2,\"current_a\":18.4,\"voltage_v\":398.5}}"
```

### 8. Verifier que Render recoit bien les messages

Reviens sur :

```text
https://electrotechnique-gpt-tool.onrender.com/connectors-status
```

Tu dois voir :

- `messages_received` augmenter
- `telemetry_channels` contenir `atelier-ligne-1`

### 9. Verifier l'arrivee dans le dashboard

Dans :

```text
https://electrotechnique-gpt-tool.onrender.com/live-dashboard?channel=atelier-ligne-1
```

Tu dois voir :

- les courbes se construire
- le statut passer en actif
- les signaux `temperature_c`, `current_a`, `voltage_v` apparaitre

### 10. Verifier le flux brut si besoin

Tu peux aussi ecouter le flux SSE brut :

```text
https://electrotechnique-gpt-tool.onrender.com/telemetry-stream?channel=atelier-ligne-1
```

### 11. Si rien n'apparait

Verifier dans cet ordre :

- `MQTT_BROKER_HOST` et `MQTT_BROKER_PORT`
- le topic exact `electrogpt/telemetry/atelier-ligne-1`
- la valeur de `MQTT_TOPIC_PREFIX`
- que le broker accepte bien la connexion depuis Render
- que le service n'est pas en veille si tu es sur un plan `Free`
- que `connectors-status` montre `connected: true`

### 12. Variante sans MQTT

Si tu veux juste valider le dashboard sans broker, injecte une trame HTTP :

```bash
curl -X POST "https://electrotechnique-gpt-tool.onrender.com/telemetry-ingest" ^
  -H "Content-Type: application/json" ^
  -d "{\"channel\":\"atelier-ligne-1\",\"source\":\"http-test\",\"values\":{\"temperature_c\":46.2,\"current_a\":18.4}}"
```

Puis ouvre :

```text
https://electrotechnique-gpt-tool.onrender.com/live-dashboard?channel=atelier-ligne-1
```
