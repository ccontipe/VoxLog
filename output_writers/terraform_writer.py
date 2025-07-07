import logging
import os
from tkinter import messagebox

logger = logging.getLogger(__name__)

def save_terraform_files(terraform_files: dict, output_dir: str, cloud_platform: str, file_name_without_ext: str):
    """
    Salva os códigos Terraform em arquivos .tf separados, dentro de um subdiretório específico.

    Args:
        terraform_files (dict): Dicionário onde as chaves são nomes de arquivos Terraform (ex: "main.tf")
                                e os valores são o conteúdo dessas strings.
        output_dir (str): O diretório base onde a subpasta Terraform será criada.
        cloud_platform (str): O nome da plataforma cloud (ex: "Azure", "AWS", "GCP").
        file_name_without_ext (str): Nome base do arquivo original para nomear o subdiretório.

    Returns:
        bool: True se o salvamento foi bem-sucedido para todos os arquivos, False caso contrário.
    """
    if not terraform_files:
        logger.info("[Terraform Writer] Nenhuns arquivos Terraform para salvar.")
        return True # Considerado sucesso se não há nada para salvar

    tf_subdir = os.path.join(output_dir, f"Terraform_{cloud_platform}_{file_name_without_ext}")
    
    try:
        os.makedirs(tf_subdir, exist_ok=True) # Criar diretório para arquivos Terraform
        logger.info(f"[Terraform Writer] Diretório Terraform criado/verificado: {tf_subdir}")
    except Exception as e:
        logger.error(f"[Terraform Writer] Erro ao criar o diretório Terraform '{tf_subdir}': {e}", exc_info=True)
        messagebox.showerror("Erro ao Salvar Terraform", f"Não foi possível criar o diretório para os arquivos Terraform: {e}")
        return False

    success = True
    for tf_filename, tf_content in terraform_files.items():
        try:
            tf_path = os.path.join(tf_subdir, tf_filename)
            with open(tf_path, "w", encoding="utf-8") as f:
                f.write(tf_content)
            logger.info(f"[Terraform Writer] Arquivo Terraform '{tf_filename}' salvo em: {tf_path}")
        except Exception as e:
            logger.error(f"[Terraform Writer] Erro ao salvar o arquivo Terraform '{tf_filename}': {e}", exc_info=True)
            messagebox.showerror("Erro ao Salvar Terraform", f"Não foi possível salvar o arquivo Terraform '{tf_filename}': {e}")
            success = False
            
    if success and terraform_files: # Só mostra esta messagebox se houve arquivos e todos foram salvos
        messagebox.showinfo("Arquivos Gerados", f"{len(terraform_files)} arquivos Terraform gerados e salvos em '{tf_subdir}'.")

    return success