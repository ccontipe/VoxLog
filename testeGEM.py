# Copyright (c) 2025 Cesar Contipelli Neto
# Todos os direitos reservados.
# Proibida a modificação e distribuição sem autorização do autor.

import google.generativeai as genai

def exemplo_chamada():
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = "Responda: 1+1="
    resposta = model.generate_content(prompt)
    print(resposta.text)