import requests


OLLAMA_URL = "http://localhost:11434/api/generate"


def ask_mistral(prompt: str):

    payload = {
        "model": "mistral",
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload
    )

    data = response.json()

    return data["response"]