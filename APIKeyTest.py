import google.generativeai as genai
import os

API_KEY = os.getenv("GOOGLE_API_KEY") # Ou a sua API Key direta
genai.configure(api_key=API_KEY)

print("Modelos disponíveis que suportam 'generateContent':")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(f"Nome: {m.name}, Display Name: {m.display_name}")