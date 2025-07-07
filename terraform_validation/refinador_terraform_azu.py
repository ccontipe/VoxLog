# Copyright (c) 2025 Cesar Contipelli Neto
# Todos os direitos reservados.
# Proibida a modificação e distribuição sem autorização do autor.

import os
import re
import logging

RECURSOS_AZURE = [
    "VNet", "subnet", "NSG", "AKS", "VM", "App Service", "SQL Database", "CosmosDB",
    "Storage Account", "Function App", "Application Gateway", "Load Balancer",
    "Key Vault", "DNS Zone", "Public IP", "Network Interface", "Log Analytics",
    "Event Hub", "Service Bus", "Firewall", "Container Registry", "Redis", "VPN Gateway",
    "Bastion"
]

MAPA_RECURSOS_TF = {
    "VNet": r'azurerm_virtual_network',
    "subnet": r'azurerm_subnet',
    "NSG": r'azurerm_network_security_group',
    "AKS": r'azurerm_kubernetes_cluster',
    "VM": r'azurerm_linux_virtual_machine|azurerm_windows_virtual_machine',
    "App Service": r'azurerm_app_service',
    "SQL Database": r'azurerm_mssql_database|azurerm_sql_database',
    "CosmosDB": r'azurerm_cosmosdb_account',
    "Storage Account": r'azurerm_storage_account',
    "Function App": r'azurerm_function_app',
    "Application Gateway": r'azurerm_application_gateway',
    "Load Balancer": r'azurerm_lb',
    "Key Vault": r'azurerm_key_vault',
    "DNS Zone": r'azurerm_dns_zone',
    "Public IP": r'azurerm_public_ip',
    "Network Interface": r'azurerm_network_interface',
    "Log Analytics": r'azurerm_log_analytics_workspace',
    "Event Hub": r'azurerm_eventhub_namespace|azurerm_eventhub',
    "Service Bus": r'azurerm_servicebus_namespace|azurerm_servicebus_queue',
    "Firewall": r'azurerm_firewall',
    "Container Registry": r'azurerm_container_registry',
    "Redis": r'azurerm_redis_cache',
    "VPN Gateway": r'azurerm_vpn_gateway',
    "Bastion": r'azurerm_bastion_host'
}

