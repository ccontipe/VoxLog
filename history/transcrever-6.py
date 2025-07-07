import subprocess
import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import time
import logging

# --- Configuração do Logging ---
LOG_FILE = "voxLOG.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- Funções de Instalação e Importação ---
def install_package(package):
    try:
        logger.info(f"Tentando instalar o pacote: {package}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--user"])
        logger.info(f"Pacote '{package}' instalado com sucesso.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao instalar o pacote '{package}': {e}", exc_info=True)
        print("Certifique-se de ter permissão de escrita ou execute como administrador, se necessário.")
        messagebox.showerror("Erro de Instalação", f"Falha ao instalar o pacote '{package}'. Por favor, tente instalar manualmente ou execute o script com permissões adequadas.")
        return False
    except Exception as e:
        logger.critical(f"Ocorreu uma exceção crítica ao instalar '{package}': {e}", exc_info=True)
        messagebox.showerror("Erro de Instalação", f"Ocorreu um erro inesperado ao instalar '{package}': {e}")
        return False

# Tenta importar faster_whisper, torch e google.generativeai globalmente.
try:
    from faster_whisper import WhisperModel
    import torch
    import google.generativeai as genai
    if not torch.cuda.is_available():
        logger.warning("Aviso: CUDA não está disponível. A transcrição será executada na CPU, mesmo se a GPU for selecionada.")
except ImportError:
    logger.warning("Módulos necessários não encontrados. Iniciando instalação automática...")
    if not install_package("faster-whisper"):
        logger.error("Falha na instalação de faster-whisper. Encerrando.")
        sys.exit(1)
    if not install_package("torch"):
        logger.error("Falha na instalação de torch. Encerrando.")
        sys.exit(1)
    if not install_package("google-generativeai"):
        logger.error("Falha na instalação de google-generativeai. Encerrando.")
        sys.exit(1)

    try:
        from faster_whisper import WhisperModel
        import torch
        import google.generativeai as genai
    except ImportError:
        logger.critical("Erro Fatal: Um ou mais módulos necessários não puderam ser instalados ou importados após a tentativa automática. Encerrando.")
        messagebox.showerror("Erro Fatal", "Módulos de transcrição e/ou análise não puderam ser instalados ou importados. Por favor, verifique sua conexão com a internet e permissões, e tente instalar manualmente: pip install faster-whisper torch google-generativeai")
        sys.exit(1)

# --- Configuração da API Google Gemini ---
API_KEY = "AIzaSyBrFE5AJuUzdRc9ysfasimGTfeowywvkFs" # Lembre-se de substituir pela sua chave real ou usar variável de ambiente
genai.configure(api_key=API_KEY)
logger.info("API Key do Gemini configurada.")

# --- Funções de geração de prompt ---
def get_analysis_prompt(transcription_text):
    """
    Retorna o prompt para a análise de transcrições.
    """
    return (
        "Você é um analista de negócios e sintetizador de informações altamente proficiente. "
        "Seu objetivo é analisar profundamente transcrições de áudio (reuniões, palestras, discussões) "
        "e extrair as informações mais relevantes, considerando os seguintes elementos essenciais:\n\n"
        "1.  **Problema/Situação Central:**\n"
        "    * Apresente o objetivo da solução em discussão, de forma clara e direta.\n"
        "    * Qual é o problema ou a situação principal que está sendo abordada? Descreva-o de forma clara e concisa.\n"
        "    * Quais são os pontos-chave discutidos que levam a essa situação?\n\n"
        "2.  **Entendimento Detalhado:**\n"
        "    * Apresente um resumo abrangente do contexto e do estado atual da discussão.\n"
        "    * Quais são os principais tópicos, conceitos ou informações apresentadas?\n\n"
        "3.  **Premissas (Claras e Ocultas):**\n"
        "    * **Premissas Explícitas:** Quais são as suposições declaradas ou fatos considerados verdadeiros que foram mencionados?\n"
        "    * **Premissas Implícitas/Ocultas:** Com base na linguagem, no tone, nos silêncios ou na forma como certos tópicos são tratados, quais são as suposições não declaradas que parecem estar em jogo? (Ex: 'assume-se que a equipe tem os recursos X', 'parece haver uma crença de que Y é impossível').\n\n"
        "4.  **Restrições (Técnicas, Orçamentárias, Temporais, etc.):**\n"
        "    * Quais são as limitações ou obstáculos claramente identificados (orçamento, prazo, recursos, tecnologia, políticas internas)?\n"
        "    * Há restrições sugeridas ou subentendidas que podem não ter sido explicitamente ditas, mas que são evidentes na discussão?\n\n"
        "5.  **Partes Interessadas (Stakeholders) e suas Perspectivas:**\n"
        "    * Quem são os principais participantes mencionados ou implicitamente relevantes na discussão?\n"
        "    * Quais são as diferentes perspectivas, preocupações ou interesses de cada parte interessada, conforme inferido da transcrição?\n\n"
        "6.  **Próximos Passos/Ações Sugeridas (se houver):**\n"
        "    * Quais são as ações, decisões ou recomendações que surgiram da discussão?\n\n"
        "7.  **Pontos de Dúvida/Esclarecimento Necessário:**\n"
        "    * Quais são as áreas da transcrição que permanecem ambíguas, contraditórias ou que requerem mais informações/esclarecimentos?\n\n"
        "**Formato da Saída:**\n"
        "A saída deve ser um texto estruturado, idealmente em formato Markdown para facilitar a leitura e a importação para outras ferramentas. Use cabeçalhos e listas para organizar as informações de forma lógica. Evite o uso de Functions e Logic Apps, focando na análise textual pura.\n\n"
        "**Instruções Adicionais:**\n"
        "* Seja o mais objetivo e imparcial possível na extração de informações.\n"
        "* Concentre-se em sintetizar, não apenas em repetir.\n"
        "* Se alguma seção não for aplicável ou não houver informações suficientes, indique-o claramente (ex: 'Nenhuma premissa oculta clara identificada').\n\n"
        f"Transcrição:\n{transcription_text}"
    )

