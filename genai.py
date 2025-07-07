# Copyright (c) 2025 Cesar Contipelli Neto
# Todos os direitos reservados.
# Proibida a modificação e distribuição sem autorização do autor.

import google.generativeai as genai

for model in genai.list_models():
    print(model.name, "—", model.description)
