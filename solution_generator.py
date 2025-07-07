# Copyright (c) 2025 Cesar Contipelli Neto
# Todos os direitos reservados.
# Proibida a modificação e distribuição sem autorização do autor.

import logging
import os
import re
from tkinter import messagebox

# Importar os módulos específicos de geração de solução (azu, aws, gcp)
try:
    from solution_modules import solution_generator_azu
    from solution_modules import solution_generator_aws
    from solution_modules import solution_generator_gcp
except ImportError as e:
    logging.critical(f"Erro: Um ou mais módulos específicos de solução (solution_modules) não foram encontrados: {e}. "
                     "Verifique a estrutura de pastas e se os arquivos estão corretos.")
    messagebox.showerror("Erro de Módulos de Solução",
                         f"Não foi possível carregar os módulos de geração de solução. "
                         f"Verifique se a pasta 'solution_modules' existe e contém os arquivos solution_generator_*.py. Erro: {e}")
    solution_generator_azu = None
    solution_generator_aws = None
    solution_generator_gcp = None

# Importar os novos módulos de escrita de saída
try:
    from output_writers import plantuml_writer
    from output_writers import terraform_writer
except ImportError as e:
    logging.critical(f"Erro: Um ou mais módulos de escrita (output_writers) não foram encontrados: {e}. "
                     "Verifique a estrutura de pastas e se os arquivos estão corretos.")
    messagebox.showerror("Erro de Módulos de Escrita",
                         f"Não foi possível carregar os módulos de escrita de saída. "
                         f"Verifique se a pasta 'output_writers' existe e contém os arquivos writer.py. Erro: {e}")
    plantuml_writer = None
    terraform_writer = None


logger = logging.getLogger(__name__)

def parse_solution_output(gem_output):
    """
    Analisa a string de saída da GEM para extrair o texto principal,
    códigos PlantUML e códigos Terraform.
    O formato esperado é definido no prompt de get_solution_prompt de cada plataforma.
    """
    solution_text = ""
    plantuml_diagrams = {}
    terraform_files = {}

    # Regex para capturar a seção de texto principal da solução
    # Tudo antes do primeiro cabeçalho de PlantUML ou Terraform
    main_text_match = re.search(r"^(.*?)(?=\n#### Diagrama PlantUML:|\n#### Arquivo Terraform:|$)", gem_output, re.DOTALL)
    if main_text_match:
        solution_text = main_text_match.group(1).strip()
        # Remove o cabeçalho "### Proposta de Solução Técnica: Projeto [Nome do Projeto] em [Plataforma]"
        solution_text = re.sub(r"### Proposta de Solução Técnica:.*?\n", "", solution_text, count=1, flags=re.DOTALL)
        # Remove a linha "---" se estiver no início
        if solution_text.startswith("---"):
            solution_text = solution_text[3:].strip()
        
        # Ocasionalmente, o Gemini pode incluir "```markdown" no início da resposta geral, remova se presente
        if solution_text.startswith("```markdown"):
            solution_text = solution_text[len("```markdown"):].strip()
        if solution_text.endswith("```"):
            solution_text = solution_text[:-3].strip()


    # Regex para PlantUML
    # Adicionando todos os tipos de diagramas que esperamos e capturando o nome
    plantuml_pattern = re.compile(
        r"#### Diagrama PlantUML: (C1 Contexto|C2 Contêineres|C3 Componentes|Sequência)\s*\n```plantuml\n(.*?)\n```",
        re.DOTALL
    )
    for match in plantuml_pattern.finditer(gem_output):
        # Limpa o nome para o arquivo (ex: "C1 Contexto" -> "C1-Contexto")
        diagram_type_raw = match.group(1)
        # Mais robusto para nomes de arquivo: substitui espaços por hífens e remove termos específicos se necessário
        diagram_name_for_file = diagram_type_raw.replace(" ", "-").replace(" do Sistema", "").replace("Contêineres", "Container").replace("Componentes", "Component").replace("(Microsserviços)", "").strip('-')
        plantuml_code = match.group(2).strip()
        plantuml_diagrams[diagram_name_for_file] = plantuml_code
    
    # Regex para Terraform
    terraform_pattern = re.compile(
        r"#### Arquivo Terraform: (\w+\.tf)\s*\n```terraform\n(.*?)\n```",
        re.DOTALL
    )
    for match in terraform_pattern.finditer(gem_output):
        filename = match.group(1).strip()
        file_content = match.group(2).strip()
        terraform_files[filename] = file_content

    return solution_text, plantuml_diagrams, terraform_files


