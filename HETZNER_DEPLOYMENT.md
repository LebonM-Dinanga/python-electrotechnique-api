# Hetzner Cloud Deployment

Ce guide remplace le mode Render quand il faut un service toujours actif, plus de RAM/CPU, et des temps de reponse plus stables.

## Pourquoi Hetzner est plus adapte ici

Cette application n'est pas un simple endpoint HTTP stateless.

Elle gere aussi :

- du streaming SSE
- des WebSockets
- de la telemetry live
- du MQTT
- des calculs et simulations plus longs
- un etat en memoire pour certains canaux live

Sur un service gratuit a mise en veille, ce type d'application devient fragile. Un VPS Hetzner supprime ce probleme de cold start.

## Point d'architecture important

L'application conserve actuellement certains flux live en memoire Python.

Consequence :

- garde `UVICORN_WORKERS=1`
- n'essaie pas de scaler horizontalement cette version telle quelle

Si tu veux plus tard plusieurs workers ou plusieurs serveurs, il faudra externaliser cet etat vers Redis ou une base de donnees adaptee.

## Architecture recommandee

- 1 serveur Hetzner Cloud Ubuntu LTS
- 1 Primary IP publique
- 1 Firewall Hetzner
- Docker + Docker Compose
- Caddy en reverse proxy TLS
- l'API FastAPI dans un conteneur Python
- optionnel : 1 Volume Hetzner si tu veux separer le stockage du serveur

## Taille de serveur recommandee

Pour ce projet, je recommande de partir au minimum sur une machine avec assez de RAM pour :

- FastAPI + WebSockets + SSE
- calculs/simulations
- Caddy
- buffers telemetry

Choix pragmatique :

- demarrage : une instance reguliere confortable ou une instance dediee si tu veux privilegier les calculs CPU
- si tu comptes faire beaucoup de simulation, prefere une instance a ressources dediees

## Ports a ouvrir

Dans le Firewall Hetzner :

- `22/tcp` : seulement depuis ton IP d'administration
- `80/tcp` : public
- `443/tcp` : public

Tu n'as pas besoin d'ouvrir :

- `1883` en entree si l'application est cliente MQTT
- `502` en entree si l'application lit un equipement Modbus distant

## Preparation DNS

Pour eviter le probleme persistant du builder GPT avec un gros pack d'actions sur un seul domaine, la configuration recommandee sur Hetzner est :

- `api.lbmdinanga-tech.com` : sante, docs, endpoint general et fallback
- `wolfram.lbmdinanga-tech.com` : action calcul
- `research.lbmdinanga-tech.com` : action recherche
- `simulation.lbmdinanga-tech.com` : action simulation
- `realtime.lbmdinanga-tech.com` : action dashboard temps reel
- `diagnosis.lbmdinanga-tech.com` : action diagnostic
- `academic.lbmdinanga-tech.com` : action academic
- `thesis.lbmdinanga-tech.com` : action thesis
- `live.lbmdinanga-tech.com` : action live capteurs / automates

Tous ces sous-domaines pointent vers le meme VPS et le meme backend FastAPI. La separation est uniquement faite pour que le builder GPT voie plusieurs domaines d'actions distincts.

Avant le cutover :

1. cree un enregistrement `A` pour chaque sous-domaine vers l'IPv4 du serveur
2. cree un enregistrement `AAAA` pour chaque sous-domaine si tu utilises IPv6
3. baisse le TTL DNS a 300 secondes avant migration
4. verifie que tous les sous-domaines resolvent bien vers le VPS avant d'importer les actions

## Fichiers ajoutes pour Hetzner

- `Dockerfile`
- `docker-compose.hetzner.yml`
- `Caddyfile`

## Variables d'environnement a definir

Copie `.env.example` vers `.env`, puis adapte au serveur :

```text
APP_DOMAIN=api.lbmdinanga-tech.com
WOLFRAM_DOMAIN=wolfram.lbmdinanga-tech.com
RESEARCH_DOMAIN=research.lbmdinanga-tech.com
SIMULATION_DOMAIN=simulation.lbmdinanga-tech.com
REALTIME_DOMAIN=realtime.lbmdinanga-tech.com
DIAGNOSIS_DOMAIN=diagnosis.lbmdinanga-tech.com
ACADEMIC_DOMAIN=academic.lbmdinanga-tech.com
THESIS_DOMAIN=thesis.lbmdinanga-tech.com
LIVE_DOMAIN=live.lbmdinanga-tech.com
PUBLIC_BASE_URL=https://api.lbmdinanga-tech.com
CONTACT_EMAIL=ton-email@example.com
WOLFRAM_APP_ID=ta-cle-wolfram
ARXIV_DOMAIN_FILTER=electrical engineering
ALLOWED_ORIGINS=https://api.lbmdinanga-tech.com,https://wolfram.lbmdinanga-tech.com,https://research.lbmdinanga-tech.com,https://simulation.lbmdinanga-tech.com,https://realtime.lbmdinanga-tech.com,https://diagnosis.lbmdinanga-tech.com,https://academic.lbmdinanga-tech.com,https://thesis.lbmdinanga-tech.com,https://live.lbmdinanga-tech.com,http://127.0.0.1:8000,http://localhost:8000
PLUGIN_LOGO_URL=https://api.lbmdinanga-tech.com/static/logo.png
PLUGIN_LEGAL_URL=https://api.lbmdinanga-tech.com/legal
MAX_TELEMETRY_POINTS=600
MQTT_BROKER_HOST=
MQTT_BROKER_PORT=1883
MQTT_TOPIC_PREFIX=electrogpt/telemetry
UVICORN_WORKERS=1
```

