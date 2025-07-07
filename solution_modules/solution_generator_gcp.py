import logging
from tkinter import messagebox
import google.generativeai as genai # Importar diretamente

logger = logging.getLogger(__name__)

# Tenta importar google.generativeai globalmente, essencial para a GEM
try:
    import google.generativeai as genai
except ImportError:
    logger.critical("Erro Fatal: google.generativeai não pôde ser importado. A geração de solução GCP não funcionará. Verifique a instalação.")
    genai = None

def get_solution_prompt_gcp(transcription_text):
    """
    Retorna o prompt completo para a geração de proposta de solução técnica para GCP,
    incluindo todas as diretrizes, exemplos de Terraform e instruções de output para a GEM.
    """
    # --------------------------------------------------------------------------
    # --- CONTEÚDO DA "GEM DE SOLUÇÃO" EMBUTIDO AQUI PARA GCP ---
    # Este prompt é específico para a plataforma GCP.
    # --------------------------------------------------------------------------
    main_solution_prompt_content = (
        "Você é uma inteligência artificial especializada em arquitetura de soluções em nuvem. Sua missão PRINCIPAL é analisar as informações fornecidas (que vêm de uma análise de transcrição de reuniões de negócios) e gerar uma proposta de solução técnica detalhada, **aderindo estritamente às diretrizes e padrões corporativos fornecidos, à plataforma cloud GCP e incluindo scripts Terraform para a infraestrutura**.\n\n"
        "**Sua resposta DEVE seguir rigorosamente a seguinte estrutura, com seções de texto, PlantUML e Terraform separadas por cabeçalhos específicos para facilitar a extração:**\n\n"
        "---\n\n"
        "### Proposta de Solução Técnica: Projeto [Nome do Projeto - inferir da transcrição] em GCP\n\n"
    )

    platform_specific_guidelines = (
        "**1. Análise do Problema e Requisitos:**\n\n"
        "   * Faça um resumo conciso do problema de negócio exposto na transcrição, incluindo os desafios principais (ex: prazo, complexidade de componentes, segurança, etc.).\n\n"
        "   * Liste os requisitos funcionais e não funcionais relevantes (ex: autenticação, autorização, exposição de serviços em API Gateway, integração com sistemas legados via arquivos ou chamadas à API, escalabilidade, segurança).\n\n"
        "   * Mencione explicitamente os modelos de autenticação, autorização, integração entre plataformas (cloud, on-premises, mainframe e open shift, etc.) e as preferências/preocupações levantadas.\n\n"
        "**2. Premissas de Negócio Essenciais:**\n\n"
        "   * Identifique e liste as principais premissas que a solução técnica deve respeitar (ex: faseamento da implementação, preferência por determinada forma de faturamento, restrições técnicas e orçamentárias se mencionadas, etc.).\n\n"
        "**3. Diretrizes e Premissas Corporativas para a Solução (GCP - CRUCIAL):**\n\n"
        "   * **Ambiente de Implantação:** Qualquer novo serviço computacional proposto deve ser criado e implementado exclusivamente no Ambiente GCP.\n"
        "   * **Componentes e Serviços:** As soluções devem utilizar preferencialmente os componentes e serviços nativos disponíveis na GCP.\n"
        "   * **Padrão Corporativo:** Evite o uso de serviços serverless excessivamente granulares (ex: Cloud Functions para lógicas de negócio complexas que seriam microsserviços inteiros). Priorize soluções baseadas em contêineres gerenciados como **Google Kubernetes Engine (GKE)** ou **Cloud Run** para microsserviços. Não utilize soluções proprietárias de outros provedores.\n"
        "   * **Padrão de Artefato Corporativo:** Adapte os conceitos de rede e segurança para o ambiente GCP, utilizando VPCs, subnets, IAM, etc.\n\n"
        "**4. Visão Geral da Solução em GCP:**\n\n"
        "   * Descreva a abordagem geral da solução em GCP.\n"
        "   * Mencione adesão a frameworks de arquitetura GCP (Excellence, Segurança, Eficiência, etc.).\n"
        "   * Identifique o padrão de arquitetura que mais se adapta ao problema identificado, preferencialmente utilizando Microsserviços.\n\n"
        "**5. Componentes da Solução GCP e sua Relação com o Problema/Solução:**\n\n"
        "   * Para cada componente GCP proposto, siga o formato:\n\n"
        "      * **Nome do Componente GCP:** (Ex: Compute Engine, GKE, Cloud Storage)\n"
        "      * **Relação com o Problema/Solução:** Explique como atende ao requisito ou resolve parte do problema.\n"
        "      * **Contribuição para os Pilares do Framework GCP:** Explique como cada componente atende os pilares de arquitetura da GCP.\n"
        "   * Detalhe os serviços propostos e sua relação com a solução e com os requisitos.\n\n"
        "**6. Segurança e Conformidade (PCI SSC):**\n\n"
        "   * Detalhe como a solução atende aos padrões PCI DSS e outros padrões relevantes, similar ao item AWS.\n"
        "   * Explique como os componentes GCP escolhidos contribuem para a conformidade PCI DSS (proteção de dados, segurança de redes, controle de acesso, monitoramento, etc).\n\n"
    )
    plantuml_section_guidelines = (
        "**9. Geração de Diagramas PlantUML (GCP):**\n\n"
        "Gere o código PlantUML para os seguintes diagramas. Os nomes dos elementos devem refletir os serviços GCP.\n\n"
        "**Formato de Saída para PlantUML:**\n"
        "Para cada diagrama, envolva o código PlantUML em blocos de código Markdown ````plantuml` e use cabeçalhos específicos:\n\n"
        "#### Diagrama PlantUML: C1 Contexto\n"
        "```plantuml\n"
        "@startuml <NomeDoDiagrama>\n"
        "!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml\n"
        "LAYOUT_WITH_LEGEND()\n"
        "title Diagrama de Contexto do Sistema: [Nome do Projeto]\n"
        "Person(user, \"Usuário\", \"Utiliza a aplicação\")\n"
        "System(System, \"[Nome do Sistema]\", \"Sistema principal em GCP\")\n"
        "System_Ext(LegacySystem, \"Sistema Legado\", \"Sistema de [descrever] (On-premises)\")\n"
        "Rel(user, System, \"Utiliza\", \"HTTPS\")\n"
        "Rel(System, LegacySystem, \"Integra com\", \"API REST / FTP\")\n"
        "@enduml\n"
        "```\n\n"
        "#### Diagrama PlantUML: C2 Contêineres\n"
        "```plantuml\n"
        "@startuml <NomeDoDiagrama>\n"
        "!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml\n"
        "LAYOUT_WITH_LEGEND()\n"
        "title Diagrama de Contêineres: [Nome do Projeto]\n"
        "System_Boundary(c4_System, \"[Nome do Sistema]\") {\n"
        "  Container(spa, \"Portal Web\", \"JavaScript e React\", \"Permite acesso via navegador\")\n"
        "  Container(api_gateway, \"API Gateway\", \"Cloud Endpoints / API Gateway\", \"Expõe APIs para microsserviços\")\n"
        "  Container(microsservicos_gke, \"Microsservicos Core\", \"Containers no GKE / Cloud Run\", \"Serviços de negócio central\")\n"
        "  ContainerDb(database, \"Banco de Dados Principal\", \"Cloud SQL\", \"Armazena dados transacionais\")\n"
        "  Container(message_broker, \"Message Broker\", \"Pub/Sub\", \"Comunicação assíncrona\")\n"
        "}\n"
        "Person(user, \"Usuário\")\n"
        "System_Ext(LegacySystem, \"Sistema Legado\")\n"
        "Rel(user, spa, \"Acessa\", \"HTTPS\")\n"
        "Rel(spa, api_gateway, \"Faz chamadas API\", \"HTTPS\")\n"
        "Rel(api_gateway, microsservicos_gke, \"Encaminha requisições para\", \"HTTPS\")\n"
        "Rel(microsservicos_gke, database, \"Lê e Escreve\", \"SQL\")\n"
        "Rel(microsservicos_gke, message_broker, \"Envia/Recebe mensagens de\", \"Pub/Sub\")\n"
        "Rel(microsservicos_gke, LegacySystem, \"Integra via\", \"API REST / SFTP\")\n"
        "@enduml\n"
        "```\n\n"
        "#### Diagrama PlantUML: C3 Componentes\n"
        "```plantuml\n"
        "@startuml <NomeDoDiagrama>\n"
        "!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml\n"
        "LAYOUT_WITH_LEGEND()\n"
        "title Diagrama de Componentes: Microsserviços Core (GCP)\n"
        "Container_Boundary(microsservicos_gke, \"Microsserviços Core (GKE/Cloud Run)\") {\n"
        "  Component(comp_users, \"Serviço de Usuários\", \"Spring Boot REST API\", \"Gerencia perfis de usuários\")\n"
        "  Component(comp_products, \"Serviço de Produtos\", \"Node.js REST API\", \"Gerencia catálogo de produtos\")\n"
        "  Component(comp_orders, \"Serviço de Pedidos\", \"Python Flask REST API\", \"Processa pedidos e transações\")\n"
        "  Component(comp_notifications, \"Serviço de Notificações\", \"Java REST API\", \"Envia notificações (email, sms)\")\n"
        "}\n"
        "ContainerDb(database, \"Banco de Dados Principal\")\n"
        "Container(message_broker, \"Message Broker\")\n"
        "Rel(comp_users, database, \"Lê e Escreve\", \"SQL\")\n"
        "Rel(comp_products, database, \"Lê e Escreve\", \"SQL\")\n"
        "Rel(comp_orders, database, \"Lê e Escreve\", \"SQL\")\n"
        "Rel(comp_orders, comp_notifications, \"Envia pedido para\", \"Mensagem Assíncrona\")\n"
        "Rel(comp_notifications, message_broker, \"Publica/Consome de\", \"Pub/Sub\")\n"
        "@enduml\n"
        "```\n\n"
        "#### Diagrama PlantUML: Sequência\n"
        "```plantuml\n"
        "@startuml <NomeDoDiagrama>\n"
        "title Fluxo de Processamento de Pedido\n"
        "participant \"Cliente (Portal Web)\" as Cliente\n"
        "participant \"API Gateway (Cloud Endpoints)\" as APIGateway\n"
        "participant \"Microsserviço de Pedidos (GKE)\" as OrderService\n"
        "participant \"Banco de Dados Principal (Cloud SQL)\" as Database\n"
        "participant \"Message Broker (Pub/Sub)\" as MessageBroker\n"
        "participant \"Microsserviço de Notificações (GKE)\" as NotificationService\n"
        "Cliente -> APIGateway: Requisição de Pedido (HTTPS)\n"
        "APIGateway -> OrderService: Encaminha Pedido (HTTPS)\n"
        "OrderService -> Database: Salva Detalhes do Pedido (SQL)\n"
        "Database --> OrderService: Confirmação\n"
        "OrderService -> MessageBroker: Publica Evento 'Pedido Processado' (Pub/Sub)\n"
        "MessageBroker -> NotificationService: Envia Evento\n"
        "NotificationService -> Cliente: Envia Confirmação de Pedido (Email/SMS)\n"
        "@enduml\n"
        "```\n"
    )
    terraform_templates_str = (
        "**10. Geração de Scripts Terraform (GCP):**\n\n"
        "Gere os blocos de código Terraform para provisionar os recursos GCP propostos, seguindo a estrutura de arquivos e as diretrizes de nomenclatura.\n"
        "Priorize o uso de módulos Terraform (ex: `vpc`, `gke`, `cloud_sql`) para reutilização.\n\n"
        "**Formato de Saída para Terraform:**\n"
        "Para cada arquivo Terraform, envolva o código em blocos de código Markdown ````terraform` e use cabeçalhos específicos:\n\n"
        "#### Arquivo Terraform: versions.tf\n"
        "```terraform\n"
        "# Conteúdo exemplo para GCP\n"
        "```\n\n"
        "#### Arquivo Terraform: providers.tf\n"
        "```terraform\n"
        "# Conteúdo exemplo para GCP\n"
        "```\n\n"
        "#### Arquivo Terraform: variables.tf\n"
        "```terraform\n"
        "# Conteúdo exemplo para GCP\n"
        "```\n\n"
        "#### Arquivo Terraform: main.tf\n"
        "```terraform\n"
        "# Conteúdo exemplo para GCP\n"
        "```\n\n"
        "#### Arquivo Terraform: outputs.tf\n"
        "```terraform\n"
        "# Conteúdo exemplo para GCP\n"
        "```\n"
    )

    full_prompt = (
        main_solution_prompt_content +
        platform_specific_guidelines +
        "**7. Informações Relevantes Adicionais:**\n\n"
        "   * **UTILIZE AS SEGUINTES INFORMAÇÕES SALVAS:**\n\n"
        "      * \"Visão geral dos 10 componentes chave da arquitetura de microsserviços: Cliente, CDN, Load Balancer, API Gateway, Microsserviços, Message Broker, Databases, Identity Provider, Service Registry e Discovery, Service Coordenação (e.g., Zookeeper).\"\n\n"
        + plantuml_section_guidelines +
        terraform_templates_str +
        f"Transcrição analisada:\n{transcription_text}"
    )

    return full_prompt

def call_gemini_api_gcp(prompt_text, prompt_purpose, api_key):
    """
    Chama o modelo Gemini com o texto do prompt fornecido, específico para GCP.
    """
    logger.info(f"[Módulo Solução GCP] Chamando o modelo Gemini para: {prompt_purpose}.")
    if genai is None:
        messagebox.showerror("Erro de Dependência", "A biblioteca 'google.generativeai' não está disponível. Não é possível gerar a solução GCP.")
        logger.error("google.generativeai não carregado. Geração de solução GCP abortada.")
        return None

    genai.configure(api_key=api_key)

    try:
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        logger.debug(f"[Módulo Solução GCP] Prompt enviado para Gemini (primeiros 200 chars): {prompt_text[:200]}...")
        
        response = model.generate_content(prompt_text)
        logger.info(f"[Módulo Solução GCP] Resposta da GEM para {prompt_purpose} recebida com sucesso.")
        return response.text
    except Exception as e:
        logger.error(f"[Módulo Solução GCP] Erro ao chamar a API da GEM para {prompt_purpose}: {e}", exc_info=True)
        messagebox.showerror(f"Erro na GEM de Solução GCP", f"Não foi possível obter a resposta da GEM: {e}")
        return None
