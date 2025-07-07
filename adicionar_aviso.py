# Copyright (c) 2025 Cesar Contipelli Neto
# Todos os direitos reservados.
# Proibida a modificação e distribuição sem autorização do autor.

import os

# Aviso legal a ser inserido
aviso = (
    "# Copyright (c) 2025 Cesar Contipelli Neto\n"
    "# Todos os direitos reservados.\n"
    "# Proibida a modificação e distribuição sem autorização do autor.\n"
)

def inserir_aviso_em_py(root_dir):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(dirpath, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                # Evita inserir múltiplas vezes
                if not conteudo.lstrip().startswith('# Copyright (c) 2025 Cesar Contipelli Neto'):
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(aviso + '\n' + conteudo)
                    print(f"Aviso inserido em: {filepath}")
                else:
                    print(f"Aviso já existente em: {filepath}")

if __name__ == "__main__":
    inserir_aviso_em_py('.')
    print("Processo concluído.")
