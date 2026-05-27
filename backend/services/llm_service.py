import requests


OLLAMA_URL = "http://localhost:11434/api/generate"


def ask_mistral(prompt):

    payload = {
        "model": "mistral",
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload
    )

    # Debugging support
    if response.status_code != 200:

        return f"Ollama API Error: {response.text}"

    data = response.json()

    # Safe extraction
    return data.get(
        "response",
        "No response generated from model."
    )