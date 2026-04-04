import mqtt from "mqtt";

const host = process.env.MQTT_HOST ?? "broker.hivemq.com";
const port = Number(process.env.MQTT_PORT ?? "1883");
const topicPrefix = (process.env.MQTT_TOPIC_PREFIX ?? "electrogpt/telemetry").replace(/\/+$/, "");
const channel = process.env.MQTT_CHANNEL ?? "atelier-ligne-1";
const username = process.env.MQTT_USERNAME ?? "";
const password = process.env.MQTT_PASSWORD ?? "";
const count = Number(process.env.MQTT_COUNT ?? "20");
const intervalMs = Number(process.env.MQTT_INTERVAL_MS ?? "1000");

const topic = `${topicPrefix}/${channel}`;
const client = mqtt.connect(`mqtt://${host}:${port}`, {
  username: username || undefined,
  password: password || undefined,
  keepalive: 60,
});

function buildPayload(sequence) {
  return {
    channel,
    values: {
      temperature_c: Number((45 + 3.5 * Math.sin(sequence / 3)).toFixed(3)),
      current_a: Number((18 + 2.2 * Math.cos(sequence / 4)).toFixed(3)),
      voltage_v: Number((398 + 4 * Math.sin(sequence / 5)).toFixed(3)),
      power_factor: Number((0.9 + 0.03 * Math.sin(sequence / 6)).toFixed(4)),
    },
    metadata: {
      publisher: "node-example",
      sequence,
      machine: "transformer-1",
    },
  };
}

client.on("connect", () => {
  console.log(`Publishing to topic: ${topic}`);
  let sequence = 1;

  const timer = setInterval(() => {
    const payload = buildPayload(sequence);
    const body = JSON.stringify(payload);
    client.publish(topic, body, { qos: 0, retain: false });
    console.log(`[${sequence}/${count}] ${body}`);

    sequence += 1;
    if (sequence > count) {
      clearInterval(timer);
      setTimeout(() => client.end(), 300);
    }
  }, Math.max(intervalMs, 50));
});

client.on("error", (error) => {
  console.error("MQTT error:", error.message);
  client.end(true);
});
