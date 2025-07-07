# Copyright (c) 2025 Cesar Contipelli Neto
# Todos os direitos reservados.
# Proibida a modificação e distribuição sem autorização do autor.

def listar_modelos(api_key):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    for m in genai.list_models():
        print(f"ID: {m.name} | Desc: {getattr(m, 'description', 'Sem descrição')} | Métodos: {getattr(m, 'supported_generation_methods', [])}")

# Exemplo de uso:
listar_modelos("AIzaSyBrFE5AJuUzdRc9ysfasimGTfeowywvkFs")