def get_solution_prompt(transcription_text, cloud_platform="Azure"):
    """
    Retorna o prompt para a geração de proposta de solução técnica.
    Ajusta o prompt com base na plataforma cloud selecionada e inclui scripts Terraform.
    """
    base_prompt = (
        "Você é uma inteligência artificial especializada em arquitetura de soluções em nuvem. Sua missão PRINCIPAL é analisar as informações fornecidas por uma outra GEM (de análise de transcrição de textos de reuniões de negócios) e gerar uma proposta de solução técnica detalhada, **aderindo estritamente às diretrizes e padrões corporativos fornecidos, à plataforma cloud selecionada e incluindo scripts Terraform para a infraestrutura**.\n\n"
        "**Sua resposta DEVE seguir rigorosamente a seguinte estrutura:**\n\n"
        "---\n\n"
        "### Proposta de Solução Técnica: Projeto [Nome do Projeto - inferir da transcrição] em "
    )

    platform_specific_guidelines = ""
    plantuml_section = ""
    terraform_section = "" # NOVA SEÇÃO PARA TERRAFORM

    # --- Definições por Plataforma ---
    if cloud_platform == "Azure":
        base_prompt += "Azure\n\n"
        platform_specific_guidelines = (
            "**3. Diretrizes e Premissas Corporativas para a Solução (Azure - CRUCIAL):**\n\n"
            "   * **Ambiente de Implantação:** Qualquer novo serviço computacional proposto deve ser criado e implementado exclusivamente no Ambiente Azure.\n"
            "   * **Componentes e Serviços:** As soluções devem utilizar preferencialmente os componentes e serviços nativos disponíveis no Azure.\n"
            "   * **Padrão Corporativo:** O uso de Functions e Logic Apps é **desencorajado**. A solução corporativa e padrão é a utilização do **ARO (Azure Red Hat OpenShift)**.\n"
            "   * **Padrão de Artefato Corporativo:** O padrão de artefato inclui: Azure Tenant, On-premises, Acesso Externo, Hub Interno, Shared Infrastructure, VNETs e subscriptions associadas ao serviço Transacionar em cada ambiente (PR, HO, DV).\n\n"
            "**4. Visão Geral da Solução em Azure (Well-Architected Infrastructure):**\n\n"
            "   * Descreva a abordagem geral da solução em Azure.\n\n"
            "   * Mencione a adesão aos pilares do Azure Well-Architected Framework (Confiabilidade, Segurança, Excelência Operacional, Otimização de Custos, Eficiência de Desempenho).\n\n"
            "   * Identifique o padrão de arquitetura que mais se adapta ao problema identificado, preferencialmente utilizando **Microsserviços** devido às premissas de ARO.\n"
            "   * Explique como o padrão de arquitetura adotado (ex.: de microsserviços, Event-Driven Architecture, etc. ) é o modelo mais adequado para ser o pilar da solução.\n\n"
            "**5. Componentes da Solução Azure e sua Relação com o Problema/Solução:**\n\n"
            "   * Para cada componente Azure que você propor, siga este formato:\n\n"
            "       * **Nome do Componente Azure:** (Ex: Azure App Service / Azure Resources for Openshift (ARO))\n\n"
            "       * **Relação com o Problema/Solução:** Explique como o componente atende a um requisito ou resolve parte do problema. Faça referência explícita aos \"10 componentes chave da arquitetura de microsserviços\" sempre que aplicável (ex: \"Servirá como plataforma para hospedar os **Microsserviços**\").\n\n"
            "       * **Well-Architected:** Descreva como o componente contribui para os pilares do Well-Architected Framework (ex: \"Promove a **Excelência de Desempenho**...\"). **Para os microsserviços implantados no ARO, detalhe a contribuição individual de cada microsserviço para os pilares do Well-Architected Framework.**\n\n"
            "   * Detalhe os serviços Azure propostos e sua relação com a solução, bem como sua contribuição para os pilares do Well-Architected Framework, especialmente para os microsserviços implantados no ARO.\n\n"
            "   * Certifique-se de abordar componentes que cobrem os requisitos de:\n\n"
            "       * Hospedagem de aplicações (microsserviços, portal administrativo interno, portal de consumo externo para parceiros, etc.).\n\n"
            "       * Gerenciamento de APIs.\n\n"
            "       * Bancos de dados.\n\n"
            "       * Comunicação síncrona/assíncrona.\n\n"
            "       * Gerenciamento de identidades.\n\n"
            "       * Monitoramento.\n\n"
            "       * Balanceamento de carga e CDN.\n\n"
            "       * Conectividade híbrida (on-premises).\n\n"
            "       * Segurança de segredos.\n\n"
        )
        plantuml_section = (
            "**6. Diagramas PlantUML:**\n\n"
            "   * Gere o código PlantUML para os seguintes diagramas:\n\n"
            "       * **Diagrama C1 - Diagrama de Contexto do Sistema:** Mostra o sistema em seu ambiente, interagindo com usuários e sistemas externos.\n\n"
            "       * **Diagrama C2 - Diagrama de Contêineres:** Detalha as aplicações principais dentro do sistema, suas tecnologias e interações.\n\n"
            "       * **Diagrama C3 - Diagrama de Componentes (Microsserviços):** Apresenta todos os contêineres da solução e mostra seus componentes internos e interações. **Certifique-se de que não haja menção a \"fidelidade\" na construção deste arquivo.**\n\n"
            "       * **Diagrama de Sequência:** Um diagrama de sequência **OBRIGATÓRIO** detalhando as chamadas de API e os passos entre os sistemas.\n\n"
            "   * **Instruções para o PlantUML:**\n\n"
            "       * Utilize `!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml` (e variantes para C2/C3) no início de cada diagrama para usar a notação C4.\n\n"
            "       * Use `LAYOUT_WITH_LEGEND()` para incluir a legenda.\n\n"
            "       * Assegure-se de que os nomes dos elementos nos diagramas sejam consistentes com a descrição da solução.\n\n"
            "       * A entrada para esta GEM será a transcrição analisada. \n\n"
            "   * **Template sugerido para todos os diagramas C4:**\n\n"
            "   ```plantuml\n"
            "   @startuml <NomeDoDiagrama>\n\n"
            "   !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml)\n"
            "   !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml)\n"
            "   !include [https://raw.githubusercontent.com/plantuml/plantuml-stdlib/master/C4_Component.puml](https://raw.githubusercontent.com/plantuml/plantuml-stdlib/master/C4_Component.puml)\n"
            "   ' Opcional: !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Class.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Class.puml) para diagramas de código\n\n"
            "   LAYOUT_WITH_LEGEND()\n\n"
            "   title <Título do Diagrama>\n\n"
            "   ' SEUS ELEMENTOS C4 AQUI (Person, System, System_Boundary, Container, Container_Boundary, Component, etc.)\n\n"
            "   @enduml\n"
            "```\n\n"
        )
        terraform_section = (
            "**7. Scripts Terraform (Infraestrutura como Código - Azure):**\n\n"
            "Gere os blocos de código Terraform para provisionar os recursos Azure propostos, seguindo a estrutura de arquivos e as diretrizes de nomenclatura.\n"
            "Priorize o uso de módulos Terraform (ex: `network`, `compute`, `database`) para reutilização.\n\n"
            "#### `versions.tf`\n"
            "```terraform\n"
            "terraform {\n"
            "  required_providers {\n"
            "    azurerm = {\n"
            "      source  = \"hashicorp/azurerm\"\n"
            "      version = \"~> 3.0\"\n"
            "    }\n"
            "  }\n"
            "  required_version = \">= 1.0.0\"\n"
            "}\n"
            "```\n\n"
            "#### `providers.tf`\n"
            "```terraform\n"
            "provider \"azurerm\" {\n"
            "  features {}\n"
            "  # Autenticação via Azure CLI, Managed Identity ou Service Principal\n"
            "  # subscription_id = var.azure_subscription_id # Exemplo\n"
            "  # tenant_id       = var.azure_tenant_id       # Exemplo\n"
            "}\n"
            "```\n\n"
            "#### `variables.tf`\n"
            "```terraform\n"
            "variable \"project_name\" {\n"
            "  description = \"Nome do projeto/aplicação.\"\n"
            "  type        = string\n"
            "}\n\n"
            "variable \"environment\" {\n"
            "  description = \"Ambiente de implantação (ex: dev, prd, hml).\"\n"
            "  type        = string\n"
            "}\n\n"
            "variable \"location\" {\n"
            "  description = \"Região do Azure para os recursos.\"\n"
            "  type        = string\n"
            "  default     = \"East US\"\n"
            "}\n\n"
            "variable \"resource_group_name_prefix\" {\n"
            "  description = \"Prefixo para o nome do Resource Group.\"\n"
            "  type        = string\n"
            "  default     = \"rg\"\n"
            "}\n\n"
            "variable \"vnet_cidr\" {\n"
            "  description = \"CIDR da VNet principal.\"\n"
            "  type        = string\n"
            "  default     = \"10.0.0.0/16\"\n"
            "}\n\n"
            "variable \"aro_cluster_name_prefix\" {\n"
            "  description = \"Prefixo para o nome do cluster ARO.\"\n"
            "  type        = string\n"
            "  default     = \"aro-cluster\"\n"
            "}\n\n"
            "variable \"db_admin_username\" {\n"
            "  description = \"Nome de usuário para o administrador do banco de dados (referenciado de Key Vault).\"\n"
            "  type        = string\n"
            "  # Este valor não deve ser definido diretamente aqui. Deve ser buscado de um segredo.\n"
            "  default = \"dbadmin\"\n"
            "}\n\n"
            "# Exemplo de variável para referência a segredos via Key Vault\n"
            "variable \"db_admin_password_secret_name\" {\n"
            "  description = \"Nome do segredo no Key Vault para a senha do DB.\"\n"
            "  type        = string\n"
            "}\n\n"
            "variable \"key_vault_name\" {\n"
            "  description = \"Nome do Key Vault a ser criado ou referenciado.\"\n"
            "  type        = string\n"
            "}\n"
            "```\n\n"
            "#### `main.tf` (Exemplos de Recursos Principais)\n"
            "```terraform\n"
            "resource \"azurerm_resource_group\" \"main\" {\n"
            "  name     = \"${var.resource_group_name_prefix}-${var.project_name}-${var.environment}-${var.location}\"\n"
            "  location = var.location\n"
            "  tags = {\n"
            "    environment = var.environment\n"
            "    project     = var.project_name\n"
            "  }\n"
            "}\n\n"
            "# Exemplo de Módulo de Rede (modules/network)\n"
            "module \"network\" {\n"
            "  source = \"./modules/network\"\n"
            "  resource_group_name = azurerm_resource_group.main.name\n"
            "  location            = var.location\n"
            "  vnet_name           = \"vnet-${var.project_name}-${var.environment}\"\n"
            "  vnet_cidr           = var.vnet_cidr\n"
            "  subnet_cidrs        = {\n"
            "    \"subnet-aro\"    = \"10.0.1.0/24\"\n"
            "    \"subnet-db\"     = \"10.0.2.0/24\"\n"
            "    \"subnet-apim\"   = \"10.0.3.0/24\"\n"
            "  }\n"
            "  tags = azurerm_resource_group.main.tags\n"
            "}\n\n"
            "# Exemplo de Key Vault\n"
            "resource \"azurerm_key_vault\" \"main\" {\n"
            "  name                      = var.key_vault_name\n"
            "  location                  = azurerm_resource_group.main.location\n"
            "  resource_group_name       = azurerm_resource_group.main.name\n"
            "  tenant_id                 = data.azurerm_client_config.current.tenant_id\n"
            "  sku_name                  = \"standard\"\n"
            "  soft_delete_retention_days= 7\n"
            "  purge_protection_enabled  = false\n"
            "  tags                      = azurerm_resource_group.main.tags\n"
            "}\n\n"
            "data \"azurerm_client_config\" \"current\" {}\n\n"
            "# Exemplo de Azure Red Hat OpenShift Cluster (ARO)\n"
            "# Este é um recurso complexo e pode requerer mais variáveis e pré-requisitos.\n"
            "resource \"azurerm_redhat_open_shift_cluster\" \"aro_cluster\" {\n"
            "  name                = \"${var.aro_cluster_name_prefix}-${var.project_name}-${var.environment}\"\n"
            "  location            = azurerm_resource_group.main.location\n"
            "  resource_group_name = azurerm_resource_group.main.name\n"
            "  cluster_resource_group = \"${azurerm_resource_group.main.name}-aro\"\n"
            "  network_cidr        = \"10.0.0.0/22\"\n"
            "\n"
            "  master_profile {\n"
            "    vm_size   = \"Standard_D8s_v3\"\n"
            "    subnet_id = module.network.subnets[\"subnet-aro\"].id\n"
            "  }\n"
            "\n"
            "  worker_profile {\n"
            "    vm_size   = \"Standard_D4s_v3\"\n"
            "    disk_size_gb = 128\n"
            "    node_count = 3\n"
            "    subnet_id = module.network.subnets[\"subnet-aro\"].id\n"
            "  }\n"
            "\n"
            "  tags = azurerm_resource_group.main.tags\n"
            "}\n\n"
            "# Exemplo de Azure API Management\n"
            "resource \"azurerm_api_management_service\" \"api_gateway\" {\n"
            "  name                = \"apim-${var.project_name}-${var.environment}\"\n"
            "  location            = azurerm_resource_group.main.location\n"
            "  resource_group_name = azurerm_resource_group.main.name\n"
            "  publisher_name      = \"${var.project_name} API Publisher\"\n"
            "  publisher_email     = \"apis@${var.project_name}.com\"\n"
            "  sku_name            = \"Developer_1\"\n"
            "  tags                = azurerm_resource_group.main.tags\n"
            "}\n\n"
            "# Exemplo de Azure Database for PostgreSQL (Flexible Server)\n"
            "resource \"azurerm_postgresql_flexible_server\" \"db_core\" {\n"
            "  name                   = \"pg-${var.project_name}-${var.environment}\"\n"
            "  resource_group_name    = azurerm_resource_group.main.name\n"
            "  location               = azurerm_resource_group.main.location\n"
            "  version                = \"13\"\n"
            "  sku_name               = \"Standard_D2ds_v4\"\n"
            "  storage_mb             = 32768\n"
            "  administrator_login    = var.db_admin_username\n"
            "  administrator_password = azurerm_key_vault_secret.db_password.value # Referência ao segredo\n"
            "  backup_retention_days  = 7\n"
            "  geo_redundant_backup_enabled = false\n"
            "  tags                   = azurerm_resource_group.main.tags\n"
            "}\n\n"
            "# Exemplo de referência a um segredo do Key Vault\n"
            "resource \"azurerm_key_vault_secret\" \"db_password\" {\n"
            "  name         = var.db_admin_password_secret_name\n"
            "  value        = \"SenhaGeradaOuBuscadaDeAlgumLugarSeguro\" # Em um cenário real, não seria hardcoded\n"
            "  key_vault_id = azurerm_key_vault.main.id\n"
            "  content_type = \"text/plain\"\n"
            "  depends_on   = [azurerm_key_vault.main]\n"
            "}\n\n"
            "# Exemplo de módulo de rede (modules/network/main.tf)\n"
            "/*\n"
            "module \"network\" {\n"
            "  source = \"./modules/network\"\n"
            "  # ... variáveis do módulo de rede ...\n"
            "}\n"
            "*/\n"
            "```\n\n"
            "#### `outputs.tf`\n"
            "```terraform\n"
            "output \"resource_group_id\" {\n"
            "  description = \"ID do Resource Group criado.\"\n"
            "  value       = azurerm_resource_group.main.id\n"
            "}\n\n"
            "output \"aro_cluster_id\" {\n"
            "  description = \"ID do cluster Azure Red Hat OpenShift.\"\n"
            "  value       = azurerm_redhat_open_shift_cluster.aro_cluster.id\n"
            "}\n\n"
            "output \"api_management_gateway_url\" {\n"
            "  description = \"URL do API Management Gateway.\"\n"
            "  value       = azurerm_api_management_service.api_gateway.gateway_url\n"
            "}\n"
            "```\n"
        )

    elif cloud_platform == "AWS":
        base_prompt += "AWS\n\n"
        platform_specific_guidelines = (
            "**3. Diretrizes e Premissas Corporativas para a Solução (AWS - CRUCIAL):**\n\n"
            "   * **Ambiente de Implantação:** Qualquer novo serviço computacional proposto deve ser criado e implementado exclusivamente no Ambiente AWS.\n"
            "   * **Componentes e Serviços:** As soluções devem utilizar preferencialmente os componentes e serviços nativos disponíveis na AWS.\n"
            "   * **Padrão Corporativo:** Evite o uso de serviços *serverless* excessivamente granulares (ex: AWS Lambda para lógicas de negócio complexas que seriam microsserviços inteiros). Priorize soluções baseadas em contêineres gerenciados como **Amazon ECS** (com Fargate) ou **Amazon EKS** para microsserviços. Não utilize soluções proprietárias de outros provedores.\n"
            "   * **Padrão de Artefato Corporativo:** Adapte os conceitos de rede e segurança para o ambiente AWS, utilizando VPCs, subnets, Security Groups, IAM, etc. Considere modelos como multi-account strategy, Landing Zone e Control Tower.\n\n"
            "**4. Visão Geral da Solução em AWS (Well-Architected Framework):**\n\n"
            "   * Descreva a abordagem geral da solução em AWS.\n\n"
            "   * Mencione a adesão aos pilares do AWS Well-Architected Framework (Excelência Operacional, Segurança, Confiabilidade, Eficiência de Performance, Otimização de Custos, Sustentabilidade).\n\n"
            "   * Identifique o padrão de arquitetura que mais se adapta ao problema identificado, preferencialmente utilizando **Microsserviços**.\n"
            "   * Explique como o padrão de arquitetura adotado (ex.: de microsserviços, Event-Driven Architecture, etc. ) é o modelo mais adequado para ser o pilar da solução.\n\n"
            "**5. Componentes da Solução AWS e sua Relação com o Problema/Solução:**\n\n"
            "   * Para cada componente AWS que você propor, siga este formato:\n\n"
            "       * **Nome do Componente AWS:** (Ex: Amazon EC2 / Amazon ECS / Amazon S3)\n\n"
            "       * **Relação com o Problema/Solução:** Explique como o componente atende a um requisito ou resolve parte do problema. Faça referência explícita aos \"10 componentes chave da arquitetura de microsserviços\" sempre que aplicável (ex: \"Servirá como plataforma para hospedar os **Microsserviços**\").\n\n"
            "       * **Well-Architected:** Descreva como o componente contribui para os pilares do Well-Architected Framework (ex: \"Promove a **Confiabilidade** através de alta disponibilidade...\"). **Para os microsserviços implantados no ECS/EKS, detalhe a contribuição individual de cada microsserviço para os pilares do Well-Architected Framework.**\n\n"
            "   * Detalhe os serviços AWS propostos e sua relação com a solução, bem como sua contribuição para os pilares do Well-Architected Framework.\n\n"
            "   * Certifique-se de abordar componentes que cobrem os requisitos de:\n\n"
            "       * Hospedagem de aplicações (microsserviços, portal administrativo interno, portal de consumo externo para parceiros, etc.).\n\n"
            "       * Gerenciamento de APIs (API Gateway).\n\n"
            "       * Bancos de dados (RDS, DynamoDB, DocumentDB).\n\n"
            "       * Comunicação síncrona/assíncrona (SQS, SNS, EventBridge).\n\n"
            "       * Gerenciamento de identidades (IAM, Cognito).\n\n"
            "       * Monitoramento (CloudWatch, X-Ray).\n\n"
            "       * Balanceamento de carga e CDN (ELB, CloudFront).\n\n"
            "       * Conectividade híbrida (Direct Connect, VPN).\n\n"
            "       * Segurança de segredos (Secrets Manager).\n\n"
        )
        plantuml_section = (
            "**6. Diagramas PlantUML:**\n\n"
            "   * Gere o código PlantUML para os seguintes diagramas:\n\n"
            "       * **Diagrama C1 - Diagrama de Contexto do Sistema:** Mostra o sistema em seu ambiente, interagindo com usuários e sistemas externos.\n\n"
            "       * **Diagrama C2 - Diagrama de Contêineres:** Detalha as aplicações principais dentro do sistema, suas tecnologias e interações.\n\n"
            "       * **Diagrama C3 - Diagrama de Componentes (Microsserviços):** Apresenta todos os contêineres da solução e mostra seus componentes internos e interações. **Certifique-se de que não haja menção a \"fidelidade\" na construção deste arquivo.**\n\n"
            "       * **Diagrama de Sequência:** Um diagrama de sequência **OBRIGATÓRIO** detalhando as chamadas de API e os passos entre os sistemas.\n\n"
            "   * **Instruções para o PlantUML:**\n\n"
            "       * Utilize `!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml` (e variantes para C2/C3) no início de cada diagrama para usar a notação C4.\n\n"
            "       * Use `LAYOUT_WITH_LEGEND()` para incluir a legenda.\n\n"
            "       * Assegure-se de que os nomes dos elementos nos diagramas sejam consistentemente com a descrição da solução e reflitam os serviços AWS.\n\n"
            "       * A entrada para esta GEM será a transcrição analisada. \n\n"
            "   * **Template sugerido para todos os diagramas C4:**\n\n"
            "   ```plantuml\n"
            "   @startuml <NomeDoDiagrama>\n\n"
            "   !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml)\n"
            "   !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml)\n"
            "   !include [https://raw.githubusercontent.com/plantuml/plantuml-stdlib/master/C4_Component.puml](https://raw.githubusercontent.com/plantuml/plantuml-stdlib/master/C4_Component.puml)\n"
            "   ' Opcional: !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Class.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Class.puml) para diagramas de código\n\n"
            "   LAYOUT_WITH_LEGEND()\n\n"
            "   title <Título do Diagrama>\n\n"
            "   ' SEUS ELEMENTOS C4 AQUI (Person, System, System_Boundary, Container, Container_Boundary, Component, etc. com nomes de serviços AWS)\n\n"
            "   @enduml\n"
            "```\n\n"
        )
        terraform_section = (
            "**7. Scripts Terraform (Infraestrutura como Código - AWS):**\n\n"
            "Gere os blocos de código Terraform para provisionar os recursos AWS propostos, seguindo a estrutura de arquivos e as diretrizes de nomenclatura.\n"
            "Priorize o uso de módulos Terraform (ex: `vpc`, `eks`, `rds`) para reutilização.\n\n"
            "#### `versions.tf`\n"
            "```terraform\n"
            "terraform {\n"
            "  required_providers {\n"
            "    aws = {\n"
            "      source  = \"hashicorp/aws\"\n"
            "      version = \"~> 5.0\"\n"
            "    }\n"
            "  }\n"
            "  required_version = \">= 1.0.0\"\n"
            "}\n"
            "```\n\n"
            "#### `providers.tf`\n"
            "```terraform\n"
            "provider \"aws\" {\n"
            "  region = var.region\n"
            "  # Credenciais configuradas via AWS CLI, IAM Roles, etc.\n"
            "}\n"
            "\n"
            "# Configuração do backend para estado remoto (ex: S3)\n"
            "# terraform {\n"
            "#   backend \"s3\" {\n"
            "#     bucket = \"my-terraform-state-bucket\"\n"
            "#     key    = \"path/to/my/terraform.tfstate\"\n"
            "#     region = \"us-east-1\"\n"
            "#     dynamodb_table = \"my-terraform-locks\"\n"
            "#   }\n"
            "# }\n"
            "```\n\n"
            "#### `variables.tf`\n"
            "```terraform\n"
            "variable \"project_name\" {\n"
            "  description = \"Nome do projeto/aplicação.\"\n"
            "  type        = string\n"
            "}\n\n"
            "variable \"environment\" {\n"
            "  description = \"Ambiente de implantação (ex: dev, prd, hml).\"\n"
            "  type        = string\n"
            "}\n\n"
            "variable \"region\" {\n"
            "  description = \"Região AWS para os recursos.\"\n"
            "  type        = string\n"
            "  default     = \"us-east-1\"\n"
            "}\n\n"
            "variable \"vpc_cidr_block\" {\n"
            "  description = \"CIDR block para a VPC.\"\n"
            "  type        = string\n"
            "  default     = \"10.0.0.0/16\"\n"
            "}\n\n"
            "variable \"private_subnet_cidrs\" {\n"
            "  description = \"Lista de CIDR blocks para as subnets privadas.\"\n"
            "  type        = list(string)\n"
            "  default     = [\"10.0.1.0/24\", \"10.0.2.0/24\"]\n"
            "}\n\n"
            "variable \"public_subnet_cidrs\" {\n"
            "  description = \"Lista de CIDR blocks para as subnets públicas.\"\n"
            "  type        = list(string)\n"
            "  default     = [\"10.0.101.0/24\", \"10.0.102.0/24\"]\n"
            "}\n\n"
            "variable \"eks_cluster_name_prefix\" {\n"
            "  description = \"Prefixo para o nome do cluster EKS.\"\n"
            "  type        = string\n"
            "  default     = \"eks-cluster\"\n"
            "}\n\n"
            "variable \"db_master_username\" {\n"
            "  description = \"Nome de usuário para o banco de dados (referenciado de Secrets Manager).\"\n"
            "  type        = string\n"
            "  default = \"dbuser\"\n"
            "}\n\n"
            "# Exemplo de variável para referência a segredos via Secrets Manager\n"
            "variable \"db_master_password_secret_name\" {\n"
            "  description = \"Nome do segredo no Secrets Manager para a senha do DB.\"\n"
            "  type        = string\n"
            "}\n"
            "```\n\n"
            "#### `main.tf` (Exemplos de Recursos Principais)\n"
            "```terraform\n"
            "# Exemplo de Módulo de VPC (modules/vpc)\n"
            "module \"vpc\" {\n"
            "  source = \"./modules/vpc\"\n"
            "  name = \"${var.project_name}-${var.environment}-vpc\"\n"
            "  cidr = var.vpc_cidr_block\n"
            "  azs = [\"${var.region}a\", \"${var.region}b\"]\n"
            "  private_subnets = var.private_subnet_cidrs\n"
            "  public_subnets = var.public_subnet_cidrs\n"
            "  enable_nat_gateway = true\n"
            "  single_nat_gateway = true\n"
            "  tags = {\n"
            "    Environment = var.environment\n"
            "    Project     = var.project_name\n"
            "  }\n"
            "}\n\n"
            "# Exemplo de Secrets Manager para senhas de DB\n"
            "resource \"aws_secretsmanager_secret\" \"db_password\" {\n"
            "  name        = var.db_master_password_secret_name\n"
            "  description = \"Senha do usuário mestre do banco de dados para ${var.project_name}\"\n"
            "}\n\n"
            "resource \"aws_secretsmanager_secret_version\" \"db_password_version\" {\n"
            "  secret_id     = aws_secretsmanager_secret.db_password.id\n"
            "  secret_string = \"SenhaGeradaOuBuscadaDeAlgumLugarSeguro\" # Em um cenário real, não seria hardcoded\n"
            "}\n\n"
            "# Exemplo de Amazon EKS Cluster\n"
            "# Requer VPC e roles IAM pré-configurados.\n"
            "resource \"aws_eks_cluster\" \"main\" {\n"
            "  name     = \"${var.eks_cluster_name_prefix}-${var.project_name}-${var.environment}\"\n"
            "  role_arn = \"arn:aws:iam::123456789012:role/eks-cluster-role\" # Substituir pelo ARN real\n"
            "  vpc_config {\n"
            "    subnet_ids = concat(module.vpc.private_subnets, module.vpc.public_subnets)\n"
            "  }\n"
            "  version = \"1.28\"\n"
            "  tags = {\n"
            "    Environment = var.environment\n"
            "    Project     = var.project_name\n"
            "  }\n"
            "}\n\n"
            "# Exemplo de Amazon RDS PostgreSQL Instance\n"
            "resource \"aws_db_instance\" \"db_core\" {\n"
            "  identifier            = \"${var.project_name}-db-${var.environment}\"\n"
            "  engine                = \"postgres\"\n"
            "  engine_version        = \"13.5\"\n"
            "  instance_class        = \"db.t3.micro\"\n"
            "  allocated_storage     = 20\n"
            "  db_subnet_group_name  = module.vpc.database_subnet_group\n"
            "  vpc_security_group_ids = [module.vpc.default_security_group_id] # Exemplo, idealmente SG dedicado\n"
            "  name                  = \"${var.project_name}_db\"\n"
            "  username              = var.db_master_username\n"
            "  password              = aws_secretsmanager_secret_version.db_password_version.secret_string # Referência ao segredo\n"
            "  skip_final_snapshot   = true\n"
            "  tags = {\n"
            "    Environment = var.environment\n"
            "    Project     = var.project_name\n"
            "  }\n"
            "}\n\n"
            "# Exemplo de AWS API Gateway\n"
            "resource \"aws_api_gateway_rest_api\" \"api_gateway\" {\n"
            "  name        = \"${var.project_name}-api-${var.environment}\"\n"
            "  description = \"API Gateway para microsserviços de ${var.project_name}\"\n"
            "  tags = {\n"
            "    Environment = var.environment\n"
            "    Project     = var.project_name\n"
            "  }\n"
            "}\n"
            "```\n\n"
            "#### `outputs.tf`\n"
            "```terraform\n"
            "output \"vpc_id\" {\n"
            "  description = \"ID da VPC criada.\"\n"
            "  value       = module.vpc.vpc_id\n"
            "}\n\n"
            "output \"eks_cluster_endpoint\" {\n"
            "  description = \"Endpoint do cluster EKS.\"\n"
            "  value       = aws_eks_cluster.main.endpoint\n"
            "}\n\n"
            "output \"api_gateway_url\" {\n"
            "  description = \"URL base do API Gateway.\"\n"
            "  value       = aws_api_gateway_rest_api.api_gateway.url\n"
            "}\n"
            "```\n"
        )
    elif cloud_platform == "GCP":
        base_prompt += "Google Cloud Platform (GCP)\n\n"
        platform_specific_guidelines = (
            "**3. Diretrizes e Premissas Corporativas para a Solução (GCP - CRUCIAL):**\n\n"
            "   * **Ambiente de Implantação:** Qualquer novo serviço computacional proposto deve ser criado e implementado exclusivamente no Ambiente Google Cloud Platform (GCP).\n"
            "   * **Componentes e Serviços:** As soluções devem utilizar preferencialmente os componentes e serviços nativos disponíveis no GCP.\n"
            "   * **Padrão Corporativo:** Priorize soluções baseadas em contêineres gerenciados como **Google Kubernetes Engine (GKE)** para microsserviços. Considere o uso de Cloud Run para *serverless* quando apropriado para casos de uso específicos e bem definidos. Não utilize soluções proprietárias de outros provedores.\n"
            "   * **Padrão de Artefato Corporativo:** Adapte os conceitos de rede e segurança para o ambiente GCP, utilizando VPCs, subnets, Firewall Rules, IAM, etc. Considere a organização de recursos via Projects e Folders.\n\n"
            "**4. Visão Geral da Solução em GCP (Google Cloud Architecture Framework):**\n\n"
            "   * Descreva a abordagem geral da solução em GCP.\n\n"
            "   * Mencione a adesão aos pilares do Google Cloud Architecture Framework (Excelência Operacional, Segurança, Confiabilidade, Otimização de Performance e Custo, Sustentabilidade).\n\n"
            "   * Identifique o padrão de arquitetura que mais se adapta ao problema identificado, preferencialmente utilizando **Microsserviços**.\n"
            "   * Explique como o padrão de arquitetura adotado (ex.: de microsserviços, Event-Driven Architecture, etc. ) é o modelo mais adequado para ser o pilar da solução.\n\n"
            "**5. Componentes da Solução GCP e sua Relação com o Problema/Solução:**\n\n"
            "   * Para cada componente GCP que você propor, siga este formato:\n\n"
            "       * **Nome do Componente GCP:** (Ex: Compute Engine / Google Kubernetes Engine / Cloud Storage)\n\n"
            "       * **Relação com o Problema/Solução:** Explique como o componente atende a um requisito ou resolve parte do problema. Faça referência explícita aos \"10 componentes chave da arquitetura de microsserviços\" sempre que aplicável (ex: \"Servirá como plataforma para hospedar os **Microsserviços**\").\n\n"
            "       * **Well-Architected:** Descreva como o componente contribui para os pilares do Google Cloud Architecture Framework (ex: \"Promove a **Excelência Operacional** através de automação...\"). **Para os microsserviços implantados no GKE, detalhe a contribuição individual de cada microsserviço para os pilares do Google Cloud Architecture Framework.**\n\n"
            "   * Detalhe os serviços GCP propostos e sua relação com a solução, bem como sua contribuição para os pilares do Google Cloud Architecture Framework.\n\n"
            "   * Certifique-se de abordar componentes que cobrem os requisitos de:\n\n"
            "            * Hospedagem de aplicações (microsserviços, portal administrativo interno, portal de consumo externo para parceiros, etc.).\n\n"
            "       * Gerenciamento de APIs (API Gateway, Apigee).\n\n"
            "       * Bancos de dados (Cloud SQL, Firestore, BigQuery, Cloud Spanner).\n\n"
            "       * Comunicação síncrona/assíncrona (Cloud Pub/Sub, Cloud Tasks).\n\n"
            "       * Gerenciamento de identidades (Cloud IAM, Identity Platform).\n\n"
            "       * Monitoramento (Cloud Monitoring, Cloud Logging, Cloud Trace).\n\n"
            "       * Balanceamento de carga e CDN (Cloud Load Balancing, Cloud CDN).\n\n"
            "       * Conectividade híbrida (Cloud Interconnect, Cloud VPN).\n\n"
            "       * Segurança de segredos (Secret Manager).\n\n"
        )
        plantuml_section = (
            "**6. Diagramas PlantUML:**\n\n"
            "   * Gere o código PlantUML para os seguintes diagramas:\n\n"
            "       * **Diagrama C1 - Diagrama de Contexto do Sistema:** Mostra o sistema em seu ambiente, interagindo com usuários e sistemas externos.\n\n"
            "       * **Diagrama C2 - Diagrama de Contêineres:** Detalha as aplicações principais dentro do sistema, suas tecnologias e interações.\n\n"
            "       * **Diagrama C3 - Diagrama de Componentes (Microsserviços):** Apresenta todos os contêineres da solução e mostra seus componentes internos e interações. **Certifique-se de que não haja menção a \"fidelidade\" na construção deste arquivo.**\n\n"
            "       * **Diagrama de Sequência:** Um diagrama de sequência **OBRIGATÓRIO** detalhando as chamadas de API e os passos entre os sistemas.\n\n"
            "   * **Instruções para o PlantUML:**\n\n"
            "       * Utilize `!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml` (e variantes para C2/C3) no início de cada diagrama para usar a notação C4.\n\n"
            "       * Use `LAYOUT_WITH_LEGEND()` para incluir a legenda.\n\n"
            "       * Assegure-se de que os nomes dos elementos nos diagramas sejam consistentes com a descrição da solução e reflitam os serviços GCP.\n\n"
            "       * A entrada para esta GEM será a transcrição analisada. \n\n"
            "   * **Template sugerido para todos os diagramas C4:**\n\n"
            "   ```plantuml\n"
            "   @startuml <NomeDoDiagrama>\n\n"
            "   !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml)\n"
            "   !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml)\n"
            "   !include [https://raw.githubusercontent.com/plantuml/plantuml-stdlib/master/C4_Component.puml](https://raw.githubusercontent.com/plantuml/plantuml-stdlib/master/C4_Component.puml)\n"
            "   ' Opcional: !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Class.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Class.puml) para diagramas de código\n\n"
            "   LAYOUT_WITH_LEGEND()\n\n"
            "   title <Título do Diagrama>\n\n"
            "   ' SEUS ELEMENTOS C4 AQUI (Person, System, System_Boundary, Container, Container_Boundary, Component, etc. com nomes de serviços GCP)\n\n"
            "   @enduml\n"
            "```\n\n"
        )
        terraform_section = (
            "**7. Scripts Terraform (Infraestrutura como Código - GCP):**\n\n"
            "Gere os blocos de código Terraform para provisionar os recursos GCP propostos, seguindo a estrutura de arquivos e as diretrizes de nomenclatura.\n"
            "Priorize o uso de módulos Terraform (ex: `vpc`, `gke`, `sql`) para reutilização.\n\n"
            "#### `versions.tf`\n"
            "```terraform\n"
            "terraform {\n"
            "  required_providers {\n"
            "    google = {\n"
            "      source  = \"hashicorp/google\"\n"
            "      version = \"~> 5.0\"\n"
            "    }\n"
            "  }\n"
            "  required_version = \">= 1.0.0\"\n"
            "}\n"
            "```\n\n"
            "#### `providers.tf`\n"
            "```terraform\n"
            "provider \"google\" {\n"
            "  project = var.project_id\n"
            "  region  = var.region\n"
            "  # Credenciais configuradas via gcloud CLI, Service Accounts, etc.\n"
            "}\n"
            "\n"
            "# Configuração do backend para estado remoto (ex: Cloud Storage)\n"
            "# terraform {\n"
            "#   backend \"gcs\" {\n"
            "#     bucket = \"my-terraform-state-bucket\"\n"
            "#     prefix = \"terraform/state\"\n"
            "#   }\n"
            "# }\n"
            "```\n\n"
            "#### `variables.tf`\n"
            "```terraform\n"
            "variable \"project_id\" {\n"
            "  description = \"ID do projeto GCP.\"\n"
            "  type        = string\n"
            "}\n\n"
            "variable \"environment\" {\n"
            "  description = \"Ambiente de implantação (ex: dev, prd, hml).\"\n"
            "  type        = string\n"
            "}\n\n"
            "variable \"region\" {\n"
            "  description = \"Região GCP para os recursos.\"\n"
            "  type        = string\n"
            "  default     = \"us-central1\"\n"
            "}\n\n"
            "variable \"zone\" {\n"
            "  description = \"Zona GCP para recursos zonais.\"\n"
            "  type        = string\n"
            "  default     = \"us-central1-a\"\n"
            "}\n\n"
            "variable \"network_name\" {\n"
            "  description = \"Nome da VPC network.\"\n"
            "  type        = string\n"
            "}\n\n"
            "variable \"subnet_cidr_primary\" {\n"
            "  description = \"CIDR block para a subnet primária.\"\n"
            "  type        = string\n"
            "  default     = \"10.10.0.0/20\"\n"
            "}\n\n"
            "variable \"gke_cluster_name_prefix\" {\n"
            "  description = \"Prefixo para o nome do cluster GKE.\"\n"
            "  type        = string\n"
            "  default     = \"gke-cluster\"\n"
            "}\n\n"
            "variable \"db_user\" {\n"
            "  description = \"Nome de usuário para o banco de dados (referenciado de Secret Manager).\"\n"
            "  type        = string\n"
            "  default = \"dbuser\"\n"
            "}\n\n"
            "# Exemplo de variável para referência a segredos via Secret Manager\n"
            "variable \"db_password_secret_id\" {\n"
            "  description = \"ID do segredo no Secret Manager para a senha do DB.\"\n"
            "  type        = string\n"
            "}\n"
            "```\n\n"
            "#### `main.tf` (Exemplos de Recursos Principais)\n"
            "```terraform\n"
            "# Exemplo de Módulo de VPC (modules/network)\n"
            "module \"vpc\" {\n"
            "  source      = \"./modules/network\"\n"
            "  project_id  = var.project_id\n"
            "  network_name = var.network_name\n"
            "  subnet_name = \"${var.project_name}-subnet-${var.environment}\"\n"
            "  subnet_ip_cidr_range = var.subnet_cidr_primary\n"
            "  region      = var.region\n"
            "}\n\n"
            "# Exemplo de Secret Manager para senhas de DB\n"
            "resource \"google_secret_manager_secret\" \"db_password\" {\n"
            "  project   = var.project_id\n"
            "  secret_id = var.db_password_secret_id\n"
            "  replication {\n"
            "    auto {\n"
            "    }\n"
            "  }\n"
            "}\n\n"
            "resource \"google_secret_manager_secret_version\" \"db_password_version\" {\n"
            "  secret    = google_secret_manager_secret.db_password.id\n"
            "  secret_data = \"SenhaGeradaOuBuscadaDeAlgumLugarSeguro\" # Em um cenário real, não seria hardcoded\n"
            "}\n\n"
            "# Exemplo de Google Kubernetes Engine (GKE) Cluster\n"
            "resource \"google_container_cluster\" \"primary\" {\n"
            "  name               = \"${var.gke_cluster_name_prefix}-${var.project_name}-${var.environment}\"\n"
            "  location           = var.region\n"
            "  initial_node_count = 1\n"
            "  network            = module.vpc.network_self_link\n"
            "  subnetwork         = module.vpc.subnet_self_link\n"
            "  logging_service    = \"[logging.googleapis.com/kubernetes](https://logging.googleapis.com/kubernetes)\"\n"
            "  monitoring_service = \"[monitoring.googleapis.com/kubernetes](https://monitoring.googleapis.com/kubernetes)\"\n"
            "  ip_allocation_policy {\n"
            "    cluster_ipv4_cidr_block  = \"/19\"\n"
            "    services_ipv4_cidr_block = \"/20\"\n"
            "  }\n"
            "  depends_on         = [module.vpc]\n"
            "}\n\n"
            "# Exemplo de Cloud SQL PostgreSQL Instance\n"
            "resource \"google_sql_database_instance\" \"db_core\" {\n"
            "  name             = \"${var.project_name}-db-${var.environment}\"\n"
            "  database_version = \"POSTGRES_13\"\n"
            "  region           = var.region\n"
            "  settings {\n"
            "    tier = \"db-f1-micro\"\n"
            "    ip_configuration {\n"
            "      ipv4_enabled = true\n"
            "      private_network = module.vpc.network_self_link # Conecta à VPC\n"
            "    }\n"
            "    backup_configuration {\n"
            "      enabled = true\n"
            "      start_time = \"03:00\"\n"
            "    }\n"
            "    disk_autoresize = true\n"
            "  }\n"
            "  root_password = google_secret_manager_secret_version.db_password_version.secret_data # Referência ao segredo\n"
            "}\n\n"
            "# Exemplo de API Gateway (GCP)\n"
            "# Geralmente, o API Gateway no GCP requer um backend (Cloud Run, GKE, Cloud Functions)\n"
            "resource \"google_api_gateway_api\" \"api_gateway\" {\n"
            "  api_id      = \"${var.project_name}-api-${var.environment}\"\n"
            "  display_name = \"${var.project_name} API\"\n"
            "}\n\n"
            "```\n\n"
            "#### `outputs.tf`\n"
            "```terraform\n"
            "output \"gke_cluster_name\" {\n"
            "  description = \"Nome do cluster GKE.\"\n"
            "  value       = google_container_cluster.primary.name\n"
            "}\n\n"
            "output \"sql_instance_connection_name\" {\n"
            "  description = \"Nome de conexão da instância Cloud SQL.\"\n"
            "  value       = google_sql_database_instance.db_core.connection_name\n"
            "}\n\n"
            "output \"api_gateway_api_id\" {\n"
            "  description = \"ID da API Gateway.\"\n"
            "  value       = google_api_gateway_api.api_gateway.api_id\n"
            "}\n"
            "```\n"
        )
    else: # Fallback para Azure se a plataforma não for reconhecida
        base_prompt += "Plataforma Não Especificada (Azure Padrão)\n\n"
        # Mantém as diretrizes e Terraform do Azure como padrão
        platform_specific_guidelines = (
            "**3. Diretrizes e Premissas Corporativas para a Solução (Azure - Padrão - CRUCIAL):**\n\n"
            "   * **Ambiente de Implantação:** Qualquer novo serviço computacional proposto deve ser criado e implementado exclusivamente no Ambiente Azure.\n"
            "   * **Componentes e Serviços:** As soluções devem utilizar preferencialmente os componentes e serviços nativos disponíveis no Azure.\n"
            "   * **Padrão Corporativo:** O uso de Functions e Logic Apps é **desencorajado**. A solução corporativa e padrão é a utilização do **ARO (Azure Red Hat OpenShift)**.\n"
            "   * **Padrão de Artefato Corporativo:** O padrão de artefato inclui: Azure Tenant, On-premises, Acesso Externo, Hub Interno, Shared Infrastructure, VNETs e subscriptions associadas ao serviço Transacionar em cada ambiente (PR, HO, DV).\n\n"
            "**4. Visão Geral da Solução em Azure (Well-Architected Infrastructure):**\n\n"
            "   * Descreva a abordagem geral da solução em Azure.\n\n"
            "   * Mencione a adesão aos pilares do Azure Well-Architected Framework (Confiabilidade, Segurança, Excelência Operacional, Otimização de Custos, Eficiência de Desempenho).\n\n"
            "   * Identifique o padrão de arquitetura que mais se adapta ao problema identificado, preferencialmente utilizando **Microsserviços** devido às premissas de ARO.\n"
            "   * Explique como o padrão de arquitetura adotado (ex.: de microsserviços, Event-Driven Architecture, etc. ) é o modelo mais adequado para ser o pilar da solução.\n\n"
            "**5. Componentes da Solução Azure e sua Relação com o Problema/Solução:**\n\n"
            "   * Para cada componente Azure que você propor, siga este formato:\n\n"
            "       * **Nome do Componente Azure:** (Ex: Azure App Service / Azure Resources for Openshift (ARO))\n\n"
            "       * **Relação com o Problema/Solução:** Explique como o componente atende a um requisito ou resolve parte do problema. Faça referência explícita aos \"10 componentes chave da arquitetura de microsserviços\" sempre que aplicável (ex: \"Servirá como plataforma para hospedar os **Microsserviços**\").\n\n"
            "       * **Well-Architected:** Descreva como o componente contribui para os pilares do Well-Architected Framework (ex: \"Promove a **Excelência de Desempenho**...\"). **Para os microsserviços implantados no ARO, detalhe a contribuição individual de cada microsserviço para os pilares do Well-Architected Framework.**\n\n"
            "   * Detalhe os serviços Azure propostos e sua relação com a solução, bem como sua contribuição para os pilares do Well-Architected Framework, especialmente para os microsserviços implantados no ARO.\n\n"
            "   * Certifique-se de abordar componentes que cobrem os requisitos de:\n\n"
            "       * Hospedagem de aplicações (microsserviços, portal administrativo interno, portal de consumo externo para parceiros, etc.).\n\n"
            "       * Gerenciamento de APIs.\n\n"
            "       * Bancos de dados.\n\n"
            "       * Comunicação síncrona/assíncrona.\n\n"
            "       * Gerenciamento de identidades.\n\n"
            "       * Monitoramento.\n\n"
            "       * Balanceamento de carga e CDN.\n\n"
            "       * Conectividade híbrida (on-premises).\n\n"
            "       * Segurança de segredos.\n\n"
        )
        plantuml_section = (
            "**6. Diagramas PlantUML:**\n\n"
            "   * Gere o código PlantUML para os seguintes diagramas:\n\n"
            "       * **Diagrama C1 - Diagrama de Contexto do Sistema:** Mostra o sistema em seu ambiente, interagindo com usuários e sistemas externos.\n\n"
            "       * **Diagrama C2 - Diagrama de Contêineres:** Detalha as aplicações principais dentro do sistema, suas tecnologias e interações.\n\n"
            "       * **Diagrama C3 - Diagrama de Componentes (Microsserviços):** Apresenta todos os contêineres da solução e mostra seus componentes internos e interações. **Certifique-se de que não haja menção a \"fidelidade\" na construção deste arquivo.**\n\n"
            "       * **Diagrama de Sequência:** Um diagrama de sequência **OBRIGATÓRIO** detalhando as chamadas de API e os passos entre os sistemas.\n\n"
            "   * **Instruções para o PlantUML:**\n\n"
            "       * Utilize `!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml` (e variantes para C2/C3) no início de cada diagrama para usar a notação C4.\n\n"
            "       * Use `LAYOUT_WITH_LEGEND()` para incluir a legenda.\n\n"
            "       * Assegure-se de que os nomes dos elementos nos diagramas sejam consistentes com a descrição da solução.\n\n"
            "       * A entrada para esta GEM será a transcrição analisada. \n\n"
            "   * **Template sugerido para todos os diagramas C4:**\n\n"
            "   ```plantuml\n"
            "   @startuml <NomeDoDiagrama>\n\n"
            "   !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml)\n"
            "   !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml)\n"
            "   !include [https://raw.githubusercontent.com/plantuml/plantuml-stdlib/master/C4_Component.puml](https://raw.githubusercontent.com/plantuml/plantuml-stdlib/master/C4_Component.puml)\n"
            "   ' Opcional: !include [https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Class.puml](https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Class.puml) para diagramas de código\n\n"
            "   LAYOUT_WITH_LEGEND()\n\n"
            "   title <Título do Diagrama>\n\n"
            "   ' SEUS ELEMENTOS C4 AQUI (Person, System, System_Boundary, Container, Container_Boundary, Component, etc.)\n\n"
            "   @enduml\n"
            "```\n\n"
        )
        terraform_section = (
            "**7. Scripts Terraform (Infraestrutura como Código - Azure):**\n\n"
            "Gere os blocos de código Terraform para provisionar os recursos Azure propostos, seguindo a estrutura de arquivos e as diretrizes de nomenclatura.\n"
            "Priorize o uso de módulos Terraform (ex: `network`, `compute`, `database`) para reutilização.\n\n"
            "#### `versions.tf`\n"
            "```terraform\n"
            "terraform {\n"
            "  required_providers {\n"
            "    azurerm = {\n"
            "      source  = \"hashicorp/azurerm\"\n"
            "      version = \"~> 3.0\"\n"
            "    }\n"
            "  }\n"
            "  required_version = \">= 1.0.0\"\n"
            "}\n"
            "```\n\n"
            "#### `providers.tf`\n"
            "```terraform\n"
            "provider \"azurerm\" {\n"
            "  features {}\n"
            "  # Autenticação via Azure CLI, Managed Identity ou Service Principal\n"
            "  # subscription_id = var.azure_subscription_id # Exemplo\n"
            "  # tenant_id       = var.azure_tenant_id       # Exemplo\n"
            "}\n"
            "```\n\n"
            "#### `variables.tf`\n"
            "```terraform\n"
            "variable \"project_name\" {\n"
            "  description = \"Nome do projeto/aplicação.\"\n"
            "  type        = string\n"
            "}\n\n"
            "variable \"environment\" {\n"
            "  description = \"Ambiente de implantação (ex: dev, prd, hml).\"\n"
            "  type        = string\n"
            "}\n\n"
            "variable \"location\" {\n"
            "  description = \"Região do Azure para os recursos.\"\n"
            "  type        = string\n"
            "  default     = \"East US\"\n"
            "}\n\n"
            "variable \"resource_group_name_prefix\" {\n"
            "  description = \"Prefixo para o nome do Resource Group.\"\n"
            "  type        = string\n"
            "  default     = \"rg\"\n"
            "}\n\n"
            "variable \"vnet_cidr\" {\n"
            "  description = \"CIDR da VNet principal.\"\n"
            "  type        = string\n"
            "  default     = \"10.0.0.0/16\"\n"
            "}\n\n"
            "variable \"aro_cluster_name_prefix\" {\n"
            "  description = \"Prefixo para o nome do cluster ARO.\"\n"
            "  type        = string\n"
            "  default     = \"aro-cluster\"\n"
            "}\n\n"
            "variable \"db_admin_username\" {\n"
            "  description = \"Nome de usuário para o administrador do banco de dados (referenciado de Key Vault).\"\n"
            "  type        = string\n"
            "  # Este valor não deve ser definido diretamente aqui. Deve ser buscado de um segredo.\n"
            "  default = \"dbadmin\"\n"
            "}\n\n"
            "# Exemplo de variável para referência a segredos via Key Vault\n"
            "variable \"db_admin_password_secret_name\" {\n"
            "  description = \"Nome do segredo no Key Vault para a senha do DB.\"\n"
            "  type        = string\n"
            "}\n\n"
            "variable \"key_vault_name\" {\n"
            "  description = \"Nome do Key Vault a ser criado ou referenciado.\"\n"
            "  type        = string\n"
            "}\n"
            "```\n\n"
            "#### `main.tf` (Exemplos de Recursos Principais)\n"
            "```terraform\n"
            "resource \"azurerm_resource_group\" \"main\" {\n"
            "  name     = \"${var.resource_group_name_prefix}-${var.project_name}-${var.environment}-${var.location}\"\n"
            "  location = var.location\n"
            "  tags = {\n"
            "    environment = var.environment\n"
            "    project     = var.project_name\n"
            "  }\n"
            "}\n\n"
            "# Exemplo de Módulo de Rede (modules/network)\n"
            "module \"network\" {\n"
            "  source = \"./modules/network\"\n"
            "  resource_group_name = azurerm_resource_group.main.name\n"
            "  location            = var.location\n"
            "  vnet_name           = \"vnet-${var.project_name}-${var.environment}\"\n"
            "  vnet_cidr           = var.vnet_cidr\n"
            "  subnet_cidrs        = {\n"
            "    \"subnet-aro\"    = \"10.0.1.0/24\"\n"
            "    \"subnet-db\"     = \"10.0.2.0/24\"\n"
            "    \"subnet-apim\"   = \"10.0.3.0/24\"\n"
            "  }\n"
            "  tags = azurerm_resource_group.main.tags\n"
            "}\n\n"
            "# Exemplo de Key Vault\n"
            "resource \"azurerm_key_vault\" \"main\" {\n"
            "  name                      = var.key_vault_name\n"
            "  location                  = azurerm_resource_group.main.location\n"
            "  resource_group_name       = azurerm_resource_group.main.name\n"
            "  tenant_id                 = data.azurerm_client_config.current.tenant_id\n"
            "  sku_name                  = \"standard\"\n"
            "  soft_delete_retention_days= 7\n"
            "  purge_protection_enabled  = false\n"
            "  tags                      = azurerm_resource_group.main.tags\n"
            "}\n\n"
            "data \"azurerm_client_config\" \"current\" {}\n\n"
            "# Exemplo de Azure Red Hat OpenShift Cluster (ARO)\n"
            "# Este é um recurso complexo e pode requerer mais variáveis e pré-requisitos.\n"
            "resource \"azurerm_redhat_open_shift_cluster\" \"aro_cluster\" {\n"
            "  name                = \"${var.aro_cluster_name_prefix}-${var.project_name}-${var.environment}\"\n"
            "  location            = azurerm_resource_group.main.location\n"
            "  resource_group_name = azurerm_resource_group.main.name\n"
            "  cluster_resource_group = \"${azurerm_resource_group.main.name}-aro\"\n"
            "  network_cidr        = \"10.0.0.0/22\"\n"
            "\n"
            "  master_profile {\n"
            "    vm_size   = \"Standard_D8s_v3\"\n"
            "    subnet_id = module.network.subnets[\"subnet-aro\"].id\n"
            "  }\n"
            "\n"
            "  worker_profile {\n"
            "    vm_size   = \"Standard_D4s_v3\"\n"
            "    disk_size_gb = 128\n"
            "    node_count = 3\n"
            "    subnet_id = module.network.subnets[\"subnet-aro\"].id\n"
            "  }\n"
            "\n"
            "  tags = azurerm_resource_group.main.tags\n"
            "}\n\n"
            "# Exemplo de Azure API Management\n"
            "resource \"azurerm_api_management_service\" \"api_gateway\" {\n"
            "  name                = \"apim-${var.project_name}-${var.environment}\"\n"
            "  location            = azurerm_resource_group.main.location\n"
            "  resource_group_name = azurerm_resource_group.main.name\n"
            "  publisher_name      = \"${var.project_name} API Publisher\"\n"
            "  publisher_email     = \"apis@${var.project_name}.com\"\n"
            "  sku_name            = \"Developer_1\"\n"
            "  tags                = azurerm_resource_group.main.tags\n"
            "}\n\n"
            "# Exemplo de Azure Database for PostgreSQL (Flexible Server)\n"
            "resource \"azurerm_postgresql_flexible_server\" \"db_core\" {\n"
            "  name                   = \"pg-${var.project_name}-${var.environment}\"\n"
            "  resource_group_name    = azurerm_resource_group.main.name\n"
            "  location               = azurerm_resource_group.main.location\n"
            "  version                = \"13\"\n"
            "  sku_name               = \"Standard_D2ds_v4\"\n"
            "  storage_mb             = 32768\n"
            "  administrator_login    = var.db_admin_username\n"
            "  administrator_password = azurerm_key_vault_secret.db_password.value # Referência ao segredo\n"
            "  backup_retention_days  = 7\n"
            "  geo_redundant_backup_enabled = false\n"
            "  tags                   = azurerm_resource_group.main.tags\n"
            "}\n\n"
            "# Exemplo de referência a um segredo do Key Vault\n"
            "resource \"azurerm_key_vault_secret\" \"db_password\" {\n"
            "  name         = var.db_admin_password_secret_name\n"
            "  value        = \"SenhaGeradaOuBuscadaDeAlgumLugarSeguro\" # Em um cenário real, não seria hardcoded\n"
            "  key_vault_id = azurerm_key_vault.main.id\n"
            "  content_type = \"text/plain\"\n"
            "  depends_on   = [azurerm_key_vault.main]\n"
            "}\n\n"
            "# Exemplo de módulo de rede (modules/network/main.tf)\n"
            "/*\n"
            "module \"network\" {\n"
            "  source = \"./modules/network\"\n"
            "  # ... variáveis do módulo de rede ...\n"
            "}\n"
            "*/\n"
            "```\n\n"
            "#### `outputs.tf`\n"
            "```terraform\n"
            "output \"resource_group_id\" {\n"
            "  description = \"ID do Resource Group criado.\"\n"
            "  value       = azurerm_resource_group.main.id\n"
            "}\n\n"
            "output \"aro_cluster_id\" {\n"
            "  description = \"ID do cluster Azure Red Hat OpenShift.\"\n"
            "  value       = azurerm_redhat_open_shift_cluster.aro_cluster.id\n"
            "}\n\n"
            "output \"api_management_gateway_url\" {\n"
            "  description = \"URL do API Management Gateway.\"\n"
            "  value       = azurerm_api_management_service.api_gateway.gateway_url\n"
            "}\n"
            "```\n"
        )

    # Concatena o prompt base com as diretrizes específicas da plataforma e a seção Terraform
    full_prompt = (
        base_prompt +
        "**1. Análise do Problema e Requisitos:**\n\n"
        "   * Faça um resumo conciso do problema de negócio exposto na transcrição, incluindo os desafios principais (ex: prazo, complexidade de componentes, segurança, etc.).\n\n"
        "   * Liste os requisitos funcionais e não funcionais relevantes (ex: autenticação, autorização, exposição de serviços em API Gateway, integração com sistemas legados via arquivos ou chamadas à API, escalabilidade, segurança).\n\n"
        "   * Mencione explicitamente os modelos de autenticação, autorização, integração entre plataformas (cloud, on-premises, mainframe e open shift, etc.) e as preferências/preocupações levantadas.\n\n"
        "**2. Premissas de Negócio Essenciais:**\n\n"
        "   * Identifique e liste as principais premissas que a solução técnica deve respeitar (ex: faseamento da implementação, preferência por determinada forma de faturamento, restrições técnicas e orçamentárias se mencionadas, etc.).\n\n"
        + platform_specific_guidelines +
        "   * **UTILIZE AS SEGUINTES INFORMAÇÕES SALVAS:**\n\n"
        "       * \"Visão geral dos 10 componentes chave da arquitetura de microsserviços: Cliente, CDN, Load Balancer, API Gateway, Microsserviços, Message Broker, Databases, Identity Provider, Service Registry e Discovery, Service Coordenação (e.g., Zookeeper).\"\n\n"
        + plantuml_section +
        terraform_section + # Adiciona a seção Terraform aqui
        f"Transcrição analisada:\n{transcription_text}"
    )
    
    return full_prompt