## Installation sur le serveur

### 1. Creer le serveur

Dans Hetzner Console :

1. cree un serveur Ubuntu LTS
2. ajoute un Primary IP public
3. attache un Firewall
4. active les Backups si tu veux un retour arriere rapide

### 2. Installer Docker

Connecte-toi en SSH puis lance :

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker compose version
```

### 3. Recuperer le projet

```bash
cd /opt
sudo mkdir -p electrogpt
sudo chown $USER:$USER electrogpt
git clone <URL_DU_REPO> /opt/electrogpt
cd /opt/electrogpt
cp .env.example .env
```

Edite ensuite `.env`.

### 4. Lancer la stack

```bash
docker compose -f docker-compose.hetzner.yml up -d --build
```

### 5. Verifier

```bash
docker compose -f docker-compose.hetzner.yml ps
docker compose -f docker-compose.hetzner.yml logs -f api
docker compose -f docker-compose.hetzner.yml logs -f caddy
```

Quand Caddy a obtenu le certificat TLS :

- `https://<APP_DOMAIN>/health`
- `https://<APP_DOMAIN>/docs`
- `https://<APP_DOMAIN>/openapi.specialized.json`
- `https://<WOLFRAM_DOMAIN>/openapi.wolfram.json`
- `https://<RESEARCH_DOMAIN>/openapi.research.json`
- `https://<SIMULATION_DOMAIN>/openapi.simulation.json`
- `https://<REALTIME_DOMAIN>/openapi.realtime.json`
- `https://<DIAGNOSIS_DOMAIN>/openapi.diagnosis.json`
- `https://<ACADEMIC_DOMAIN>/openapi.academic.json`
- `https://<THESIS_DOMAIN>/openapi.thesis.json`
- `https://<LIVE_DOMAIN>/openapi.live.json`

## Migration depuis Render

Ordre recommande :

1. deploie sur Hetzner sans couper Render
2. verifie tous les endpoints critiques sur le nouveau domaine
3. reconfigure le builder GPT vers le nouveau domaine
4. teste dans une nouvelle conversation
5. bascule le DNS final si besoin
6. garde Render 24h a 48h comme rollback

## Tests minimum avant bascule

### Sante et schema

- `/health`
- `/docs`
- `/openapi.specialized.json`
- `/openapi.chatgpt.json`
- `/legal`

### Schemas d'actions separees

- `https://wolfram.lbmdinanga-tech.com/openapi.wolfram.json`
- `https://research.lbmdinanga-tech.com/openapi.research.json`
- `https://simulation.lbmdinanga-tech.com/openapi.simulation.json`
- `https://realtime.lbmdinanga-tech.com/openapi.realtime.json`
- `https://diagnosis.lbmdinanga-tech.com/openapi.diagnosis.json`
- `https://academic.lbmdinanga-tech.com/openapi.academic.json`
- `https://thesis.lbmdinanga-tech.com/openapi.thesis.json`
- `https://live.lbmdinanga-tech.com/openapi.live.json`

### Outils

- calcul : `/action-wolfram?query=integrate x^2`
- recherche : `/action-research?query=transformer losses`
- simulation : `/action-simulation?query=simulate rc r=1000 c=0.001 v=5 t=5`
- realtime : `/action-realtime?query=dashboard temps reel pour simulate rc r=1000 c=0.001 v=5 t=5`
- diagnostic : `/action-diagnosis?query=Pourquoi mon transformateur chauffe et declenche sous charge`
- academic : `/action-academic?query=Donne moi 3 sujets originaux de TFE en electrotechnique avec leur problematique`
- thesis : `/action-thesis?query=Workflow complet de these sur les microreseaux`
- live : `/action-live?query=Je veux connecter un automate via Modbus TCP et MQTT`

## Sauvegarde et persistance

Point important :

- les Backups/Snapshots serveur Hetzner ne sauvegardent pas les Volumes attaches
- si tu utilises un Volume pour des donnees persistantes, il faut une strategie de sauvegarde en plus

Minimum recommande :

- Backups Hetzner actives sur le serveur
- Snapshot manuel avant gros changement
- sauvegarde externe des fichiers `.env`

## Mise a jour

```bash
cd /opt/electrogpt
git pull
docker compose -f docker-compose.hetzner.yml up -d --build
```

## Rollback

Deux options rapides :

- redeployer le commit precedent
- restaurer un Backup/Snapshot Hetzner

## Notes d'exploitation

- garde `UVICORN_WORKERS=1` tant que la telemetry live reste stockee en memoire
- WebSocket et SSE passent correctement derriere Caddy
- si tu veux plus de debit plus tard, le prochain vrai palier sera Redis + workers multiples

