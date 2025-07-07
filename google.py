# Copyright (c) 2025 Cesar Contipelli Neto
# Todos os direitos reservados.
# Proibida a modificação e distribuição sem autorização do autor.

import google.generativeai as genai
genai.configure(api_key="AIzaSyBrFE5AJuUzdRc9ysfasimGTfeowywvkFs")
model = genai.GenerativeModel("gemini-1.5-flash")
print(model)
response = model.generate_content("Olá, Gemini")
print(response)