### MODIFICADO: Função call_gemini_analysis para aceitar o tipo de prompt ###
def call_gemini_api(prompt_text, prompt_purpose):
    """
    Chama o modelo Gemini com o texto do prompt fornecido.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info(f"Chamando o modelo Gemini para: {prompt_purpose}.")
        logger.debug(f"Prompt enviado para Gemini (primeiros 200 chars): {prompt_text[:200]}...")
        
        response = model.generate_content(prompt_text)
        logger.info(f"Resposta da GEM para {prompt_purpose} recebida com sucesso.")
        return response.text
    except Exception as e:
        logger.error(f"Erro ao chamar a API da GEM para {prompt_purpose}: {e}", exc_info=True)
        messagebox.showerror(f"Erro na {prompt_purpose} GEM", f"Não foi possível obter a resposta da GEM: {e}")
        return None

# --- Lógica de Transcrição ---
# MODIFICADO: transcribe_audio_logic para aceitar selected_cloud_platform
def transcribe_audio_logic(audio_path, model_size, use_gpu, output_path, generate_analysis_option, generate_solution_option, selected_cloud_platform, progress_label_callback=None, progress_bar_callback=None, stop_event=None, clear_fields_callback=None):
    transcription_interrupted = False
    logger.info(f"Iniciando lógica de transcrição para: {audio_path}")
    try:
        if 'torch' not in sys.modules:
            raise ImportError("O módulo 'torch' não está carregado. Por favor, reinicie e verifique a instalação.")

        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        logger.info(f"Dispositivo de transcrição selecionado: {device}")

        if use_gpu and not torch.cuda.is_available():
            messagebox.showwarning("Aviso de GPU", "Você selecionou 'Usar GPU', mas nenhuma GPU compatível com CUDA foi encontrada. A transcrição será executada na CPU.")
            logger.warning("GPU selecionada, mas CUDA não disponível. Revertendo para CPU.")
            device = "cpu"

        logger.info(f"Usando o dispositivo: {device}")

        compute_type = "float16" if device == "cuda" else "int8"
        logger.info(f"Tipo de computação: {compute_type}")

        model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info(f"Modelo Whisper carregado: {model_size}")

        if not os.path.exists(audio_path):
            messagebox.showerror("Erro de Arquivo", f"O arquivo de áudio '{audio_path}' não foi encontrado.")
            logger.error(f"Arquivo de áudio não encontrado: {audio_path}")
            return

        segments_generator, info = model.transcribe(audio_path, beam_size=5)
        logger.info(f"Iniciando transcrição de áudio com duração: {info.duration:.2f} segundos.")

        full_transcription = ""
        audio_duration = info.duration

        for segment in segments_generator:
            if stop_event and stop_event.is_set():
                transcription_interrupted = True
                messagebox.showinfo("Transcrição Cancelada", "A transcrição foi cancelada pelo usuário.")
                logger.info("Transcrição cancelada pelo usuário.")
                break

            text = segment.text.strip()
            full_transcription += text + " "

            if progress_label_callback and progress_bar_callback:
                progress_percentage = (segment.end / audio_duration) * 100
                progress_bar_callback(progress_percentage)
                progress_label_callback(f"Progresso: {int(progress_percentage)}%\n[{text}]")

        if not transcription_interrupted:
            transcribed_text = full_transcription.strip()
            logger.info(f"Transcrição completa. Salvando em: {output_path}")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(transcribed_text)

            messagebox.showinfo("Sucesso", f"Transcrição concluída e salva em '{output_path}'")
            logger.info("Transcrição salva com sucesso.")

            # --- Lógica para gerar análise e/ou solução com a GEM ---
            if generate_analysis_option or generate_solution_option:
                if 'google.generativeai' not in sys.modules:
                    messagebox.showerror("Erro de Dependência", "A biblioteca 'google-generativeai' não está disponível. Por favor, reinicie o script para tentar a instalação automática ou instale manualmente.")
                    progress_label_callback("Erro: 'google.generativeai' não encontrado.")
                    logger.error("A biblioteca 'google.generativeai' não está carregada para análise da GEM.")
                    return
                
                base_name = os.path.basename(output_path)
                file_name_without_ext = os.path.splitext(base_name)[0]

                if generate_analysis_option:
                    progress_label_callback("Chamando Analisador de Transcrições (GEM)...")
                    analysis_output = call_gemini_api(get_analysis_prompt(transcribed_text), "Análise de Transcrições")
                    
                    if analysis_output:
                        analysis_output_path = os.path.join(os.path.dirname(output_path), f"GEM - Analise {file_name_without_ext}.txt")
                        logger.info(f"Análise da GEM gerada. Salvando em: {analysis_output_path}")
                        with open(analysis_output_path, "w", encoding="utf-8") as f:
                            f.write(analysis_output)
                        messagebox.showinfo("Análise Concluída", f"Análise da GEM gerada e salva em '{analysis_output_path}'")
                        logger.info("Análise da GEM salva com sucesso.")
                    else:
                        messagebox.showwarning("Análise GEM", "A análise da GEM não foi gerada devido a um erro.")
                        logger.warning("Análise da GEM não foi gerada ou retornou vazia.")

                if generate_solution_option:
                    progress_label_callback(f"Chamando Gerador de Solução ({selected_cloud_platform} GEM)...")
                    solution_output = call_gemini_api(get_solution_prompt(transcribed_text, selected_cloud_platform), "Geração de Solução")
                    
                    if solution_output:
                        solution_output_path = os.path.join(os.path.dirname(output_path), f"GEM - Solucao Tecnica ({selected_cloud_platform}) {file_name_without_ext}.txt")
                        logger.info(f"Solução Técnica da GEM gerada. Salvando em: {solution_output_path}")
                        with open(solution_output_path, "w", encoding="utf-8") as f:
                            f.write(solution_output)
                        messagebox.showinfo("Solução Concluída", f"Solução Técnica da GEM gerada e salva em '{solution_output_path}'")
                        logger.info("Solução Técnica da GEM salva com sucesso.")
                    else:
                        messagebox.showwarning("Solução GEM", "A solução técnica da GEM não foi gerada devido a um erro.")
                        logger.warning("Solução técnica da GEM não foi gerada ou retornou vazia.")
            else:
                logger.info("Nenhuma opção de análise ou solução da GEM selecionada. Pulando chamada à API.")

        else:
            if progress_label_callback:
                progress_label_callback("Cancelado.")

    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado durante a transcrição: {e}", exc_info=True)
        messagebox.showerror("Erro de Transcrição", f"Ocorreu um erro durante a transcrição: {e}")
    finally:
        logger.info("Processo de transcrição finalizado.")
        if progress_label_callback:
            progress_label_callback("Pronto.")
        if progress_bar_callback:
            progress_bar_callback(0)
        
        if clear_fields_callback:
            clear_fields_callback()

# --- Interface Gráfica Tkinter ---
class TranscriptionApp:
    def __init__(self, master):
        self.master = master
        master.title("Transcritor de Áudio 'CesarVox' [Faster Whisper]")
        master.geometry("600x610") # Ajuste sutil na altura para acomodar o novo posicionamento
        master.resizable(False, False)

        self.gpu_var = tk.BooleanVar(value=False)
        self.analysis_var = tk.BooleanVar(value=False) 
        self.solution_var = tk.BooleanVar(value=False)
        self.model_var = tk.StringVar(value="small")
        self.audio_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        self.progress_value = tk.DoubleVar(value=0)
        self.cloud_platform_var = tk.StringVar(value="Azure")

        self.stop_transcription_event = threading.Event()

        master.columnconfigure(0, weight=1)
        master.columnconfigure(1, weight=3)

        self.create_widgets()

    def create_widgets(self):
        # --- DEFINIÇÃO DOS ESTILOS NO INÍCIO ---
        style = ttk.Style()
        style.configure("Small.TButton", font=('Helvetica', 10), padding=8)
        style.map("Small.TButton",
                  foreground=[('pressed', 'red'), ('active', 'blue')],
                  background=[('pressed', '!focus', 'SystemButtonFace'), ('active', 'SystemButtonFace')])

        style.configure("Green.TButton", font=('Helvetica', 10, 'bold'), padding=8, foreground="green")
        style.map("Green.TButton",
                  foreground=[('pressed', 'darkgreen'), ('active', 'lime green')],
                  background=[('pressed', '!focus', 'SystemButtonFace'), ('active', 'SystemButtonFace')])

        style.configure("Red.TButton", font=('Helvetica', 10, 'bold'), padding=8, foreground="red")
        style.map("Red.TButton",
                  foreground=[('pressed', 'darkred'), ('active', 'salmon')],
                  background=[('pressed', '!focus', 'SystemButtonFace'), ('active', 'SystemButtonFace')])
        # --- FIM DA DEFINIÇÃO DE ESTILOS ---

        row_idx = 0

        # Checkboxes (mantêm a mesma linha e posição inicial)
        checkbox_frame = ttk.Frame(self.master)
        checkbox_frame.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=(5, 10))
        
        tk.Label(checkbox_frame, text="Usar GPU (se disponível):").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(checkbox_frame, text="Sim", variable=self.gpu_var).pack(side=tk.LEFT, padx=(0, 20)) 

        tk.Label(checkbox_frame, text="Gerar Análise:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(checkbox_frame, text="Sim", variable=self.analysis_var).pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Label(checkbox_frame, text="Gerar Solução:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Checkbutton(checkbox_frame, text="Sim", variable=self.solution_var,
                        command=self.toggle_cloud_platform_dropdown).pack(side=tk.LEFT)
        row_idx += 1 # Passa para a próxima linha para o Modelo Whisper

        # Modelo Whisper (mantém a posição relativa)
        tk.Label(self.master, text="Modelo Whisper:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        models = ["tiny", "base", "small", "medium", "large"]
        ttk.OptionMenu(self.master, self.model_var, self.model_var.get(), *models).grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        row_idx += 1

        # Arquivo de Áudio (mantém a posição relativa)
        tk.Label(self.master, text="Arquivo de Áudio:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        audio_frame = ttk.Frame(self.master)
        audio_frame.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        audio_frame.columnconfigure(0, weight=1)
        ttk.Entry(audio_frame, textvariable=self.audio_file_path, state="readonly", width=50).grid(row=0, column=0, sticky="ew")
        ttk.Button(audio_frame, text="Procurar", command=self.browse_audio_file, style="Small.TButton").grid(row=0, column=1, padx=5)
        row_idx += 1

        # Salvar Transcrição Como (mantém a posição relativa)
        tk.Label(self.master, text="Salvar Transcrição Como:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        output_frame = ttk.Frame(self.master)
        output_frame.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        output_frame.columnconfigure(0, weight=1)
        ttk.Entry(output_frame, textvariable=self.output_file_path, width=50).grid(row=0, column=0, sticky="ew")
        ttk.Button(output_frame, text="Salvar", command=self.save_output_file, style="Small.TButton").grid(row=0, column=1, padx=5)
        self.audio_file_path.trace_add("write", self.suggest_output_filename)
        row_idx += 1 # Agora, esta é a linha após "Salvar Transcrição Como"

        # NOVO POSICIONAMENTO: Seção para seleção da Plataforma Cloud
        self.cloud_platform_frame = ttk.Frame(self.master)
        # Reposicionando aqui: usa a nova row_idx
        self.cloud_platform_frame.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        self.cloud_platform_frame.columnconfigure(1, weight=1) 
        
        tk.Label(self.cloud_platform_frame, text="Plataforma Cloud para Solução:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        cloud_options = ["Azure", "AWS", "GCP"]
        self.cloud_platform_dropdown = ttk.OptionMenu(self.cloud_platform_frame, self.cloud_platform_var,
                                                     self.cloud_platform_var.get(), *cloud_options)
        self.cloud_platform_dropdown.grid(row=0, column=1, sticky="ew")
        
        self.toggle_cloud_platform_dropdown() # Define o estado inicial do dropdown
        row_idx += 1 # Incrementa para a próxima linha (botões de Transcrever/Cancelar)


        buttons_frame = ttk.Frame(self.master)
        buttons_frame.grid(row=row_idx, column=0, columnspan=2, pady=20)
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)

        self.transcribe_button = ttk.Button(buttons_frame, text="Transcrever", command=self.start_transcription_thread, style="Green.TButton")
        self.transcribe_button.grid(row=0, column=0, padx=5, sticky="ew")

        self.cancel_button = ttk.Button(buttons_frame, text="Parar/Cancelar", command=self.cancel_transcription, style="Red.TButton")
        self.cancel_button.grid(row=0, column=1, padx=5, sticky="ew")
        self.cancel_button.config(state=tk.DISABLED)
        row_idx += 1

        tk.Label(self.master, text="Progresso:").grid(row=row_idx, column=0, sticky="w", padx=10, pady=5)
        self.progress_bar = ttk.Progressbar(self.master, orient="horizontal", length=400, mode="determinate", variable=self.progress_value)
        self.progress_bar.grid(row=row_idx, column=1, sticky="ew", padx=10, pady=5)
        row_idx += 1

        self.progress_label = ttk.Label(self.master, text="Pronto.", foreground="blue", wraplength=450)
        self.progress_label.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        row_idx += 1

        # --- Botão "Fechar" ---
        self.close_button = ttk.Button(self.master, text="Fechar", command=self.master.quit, style="Red.TButton")
        self.close_button.grid(row=row_idx, column=1, sticky="se", padx=10, pady=10) 
        row_idx +=1 

    def toggle_cloud_platform_dropdown(self):
        # AQUI A LÓGICA MUDOU UM POUCO para garantir que o frame inteiro seja habilitado/desabilitado.
        if self.solution_var.get():
            # Habilita todos os widgets dentro do frame
            for child in self.cloud_platform_frame.winfo_children():
                child.config(state=tk.NORMAL)
        else:
            # Desabilita todos os widgets dentro do frame
            for child in self.cloud_platform_frame.winfo_children():
                child.config(state=tk.DISABLED)


    def browse_audio_file(self):
        file_path = filedialog.askopenfilename(
            title="Selecionar Arquivo de Áudio",
            filetypes=[("Arquivos de Áudio", "*.mp3 *.wav *.m4a *.flac"), ("Todos os Arquivos", "*.*")]
        )
        if file_path:
            self.audio_file_path.set(file_path)

    def save_output_file(self):
        file_path = filedialog.asksaveasfilename(
            title="Salvar Transcrição",
            defaultextension=".txt",
            filetypes=[("Arquivo de Texto", "*.txt"), ("Todos os Arquivos", "*.*")],
            initialfile=self.output_file_path.get()
        )
        if file_path:
            self.output_file_path.set(file_path)

    def suggest_output_filename(self, *args):
        audio_path = self.audio_file_path.get()
        if audio_path:
            base_name = os.path.basename(audio_path)
            file_name_without_ext = os.path.splitext(base_name)[0]
            suggested_name = f"Transcricao-{file_name_without_ext}.txt"
            self.output_file_path.set(suggested_name)
        else:
            self.output_file_path.set("transcricao_final.txt")

    def update_progress_label(self, message):
        self.master.after(0, lambda: self.progress_label.config(text=message))

    def update_progress_bar_value(self, value):
        self.master.after(0, lambda: self.progress_value.set(value))

    def clear_input_fields(self):
        self.audio_file_path.set("")
        self.output_file_path.set("")

    def start_transcription_thread(self):
        self.stop_transcription_event.clear()

        audio_path = self.audio_file_path.get()
        model_size = self.model_var.get()
        use_gpu = self.gpu_var.get()
        generate_analysis_option = self.analysis_var.get()
        generate_solution_option = self.solution_var.get()
        selected_cloud_platform = self.cloud_platform_var.get()
        output_path = self.output_file_path.get()

        if not audio_path:
            messagebox.showwarning("Entrada Ausente", "Por favor, selecione um arquivo de áudio para transcrever.")
            logger.warning("Tentativa de transcrição sem arquivo de áudio selecionado.")
            return
        if not output_path:
            messagebox.showwarning("Entrada Ausente", "Por favor, defina o nome e local do arquivo de saída.")
            logger.warning("Tentativa de transcrição sem local de saída definido.")
            return

        if (generate_analysis_option or generate_solution_option) and not API_KEY:
            messagebox.showwarning("API Key Ausente", "Para gerar a análise ou solução com a GEM, você precisa configurar sua chave de API do Google Gemini no script.")
            logger.warning("Análise/Solução da GEM solicitada, mas API Key do Gemini não configurada.")
            return
        
        if generate_solution_option and not selected_cloud_platform:
            messagebox.showwarning("Seleção Ausente", "Por favor, selecione uma Plataforma Cloud para gerar a solução.")
            logger.warning("Gerar Solução marcado, mas plataforma Cloud não selecionada.")
            return


        self.transcribe_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)

        self.update_progress_label("Iniciando transcrição...")
        self.update_progress_bar_value(0)
        logger.info(f"Iniciando thread de transcrição para '{audio_path}' (Modelo: {model_size}, GPU: {use_gpu}, Análise GEM: {generate_analysis_option}, Solução GEM: {generate_solution_option}, Plataforma Cloud: {selected_cloud_platform})")

        transcription_thread = threading.Thread(
            target=transcribe_audio_logic,
            args=(audio_path, model_size, use_gpu, output_path, generate_analysis_option,
                  generate_solution_option, selected_cloud_platform,
                  self.update_progress_label, self.update_progress_bar_value, self.stop_transcription_event,
                  self.clear_input_fields)
        )
        transcription_thread.start()

        self.master.after(100, lambda: self.check_transcription_thread(transcription_thread))

    def cancel_transcription(self):
        response = messagebox.askyesno("Confirmar Cancelamento", "Tem certeza que deseja cancelar a transcrição?")
        if response:
            self.stop_transcription_event.set()
            self.update_progress_label("Sinal de cancelamento enviado...")
            logger.info("Solicitação de cancelamento de transcrição enviada.")

    def check_transcription_thread(self, thread):
        if thread.is_alive():
            self.master.after(100, lambda: self.check_transcription_thread(thread))
        else:
            self.transcribe_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
            logger.info("Thread de transcrição finalizada e botões reativados.")
            
# --- Execução Principal ---
if __name__ == "__main__":
    logger.info("Aplicação 'CesarVox' iniciada.")
    root = tk.Tk()
    app = TranscriptionApp(root)
    root.mainloop()
    logger.info("Aplicação 'CesarVox' encerrada.")