def generate_solution(transcription_text, cloud_platform, api_key, output_dir, file_name_without_ext):
    """
    Orquestra a geração da solução técnica para a plataforma cloud selecionada,
    chamando a GEM e os módulos de escrita de saída.

    Args:
        transcription_text (str): O texto transcrito do áudio.
        cloud_platform (str): A plataforma cloud selecionada ("Azure", "AWS", "GCP").
        api_key (str): A chave da API do Google Gemini.
        output_dir (str): Diretório base para salvar os arquivos gerados.
        file_name_without_ext (str): Nome base do arquivo de áudio original para naming.

    Returns:
        tuple: (texto_solucao_principal, dict_plantuml_diagrams, dict_terraform_files)
               ou (None, None, None) em caso de erro.
    """
    logger.info(f"[Módulo Solução] Iniciando geração de solução para plataforma: {cloud_platform}")

    gem_caller_func = None
    get_prompt_func = None

    # Seleciona o módulo de plataforma correto
    if cloud_platform == "Azure":
        if solution_generator_azu is not None:
            gem_caller_func = solution_generator_azu.call_gemini_api_azure
            get_prompt_func = solution_generator_azu.get_solution_prompt_azure
        else:
            logger.error("Módulo solution_generator_azu.py não disponível.")
            return None, None, None
    elif cloud_platform == "AWS":
        if solution_generator_aws is not None:
            gem_caller_func = solution_generator_aws.call_gemini_api_aws
            get_prompt_func = solution_generator_aws.get_solution_prompt_aws
        else:
            logger.error("Módulo solution_generator_aws.py não disponível.")
            return None, None, None
    elif cloud_platform == "GCP":
        if solution_generator_gcp is not None:
            gem_caller_func = solution_generator_gcp.call_gemini_api_gcp
            get_prompt_func = solution_generator_gcp.get_solution_prompt_gcp
        else:
            logger.error("Módulo solution_generator_gcp.py não disponível.")
            return None, None, None
    else:
        messagebox.showerror("Plataforma Inválida", f"Plataforma '{cloud_platform}' não suportada para geração de solução.")
        logger.error(f"Plataforma '{cloud_platform}' não suportada.")
        return None, None, None

    if gem_caller_func is None:
        messagebox.showerror("Erro de Geração de Solução", "O gerador de solução para a plataforma selecionada não pôde ser carregado.")
        return None, None, None

    try:
        # 1. Obter o prompt específico da plataforma
        full_gem_prompt = get_prompt_func(transcription_text)

        # 2. Chamar a API da GEM usando a função específica
        logger.info(f"[Módulo Solução] Chamando a GEM para gerar a solução ({cloud_platform})...")
        full_gem_solution_output = gem_caller_func(full_gem_prompt, "Geração de Solução", api_key)
        
        if not full_gem_solution_output:
            logger.warning(f"[Módulo Solução] A GEM não retornou conteúdo para a solução em {cloud_platform}.")
            messagebox.showwarning("Geração de Solução", f"A GEM não conseguiu gerar a solução para {cloud_platform}.")
            return None, None, None

        # 3. Parsear a saída completa da GEM
        logger.info("[Módulo Solução] Parseando a saída da GEM.")
        solution_text, plantuml_diagrams, terraform_files = parse_solution_output(full_gem_solution_output)

        # 4. Salvar os arquivos gerados usando os novos módulos de escrita
        
        # Salvar texto principal da solução
        solution_output_path = os.path.join(output_dir, f"GEM - Solucao Tecnica ({cloud_platform}) {file_name_without_ext}.txt")
        with open(solution_output_path, "w", encoding="utf-8") as f:
            f.write(solution_text)
        logger.info(f"[Módulo Solução] Solução Técnica principal salva em: {solution_output_path}")

        # Salvar diagramas PlantUML usando o plantuml_writer
        if plantuml_writer is not None:
            plantuml_writer.save_plantuml_diagrams(plantuml_diagrams, output_dir, file_name_without_ext)
        else:
            logger.warning("[Módulo Solução] plantuml_writer não disponível. Pulando salvamento de PlantUML.")
            messagebox.showwarning("Geração de Solução", "Módulo de escrita PlantUML não carregado. Diagramas não serão salvos.")


        # Salvar arquivos Terraform usando o terraform_writer
        if terraform_writer is not None:
            terraform_writer.save_terraform_files(terraform_files, output_dir, cloud_platform, file_name_without_ext)
        else:
            logger.warning("[Módulo Solução] terraform_writer não disponível. Pulando salvamento de Terraform.")
            messagebox.showwarning("Geração de Solução", "Módulo de escrita Terraform não carregado. Scripts Terraform não serão salvos.")

        logger.info(f"[Módulo Solução] Geração de solução para {cloud_platform} concluída.")
        return solution_text, plantuml_diagrams, terraform_files

    except Exception as e:
        logger.error(f"[Módulo Solução] Ocorreu um erro durante a geração da solução: {e}", exc_info=True)
        messagebox.showerror("Erro na Geração de Solução", f"Ocorreu um erro ao gerar a solução técnica: {e}")
        return None, None, None