TEMPLATES_RECURSOS = {
    "VNet": '''
# Gerado automaticamente - componente faltante: VNet
resource "azurerm_virtual_network" "auto_generated" {
  name                = "auto-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = "East US"
  resource_group_name = "auto-generated"
  tags = {
    Environment = "auto"
  }
}
''',
    "subnet": '''
# Gerado automaticamente - componente faltante: subnet
resource "azurerm_subnet" "auto_generated" {
  name                 = "auto-subnet"
  resource_group_name  = "auto-generated"
  virtual_network_name = "auto-vnet"
  address_prefixes     = ["10.0.1.0/24"]
}
''',
    "NSG": '''
# Gerado automaticamente - componente faltante: NSG
resource "azurerm_network_security_group" "auto_generated" {
  name                = "auto-nsg"
  location            = "East US"
  resource_group_name = "auto-generated"
  security_rule {
    name                       = "allow_http"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}
''',
    "AKS": '''
# Gerado automaticamente - componente faltante: AKS
resource "azurerm_kubernetes_cluster" "auto_generated" {
  name                = "auto-aks"
  location            = "East US"
  resource_group_name = "auto-generated"
  dns_prefix          = "auto-aks"
  default_node_pool {
    name       = "default"
    node_count = 1
    vm_size    = "Standard_DS2_v2"
  }
  identity {
    type = "SystemAssigned"
  }
}
''',
    "VM": '''
# Gerado automaticamente - componente faltante: VM
resource "azurerm_linux_virtual_machine" "auto_generated" {
  name                  = "auto-vm"
  resource_group_name   = "auto-generated"
  location              = "East US"
  size                  = "Standard_B1ls"
  admin_username        = "azureuser"
  network_interface_ids = []
  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
    name                 = "auto-osdisk"
  }
  source_image_reference {
    publisher = "Canonical"
    offer     = "UbuntuServer"
    sku       = "18.04-LTS"
    version   = "latest"
  }
  disable_password_authentication = false
  admin_password = "ChangeMe1234!"
}
''',
    "App Service": '''
# Gerado automaticamente - componente faltante: App Service
resource "azurerm_app_service_plan" "auto_generated" {
  name                = "auto-appserviceplan"
  location            = "East US"
  resource_group_name = "auto-generated"
  sku {
    tier = "Basic"
    size = "B1"
  }
}
resource "azurerm_app_service" "auto_generated" {
  name                = "auto-appservice"
  location            = "East US"
  resource_group_name = "auto-generated"
  app_service_plan_id = azurerm_app_service_plan.auto_generated.id
}
''',
    "SQL Database": '''
# Gerado automaticamente - componente faltante: SQL Database
resource "azurerm_mssql_server" "auto_generated" {
  name                         = "auto-mssqlserver"
  resource_group_name          = "auto-generated"
  location                     = "East US"
  version                      = "12.0"
  administrator_login          = "sqladminuser"
  administrator_login_password = "ChangeMe1234!"
}
resource "azurerm_mssql_database" "auto_generated" {
  name           = "auto-database"
  server_id      = azurerm_mssql_server.auto_generated.id
  collation      = "SQL_Latin1_General_CP1_CI_AS"
  sku_name       = "S0"
}
''',
    "CosmosDB": '''
# Gerado automaticamente - componente faltante: CosmosDB
resource "azurerm_cosmosdb_account" "auto_generated" {
  name                = "auto-cosmosdb"
  location            = "East US"
  resource_group_name = "auto-generated"
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"
  consistency_policy {
    consistency_level = "Session"
  }
  geo_location {
    location          = "East US"
    failover_priority = 0
  }
}
''',
    "Storage Account": '''
# Gerado automaticamente - componente faltante: Storage Account
resource "azurerm_storage_account" "auto_generated" {
  name                     = "autostgacct${random_id.sufixo.hex}"
  resource_group_name      = "auto-generated"
  location                 = "East US"
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags = {
    Environment = "auto"
  }
}
''',
    "Function App": '''
# Gerado automaticamente - componente faltante: Function App
resource "azurerm_storage_account" "auto_generated_func" {
  name                     = "funcstgacct${random_id.sufixo.hex}"
  resource_group_name      = "auto-generated"
  location                 = "East US"
  account_tier             = "Standard"
  account_replication_type = "LRS"
}
resource "azurerm_app_service_plan" "auto_generated_func" {
  name                = "auto-func-asp"
  location            = "East US"
  resource_group_name = "auto-generated"
  sku {
    tier = "Dynamic"
    size = "Y1"
  }
}
resource "azurerm_function_app" "auto_generated" {
  name                       = "auto-funcapp"
  location                   = "East US"
  resource_group_name        = "auto-generated"
  app_service_plan_id        = azurerm_app_service_plan.auto_generated_func.id
  storage_account_name       = azurerm_storage_account.auto_generated_func.name
  storage_account_access_key = azurerm_storage_account.auto_generated_func.primary_access_key
  version                    = "~4"
}
''',
    "Application Gateway": '''
# Gerado automaticamente - componente faltante: Application Gateway
resource "azurerm_application_gateway" "auto_generated" {
  name                = "auto-appgw"
  resource_group_name = "auto-generated"
  location            = "East US"
  sku {
    name     = "Standard_Small"
    tier     = "Standard"
    capacity = 2
  }
  gateway_ip_configuration {
    name      = "auto-gwip"
    subnet_id = "auto-subnet-id" # Substitua pelo id real de um recurso azurerm_subnet
  }
  frontend_port {
    name = "appGatewayFrontendPort"
    port = 80
  }
  frontend_ip_configuration {
    name                 = "appGatewayFrontendIP"
    public_ip_address_id = "auto-public-ip-id" # Substitua pelo id real de um recurso azurerm_public_ip
  }
}
''',
    "Load Balancer": '''
# Gerado automaticamente - componente faltante: Load Balancer
resource "azurerm_lb" "auto_generated" {
  name                = "auto-lb"
  location            = "East US"
  resource_group_name = "auto-generated"
  sku                 = "Standard"
  frontend_ip_configuration {
    name                 = "auto-frontend"
    public_ip_address_id = "auto-public-ip-id" # Substitua pelo id real de um recurso azurerm_public_ip
  }
  tags = {
    Environment = "auto"
  }
}
''',
    "Key Vault": '''
# Gerado automaticamente - componente faltante: Key Vault
resource "azurerm_key_vault" "auto_generated" {
  name                        = "autokeyvault${random_id.sufixo.hex}"
  location                    = "East US"
  resource_group_name         = "auto-generated"
  tenant_id                   = "00000000-0000-0000-0000-000000000000" # Substitua pelo tenant real
  sku_name                    = "standard"
  soft_delete_enabled         = true
  purge_protection_enabled    = false
  access_policy {
    tenant_id = "00000000-0000-0000-0000-000000000000"
    object_id = "00000000-0000-0000-0000-000000000000"
    key_permissions = [
      "get", "list"
    ]
    secret_permissions = [
      "get", "list"
    ]
  }
  tags = {
    Environment = "auto"
  }
}
''',
    "DNS Zone": '''
# Gerado automaticamente - componente faltante: DNS Zone
resource "azurerm_dns_zone" "auto_generated" {
  name                = "auto.com"
  resource_group_name = "auto-generated"
}
''',
    "Public IP": '''
# Gerado automaticamente - componente faltante: Public IP
resource "azurerm_public_ip" "auto_generated" {
  name                = "auto-publicip"
  location            = "East US"
  resource_group_name = "auto-generated"
  allocation_method   = "Static"
  sku                 = "Standard"
}
''',
    "Network Interface": '''
# Gerado automaticamente - componente faltante: Network Interface
resource "azurerm_network_interface" "auto_generated" {
  name                = "auto-nic"
  location            = "East US"
  resource_group_name = "auto-generated"
  ip_configuration {
    name                          = "internal"
    subnet_id                     = "auto-subnet-id"
    private_ip_address_allocation = "Dynamic"
  }
}
''',
    "Log Analytics": '''
# Gerado automaticamente - componente faltante: Log Analytics
resource "azurerm_log_analytics_workspace" "auto_generated" {
  name                = "auto-log"
  location            = "East US"
  resource_group_name = "auto-generated"
  sku                 = "PerGB2018"
  retention_in_days   = 30
}
''',
    "Event Hub": '''
# Gerado automaticamente - componente faltante: Event Hub
resource "azurerm_eventhub_namespace" "auto_generated" {
  name                = "auto-ehns"
  location            = "East US"
  resource_group_name = "auto-generated"
  sku                 = "Standard"
  capacity            = 1
}
resource "azurerm_eventhub" "auto_generated" {
  name                = "auto-eventhub"
  namespace_name      = azurerm_eventhub_namespace.auto_generated.name
  resource_group_name = "auto-generated"
  partition_count     = 2
  message_retention   = 1
}
''',
    "Service Bus": '''
# Gerado automaticamente - componente faltante: Service Bus
resource "azurerm_servicebus_namespace" "auto_generated" {
  name                = "auto-sbns"
  location            = "East US"
  resource_group_name = "auto-generated"
  sku                 = "Standard"
}
resource "azurerm_servicebus_queue" "auto_generated" {
  name                = "auto-queue"
  resource_group_name = "auto-generated"
  namespace_name      = azurerm_servicebus_namespace.auto_generated.name
  enable_partitioning = true
}
''',
    "Firewall": '''
# Gerado automaticamente - componente faltante: Firewall
resource "azurerm_firewall" "auto_generated" {
  name                = "auto-firewall"
  location            = "East US"
  resource_group_name = "auto-generated"
  sku_name            = "AZFW_VNet"
  sku_tier            = "Standard"
  ip_configuration {
    name                 = "configuration"
    subnet_id            = "auto-subnet-id" # Substitua por id real de um recurso azurerm_subnet
    public_ip_address_id = "auto-public-ip-id" # Substitua por id real de um recurso azurerm_public_ip
  }
  tags = {
    Environment = "auto"
  }
}
''',
    "Container Registry": '''
# Gerado automaticamente - componente faltante: Container Registry
resource "azurerm_container_registry" "auto_generated" {
  name                = "autocontainerreg${random_id.sufixo.hex}"
  resource_group_name = "auto-generated"
  location            = "East US"
  sku                 = "Basic"
  admin_enabled       = true
}
''',
    "Redis": '''
# Gerado automaticamente - componente faltante: Redis
resource "azurerm_redis_cache" "auto_generated" {
  name                = "auto-redis"
  location            = "East US"
  resource_group_name = "auto-generated"
  capacity            = 1
  family              = "C"
  sku_name            = "Basic"
}
''',
    "VPN Gateway": '''
# Gerado automaticamente - componente faltante: VPN Gateway
resource "azurerm_vpn_gateway" "auto_generated" {
  name                = "auto-vpn"
  location            = "East US"
  resource_group_name = "auto-generated"
  virtual_hub_id      = "auto-virtual-hub-id" # Substitua por id real
}
''',
    "Bastion": '''
# Gerado automaticamente - componente faltante: Bastion
resource "azurerm_bastion_host" "auto_generated" {
  name                = "auto-bastion"
  location            = "East US"
  resource_group_name = "auto-generated"
  ip_configuration {
    name                 = "configuration"
    subnet_id            = "auto-subnet-id"
    public_ip_address_id = "auto-public-ip-id"
  }
}
'''
}

