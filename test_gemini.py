from google import genai
import sys

API_KEY = "AIzaSyClLjMpDX9aFvDQrvy0IN3J1cSoabcIMkQ"
client = genai.Client(api_key=API_KEY)

models_to_test = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
]

for model in models_to_test:
    try:
        r = client.models.generate_content(model=model, contents="say hi")
        print(f"OK  {model}: {r.text[:40].strip()}")
    except Exception as e:
        err = str(e)[:80]
        print(f"ERR {model}: {err}")
