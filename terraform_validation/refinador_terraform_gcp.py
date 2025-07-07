import os
import re
import logging

RECURSOS_GCP = [
    "VPC", "subnet", "firewall", "GKE", "VM Instance", "Cloud SQL", "Pub/Sub",
    "Storage Bucket", "BigQuery", "Cloud Function", "Load Balancer",
    "Cloud DNS", "Cloud NAT", "Cloud Router", "IAM", "Secret Manager",
    "Cloud Run", "VPN", "Memorystore"
]

MAPA_RECURSOS_TF = {
    "VPC": r'google_compute_network',
    "subnet": r'google_compute_subnetwork',
    "firewall": r'google_compute_firewall',
    "GKE": r'google_container_cluster',
    "VM Instance": r'google_compute_instance',
    "Cloud SQL": r'google_sql_database_instance',
    "Pub/Sub": r'google_pubsub_topic|google_pubsub_subscription',
    "Storage Bucket": r'google_storage_bucket',
    "BigQuery": r'google_bigquery_dataset|google_bigquery_table',
    "Cloud Function": r'google_cloudfunctions_function',
    "Load Balancer": r'google_compute_forwarding_rule|google_compute_target_pool|google_compute_backend_service',
    "Cloud DNS": r'google_dns_managed_zone',
    "Cloud NAT": r'google_compute_router_nat',
    "Cloud Router": r'google_compute_router',
    "IAM": r'google_project_iam_|google_service_account',
    "Secret Manager": r'google_secret_manager_secret',
    "Cloud Run": r'google_cloud_run_service',
    "VPN": r'google_compute_vpn_gateway',
    "Memorystore": r'google_redis_instance'
}

TEMPLATES_RECURSOS = {
    "VPC": '''
# Gerado automaticamente - componente faltante: VPC
resource "google_compute_network" "auto_generated" {
  name                    = "auto-vpc"
  auto_create_subnetworks = true
}
''',
    "subnet": '''
# Gerado automaticamente - componente faltante: subnet
resource "google_compute_subnetwork" "auto_generated" {
  name          = "auto-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = "us-central1"
  network       = "auto-vpc"
}
''',
    "firewall": '''
# Gerado automaticamente - componente faltante: firewall
resource "google_compute_firewall" "auto_generated" {
  name    = "auto-fw"
  network = "auto-vpc"
  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }
  source_ranges = ["0.0.0.0/0"]
}
''',
    "GKE": '''
# Gerado automaticamente - componente faltante: GKE
resource "google_container_cluster" "auto_generated" {
  name     = "auto-gke"
  location = "us-central1"
  initial_node_count = 1
  node_config {
    machine_type = "e2-medium"
  }
}
''',
    "VM Instance": '''
# Gerado automaticamente - componente faltante: VM Instance
resource "google_compute_instance" "auto_generated" {
  name         = "auto-instance"
  machine_type = "e2-micro"
  zone         = "us-central1-a"
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }
  network_interface {
    network = "default"
    access_config {}
  }
}
''',
    "Cloud SQL": '''
# Gerado automaticamente - componente faltante: Cloud SQL
resource "google_sql_database_instance" "auto_generated" {
  name             = "auto-sql"
  database_version = "POSTGRES_13"
  region           = "us-central1"
  settings {
    tier = "db-f1-micro"
  }
  root_password = "ChangeMe1234!"
}
''',
    "Pub/Sub": '''
# Gerado automaticamente - componente faltante: Pub/Sub
resource "google_pubsub_topic" "auto_generated" {
  name = "auto-topic"
}
resource "google_pubsub_subscription" "auto_generated" {
  name  = "auto-subscription"
  topic = google_pubsub_topic.auto_generated.name
}
''',
    "Storage Bucket": '''
# Gerado automaticamente - componente faltante: Storage Bucket
resource "google_storage_bucket" "auto_generated" {
  name     = "auto-bucket-${random_id.sufixo.hex}"
  location = "US"
}
''',
    "BigQuery": '''
# Gerado automaticamente - componente faltante: BigQuery
resource "google_bigquery_dataset" "auto_generated" {
  dataset_id                  = "auto_dataset"
  location                    = "US"
  delete_contents_on_destroy  = true
}
resource "google_bigquery_table" "auto_generated" {
  table_id   = "auto_table"
  dataset_id = google_bigquery_dataset.auto_generated.dataset_id
  schema     = <<EOF
[
  {
    "name": "id",
    "type": "STRING",
    "mode": "REQUIRED"
  }
]
EOF
}
''',
    "Cloud Function": '''
# Gerado automaticamente - componente faltante: Cloud Function
resource "google_storage_bucket" "auto_generated_func" {
  name     = "auto-func-bucket"
  location = "US"
}
resource "google_cloudfunctions_function" "auto_generated" {
  name        = "auto-function"
  runtime     = "python39"
  entry_point = "hello_world"
  region      = "us-central1"
  source_archive_bucket = google_storage_bucket.auto_generated_func.name
  source_archive_object = "function-source.zip"
  trigger_http         = true
}
''',
    "Load Balancer": '''
# Gerado automaticamente - componente faltante: Load Balancer
resource "google_compute_forwarding_rule" "auto_generated" {
  name       = "auto-lb"
  load_balancing_scheme = "EXTERNAL"
  port_range = "80"
  target     = "auto-target-proxy" # Substitua pelo target real
}
''',
    "Cloud DNS": '''
# Gerado automaticamente - componente faltante: Cloud DNS
resource "google_dns_managed_zone" "auto_generated" {
  name     = "auto-zone"
  dns_name = "auto.example.com."
}
''',
    "Cloud NAT": '''
# Gerado automaticamente - componente faltante: Cloud NAT
resource "google_compute_router_nat" "auto_generated" {
  name   = "auto-nat"
  router = "auto-router"
  region = "us-central1"
  nat_ip_allocate_option = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}
''',
    "Cloud Router": '''
# Gerado automaticamente - componente faltante: Cloud Router
resource "google_compute_router" "auto_generated" {
  name    = "auto-router"
  network = "auto-vpc"
  region  = "us-central1"
}
''',
    "IAM": '''
# Gerado automaticamente - componente faltante: IAM
resource "google_service_account" "auto_generated" {
  account_id   = "auto-sa"
  display_name = "Auto Service Account"
}
resource "google_project_iam_member" "auto_generated" {
  project = "auto-project-id"
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.auto_generated.email}"
}
''',
    "Secret Manager": '''
# Gerado automaticamente - componente faltante: Secret Manager
resource "google_secret_manager_secret" "auto_generated" {
  secret_id = "auto-secret"
  replication {
    automatic = true
  }
}
''',
    "Cloud Run": '''
# Gerado automaticamente - componente faltante: Cloud Run
resource "google_cloud_run_service" "auto_generated" {
  name     = "auto-run"
  location = "us-central1"
  template {
    spec {
      containers {
        image = "gcr.io/cloudrun/hello"
      }
    }
  }
  traffic {
    percent         = 100
    latest_revision = true
  }
}
''',
    "VPN": '''
# Gerado automaticamente - componente faltante: VPN
resource "google_compute_vpn_gateway" "auto_generated" {
  name    = "auto-vpn"
  network = "auto-vpc"
  region  = "us-central1"
}
''',
    "Memorystore": '''
# Gerado automaticamente - componente faltante: Memorystore
resource "google_redis_instance" "auto_generated" {
  name           = "auto-redis"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = "us-central1"
}
'''
}

