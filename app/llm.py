import os
from dotenv import load_dotenv

load_dotenv()

try:
    from groq import Groq
except ModuleNotFoundError:
    Groq = None

MODEL = "llama-3.1-8b-instant"

def ask_gemini(prompt: str) -> str:
    # Name kept as ask_gemini so no other file needs to change
    if Groq is None:
        raise RuntimeError(
            "The groq package is not installed. Install it or configure a compatible LLM client."
        )
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()
