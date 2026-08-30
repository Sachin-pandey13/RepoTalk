import requests


OLLAMA_URL = "http://localhost:11434/api/generate"


def ask_mistral(prompt):

    payload = {
        "model": "mistral",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            return f"Ollama API Error: {response.text}"

        data = response.json()

        return data.get(
            "response",
            "No response generated from model."
        )
    except Exception as e:
        return f"Ollama Connection Error: {str(e)}"