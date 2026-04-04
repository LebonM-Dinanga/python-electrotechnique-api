# MQTT Live Examples

Ces exemples publient des donnees MQTT compatibles avec le dashboard live de l'API.

Topic par defaut :

```text
electrogpt/telemetry/atelier-ligne-1
```

Dashboard a ouvrir pendant le test :

```text
https://electrotechnique-gpt-tool.onrender.com/live-dashboard?channel=atelier-ligne-1
```

## Python

Installation locale :

```bash
pip install paho-mqtt
```

Execution :

```bash
python examples/mqtt_publish.py --host broker.hivemq.com --channel atelier-ligne-1 --count 20
```

## Node.js

Installation locale :

```bash
npm install mqtt
```

Execution :

```bash
node examples/mqtt_publish.mjs
```

## Broker avec authentification

Si ton broker exige des identifiants, ajoute simplement :

```bash
--username <user> --password <pass>
```

ou configure ces variables d'environnement :

```text
MQTT_USERNAME
MQTT_PASSWORD
MQTT_HOST
MQTT_PORT
MQTT_TOPIC_PREFIX
MQTT_CHANNEL
```
