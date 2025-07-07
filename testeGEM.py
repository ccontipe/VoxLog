import google.generativeai as genai

def exemplo_chamada():
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = "Responda: 1+1="
    resposta = model.generate_content(prompt)
    print(resposta.text)