def extrair_componentes_solucao_azure(arquivo_solucao):
    with open(arquivo_solucao, encoding="utf-8") as f:
        texto = f.read().lower()
    encontrados = []
    for recurso in RECURSOS_AZURE:
        if recurso.lower() in texto:
            encontrados.append(recurso)
    return encontrados

def extrair_blocos_presentes(pasta_terraform):
    presentes = set()
    arquivos_tf = [f for f in os.listdir(pasta_terraform) if f.endswith('.tf')]
    for fname in arquivos_tf:
        path = os.path.join(pasta_terraform, fname)
        with open(path, encoding="utf-8") as f:
            conteudo = f.read()
        for recurso, regex in MAPA_RECURSOS_TF.items():
            if re.search(regex, conteudo, re.IGNORECASE):
                presentes.add(recurso)
    return presentes

def criar_arquivo_auto_generated(pasta_terraform, componentes_faltantes):
    if not componentes_faltantes:
        return
    arquivo_auto = os.path.join(pasta_terraform, "auto_generated.tf")
    blocos_gerados = []
    for componente in componentes_faltantes:
        template = TEMPLATES_RECURSOS.get(componente)
        if template:
            blocos_gerados.append(template.strip())
        else:
            blocos_gerados.append(f"# ATENÇÃO: Template não definido para {componente}")
    with open(arquivo_auto, "w", encoding="utf-8") as f:
        f.write("# ================================\n")
        f.write("# Blocos gerados automaticamente\n")
        f.write("# Revise e complete conforme necessário!\n")
        f.write("# ================================\n\n")
        f.write("\n\n".join(blocos_gerados))
        f.write("\n")