def extrair_componentes_solucao_gcp(arquivo_solucao):
    with open(arquivo_solucao, encoding="utf-8") as f:
        texto = f.read().lower()
    encontrados = []
    for recurso in RECURSOS_GCP:
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
    relatorio.append("==== Resumo do Refino GCP ====\n")
    relatorio.append(f"Componentes previstos na solução: {sorted(componentes_previstos)}")
    relatorio.append(f"\nComponentes encontrados nos arquivos .tf: {sorted(componentes_encontrados)}")
    relatorio.append(f"\nComponentes faltantes (gerados em auto_generated.tf): {sorted(componentes_faltantes)}")
    relatorio.append(f"\nComponentes extras (presentes mas não previstos): {sorted(componentes_extras)}")
    relatorio.append("\nNenhum arquivo .tf existente foi alterado.")
    path_relatorio = os.path.join(pasta_terraform, "resumo_refino_gcp.log")
    with open(path_relatorio, "w", encoding="utf-8") as f:
        f.write("\n".join(relatorio))

def refinar_terraform_gcp(pasta_terraform, arquivo_solucao_tecnica):
    logger = logging.getLogger(__name__)
    arquivos_tf = [f for f in os.listdir(pasta_terraform) if f.endswith('.tf')]
    if not arquivos_tf:
        print("Nenhum arquivo .tf encontrado para análise.")
        return

    componentes_previstos = set(extrair_componentes_solucao_gcp(arquivo_solucao_tecnica))
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

    print(f"Refino GCP concluído. Nenhum arquivo .tf original alterado. Relatório salvo em: resumo_refino_gcp.log")
    logger.info("Refino GCP (não-destrutivo) concluído. Relatório salvo.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Refinador NÃO-DESTRUTIVO de arquivos Terraform para GCP.")
    parser.add_argument("--tf_dir", required=True, help="Pasta com arquivos .tf para analisar")
    parser.add_argument("--solucao", required=True, help="Caminho do arquivo da solução técnica (GEM - Solucao Tecnica GCP)")
    args = parser.parse_args()
    refinar_terraform_gcp(args.tf_dir, args.solucao)
