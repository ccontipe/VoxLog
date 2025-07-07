import re
import os
import logging
import subprocess
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

# 1. Parsing de blocos Terraform
def parse_terraform_blocks(gemini_output: str, cloud_provider: str) -> List[Dict]:
    """
    Extrai blocos ```terraform ... ``` do output da GEM.
    Tenta inferir tipo de recurso pelo conteúdo para sugestão de nome.
    """
    blocks = []
    matches = re.finditer(r"```terraform(.*?)```", gemini_output, re.DOTALL | re.IGNORECASE)
    for match in matches:
        block_content = match.group(1).strip()
        # Inferir tipo de recurso para nomeação do arquivo
        resource_match = re.search(r'resource\s+"([^"]+)"\s+"([^"]+)"', block_content)
        if resource_match:
            resource_type = resource_match.group(1)
            suggested_name = f"{cloud_provider.lower()}_{resource_type}"
        else:
            suggested_name = f"{cloud_provider.lower()}_resource"
        blocks.append({'content': block_content, 'suggested_name': suggested_name})
    return blocks

# 2. Validação mínima do bloco Terraform
def validate_terraform_block(block_content: str, cloud_provider: str) -> Tuple[bool, List[str]]:
    """
    Checa presença de bloco provider, pelo menos um resource, e se o provider corresponde ao esperado.
    """
    issues = []
    provider_pattern = {
        'aws': r'provider\s+"aws"',
        'azure': r'provider\s+"azurerm"',
        'gcp': r'provider\s+"google"',
    }
    # Verifica se existe bloco provider correto
    prov_pat = provider_pattern.get(cloud_provider.lower())
    if prov_pat and not re.search(prov_pat, block_content, re.IGNORECASE):
        issues.append(f"Faltando bloco provider '{cloud_provider}'")
    # Verifica se há pelo menos um resource
    if not re.search(r'resource\s+"[^"]+"\s+"[^"]+"', block_content):
        issues.append("Faltando bloco resource")
    # (Opcional) Pode incluir checagem por blocos output, variable, etc.
    return (len(issues) == 0), issues

# 3. Salvamento do arquivo .tf
def salvar_terraform(block_content: str, filename: str):
    """
    Salva o bloco de código Terraform no arquivo especificado.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(block_content)
    logger.info(f"Arquivo Terraform salvo: {filename}")

# 4. Lint e validação com Terraform CLI (opcional)
def terraform_cli_available() -> bool:
    """
    Verifica se o terraform CLI está disponível no sistema.
    """
    try:
        result = subprocess.run(["terraform", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return result.returncode == 0
    except Exception:
        return False

def run_terraform_validate(tf_file_path: str) -> bool:
    """
    Roda 'terraform validate' no arquivo especificado (precisa de diretório inicializado!).
    Retorna True se valida, False se não.
    """
    tf_dir = os.path.dirname(tf_file_path)
    try:
        # Inicializa, se necessário
        subprocess.run(["terraform", "init", "-input=false"], cwd=tf_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        # Valida
        result = subprocess.run(["terraform", "validate"], cwd=tf_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return result.returncode == 0
    except Exception as e:
        logger.warning(f"Falha ao rodar terraform validate em {tf_file_path}: {e}")
        return False

# 5. Pipeline principal: geração, validação e salvamento dos artefatos
def generate_terraform_artifacts(gemini_output: str, output_dir: str, cloud_provider: str, run_lint: bool = True):
    """
    Pipeline completo para extração, validação e salvamento dos blocos Terraform.
    """
    logger.info("[TerraformGen] Iniciando pipeline de artefatos Terraform...")
    blocks = parse_terraform_blocks(gemini_output, cloud_provider)
    if not blocks:
        logger.warning("[TerraformGen] Nenhum bloco Terraform encontrado na saída da GEM.")
        return []
    logger.info(f"[TerraformGen] {len(blocks)} blocos Terraform encontrados.")
    all_files = []
    for idx, block_info in enumerate(blocks, 1):
        valid, issues = validate_terraform_block(block_info['content'], cloud_provider)
        filename = os.path.join(output_dir, f"{block_info['suggested_name']}_{idx}.tf")
        if valid:
            salvar_terraform(block_info['content'], filename)
            logger.info(f"[TerraformGen] Bloco válido salvo em: {filename}")
            all_files.append(filename)
            if run_lint and terraform_cli_available():
                passed = run_terraform_validate(filename)
                if passed:
                    logger.info(f"[TerraformGen] {filename} validado com sucesso pelo Terraform CLI.")
                else:
                    logger.warning(f"[TerraformGen] {filename} NÃO passou no terraform validate!")
        else:
            logger.error(f"[TerraformGen] Bloco inválido: {filename}. Problemas: {issues}")
    logger.info("[TerraformGen] Pipeline concluído.")
    return all_files

# 6. Exemplo de uso (descomente para rodar em script independente)
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     gemini_output = "... (saída da GEM aqui) ..."
#     output_dir = "output_terraform"
#     cloud_provider = "aws"
#     generate_terraform_artifacts(gemini_output,
