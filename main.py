from fastapi import FastAPI
import requests

app = FastAPI()

@app.get("/")
def home():
    return {"status": "ok", "message": "API Python électrotechnique active"}

@app.get("/wolfram")
def wolfram_query(input: str):
    APP_ID = "LR29UEPJY6"

    url = "https://api.wolframalpha.com/v1/result"
    params = {
        "i": input,
        "appid": APP_ID
    }

    response = requests.get(url, params=params)

    return {
        "question": input,
        "result": response.text
    }