def gerar_relatorio_resumido(pasta_terraform, componentes_previstos, componentes_encontrados, componentes_faltantes, componentes_extras):
    relatorio = []
    relatorio.append("==== Resumo do Refino Azure ====\n")
    relatorio.append(f"Componentes previstos na solução: {sorted(componentes_previstos)}")
    relatorio.append(f"\nComponentes encontrados nos arquivos .tf: {sorted(componentes_encontrados)}")
    relatorio.append(f"\nComponentes faltantes (gerados em auto_generated.tf): {sorted(componentes_faltantes)}")
    relatorio.append(f"\nComponentes extras (presentes mas não previstos): {sorted(componentes_extras)}")
    relatorio.append("\nNenhum arquivo .tf existente foi alterado.")
    path_relatorio = os.path.join(pasta_terraform, "resumo_refino_azure.log")
    with open(path_relatorio, "w", encoding="utf-8") as f:
        f.write("\n".join(relatorio))

def refinar_terraform_azure(pasta_terraform, arquivo_solucao_tecnica):
    logger = logging.getLogger(__name__)
    arquivos_tf = [f for f in os.listdir(pasta_terraform) if f.endswith('.tf')]
    if not arquivos_tf:
        print("Nenhum arquivo .tf encontrado para análise.")
        return

    componentes_previstos = set(extrair_componentes_solucao_azure(arquivo_solucao_tecnica))
    componentes_encontrados = extrair_blocos_presentes(pasta_terraform)
    componentes_faltantes = componentes_previstos - componentes_encontrados
    componentes_extras = componentes_encontrados - componentes_previstos

    if componentes_faltantes:
        criar_arquivo_auto_generated(pasta_terraform, componentes_faltantes)

    gerar_relatorio_resumido(
        pasta_terraform,
        componentes_previstos,
        componentes_encontrados,
        componentes_faltantes,
        componentes_extras
    )

    print(f"Refino AZURE concluído. Nenhum arquivo .tf original alterado. Relatório salvo em: resumo_refino_azure.log")
    logger.info("Refino AZURE (não-destrutivo) concluído. Relatório salvo.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Refinador NÃO-DESTRUTIVO de arquivos Terraform para Azure.")
    parser.add_argument("--tf_dir", required=True, help="Pasta com arquivos .tf para analisar")
    parser.add_argument("--solucao", required=True, help="Caminho do arquivo da solução técnica (GEM - Solucao Tecnica AZURE)")
    args = parser.parse_args()
    refinar_terraform_azure(args.tf_dir, args.solucao)
