import argparse
import json
import math
import os
import time

import paho.mqtt.client as mqtt


def create_client() -> mqtt.Client:
    if hasattr(mqtt, "CallbackAPIVersion"):
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="electrogpt-python-publisher")
    return mqtt.Client(client_id="electrogpt-python-publisher")


def build_payload(channel: str, sequence: int) -> dict:
    temperature = 45.0 + 3.5 * math.sin(sequence / 3.0)
    current = 18.0 + 2.2 * math.cos(sequence / 4.0)
    voltage = 398.0 + 4.0 * math.sin(sequence / 5.0)
    power_factor = 0.9 + 0.03 * math.sin(sequence / 6.0)
    return {
        "channel": channel,
        "values": {
            "temperature_c": round(temperature, 3),
            "current_a": round(current, 3),
            "voltage_v": round(voltage, 3),
            "power_factor": round(power_factor, 4),
        },
        "metadata": {
            "publisher": "python-example",
            "sequence": sequence,
            "machine": "transformer-1",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Publie des donnees MQTT pour le dashboard live ElectroGPT.")
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "broker.hivemq.com"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument("--topic-prefix", default=os.getenv("MQTT_TOPIC_PREFIX", "electrogpt/telemetry"))
    parser.add_argument("--channel", default=os.getenv("MQTT_CHANNEL", "atelier-ligne-1"))
    parser.add_argument("--count", type=int, default=20, help="Nombre de messages a publier")
    parser.add_argument("--interval", type=float, default=1.0, help="Intervalle entre deux publications en secondes")
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME", ""))
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD", ""))
    args = parser.parse_args()

    topic = f"{args.topic_prefix.strip('/')}/{args.channel}"
    client = create_client()
    if args.username:
        client.username_pw_set(args.username, args.password or None)

    client.connect(args.host, args.port, 60)
    client.loop_start()

    print(f"Publishing to topic: {topic}")
    try:
        for sequence in range(1, args.count + 1):
            payload = build_payload(args.channel, sequence)
            body = json.dumps(payload)
            client.publish(topic, body, qos=0, retain=False)
            print(f"[{sequence}/{args.count}] {body}")
            time.sleep(max(args.interval, 0.05))
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
