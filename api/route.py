import requests


def model_call(data, history):
    url = "http://localhost:11434/api/chat"

    payload = {
        "model": "qwen2.5:0.5b",
        "messages": history,
        "stream": False
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        return result["message"]

    except requests.exceptions.RequestException as e:
        print(f"API error: {e}")
        return None