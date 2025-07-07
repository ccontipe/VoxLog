import os
import re
import logging

RECURSOS_AWS = [
    "VPC", "subnet", "NAT", "security group", "EKS", "ECS", "Fargate",
    "API Gateway", "RDS", "PostgreSQL", "Aurora", "SQS", "SNS", "Lambda",
    "Secrets Manager", "IAM", "CloudWatch", "X-Ray", "CloudFront",
    "WAF", "Backup", "KMS", "S3", "ALB", "ELB", "EC2 Instance"
]

MAPA_RECURSOS_TF = {
    "VPC": r'aws_vpc',
    "subnet": r'aws_subnet',
    "NAT": r'aws_nat_gateway',
    "security group": r'aws_security_group',
    "EKS": r'aws_eks_',
    "ECS": r'aws_ecs_',
    "Fargate": r'fargate',
    "API Gateway": r'aws_api_gateway_',
    "RDS": r'aws_db_instance',
    "PostgreSQL": r'engine\s*=\s*"postgres"',
    "Aurora": r'aurora',
    "SQS": r'aws_sqs_queue',
    "SNS": r'aws_sns_topic',
    "Lambda": r'aws_lambda_function',
    "Secrets Manager": r'aws_secretsmanager_secret',
    "IAM": r'aws_iam_',
    "CloudWatch": r'aws_cloudwatch_',
    "X-Ray": r'aws_xray_group',
    "CloudFront": r'aws_cloudfront_distribution',
    "WAF": r'aws_wafv2_web_acl',
    "Backup": r'aws_backup_',
    "KMS": r'aws_kms_key',
    "S3": r'aws_s3_bucket',
    "ALB": r'aws_lb|aws_alb',
    "ELB": r'aws_elb',
    "EC2 Instance": r'aws_instance'
}

TEMPLATES_RECURSOS = {
    "VPC": '''
# Gerado automaticamente - componente faltante: VPC
resource "aws_vpc" "auto_generated" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "auto-vpc"
  }
}
''',
    "subnet": '''
# Gerado automaticamente - componente faltante: subnet
resource "aws_subnet" "auto_generated" {
  vpc_id                  = "vpc-xxxxxx" # Substitua por vpc_id real
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true
  tags = {
    Name = "auto-subnet"
  }
}
''',
    "NAT": '''
# Gerado automaticamente - componente faltante: NAT
resource "aws_nat_gateway" "auto_generated" {
  allocation_id = "eipalloc-xxxxxx" # Substitua por allocation_id válido
  subnet_id     = "subnet-xxxxxx"   # Substitua por subnet_id válido
}
''',
    "security group": '''
# Gerado automaticamente - componente faltante: security group
resource "aws_security_group" "auto_generated" {
  name        = "auto-sg"
  description = "SG gerado automaticamente"
  vpc_id      = "vpc-xxxxxx" # Substitua por vpc_id real

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "auto-sg"
  }
}
''',
    "EKS": '''
# Gerado automaticamente - componente faltante: EKS
resource "aws_eks_cluster" "auto_generated" {
  name     = "auto-eks-cluster"
  role_arn = "arn:aws:iam::123456789012:role/eksClusterRole" # Substitua por um role válido!
  vpc_config {
    subnet_ids = ["subnet-xxxxxxxx"] # Substitua por subnets reais!
  }
}
''',
    "ECS": '''
# Gerado automaticamente - componente faltante: ECS
resource "aws_ecs_cluster" "auto_generated" {
  name = "auto-ecs-cluster"
}
''',
    "Fargate": '''
# Gerado automaticamente - componente faltante: Fargate
resource "aws_ecs_cluster" "auto_generated" {
  name = "auto-fargate-cluster"
}
''',
    "API Gateway": '''
# Gerado automaticamente - componente faltante: API Gateway
resource "aws_api_gateway_rest_api" "auto_generated" {
  name        = "auto-api"
  description = "API Gateway gerado automaticamente"
}
''',
    "RDS": '''
# Gerado automaticamente - componente faltante: RDS
resource "aws_db_instance" "auto_generated" {
  allocated_storage    = 20
  storage_type         = "gp2"
  engine               = "mysql"
  instance_class       = "db.t3.micro"
  name                 = "auto-db"
  username             = "admin"
  password             = "ChangeMe1234!"
  skip_final_snapshot  = true
}
''',
    "PostgreSQL": '''
# Gerado automaticamente - componente faltante: PostgreSQL
resource "aws_db_instance" "auto_generated_pg" {
  allocated_storage    = 20
  storage_type         = "gp2"
  engine               = "postgres"
  engine_version       = "13.7"
  instance_class       = "db.t3.micro"
  name                 = "autopg"
  username             = "admin"
  password             = "ChangeMe1234!"
  skip_final_snapshot  = true
}
''',
    "Aurora": '''
# Gerado automaticamente - componente faltante: Aurora
resource "aws_rds_cluster" "auto_generated" {
  cluster_identifier      = "auto-aurora-cluster"
  engine                 = "aurora-mysql"
  master_username         = "admin"
  master_password         = "ChangeMe1234!"
  skip_final_snapshot     = true
}
''',
    "SQS": '''
# Gerado automaticamente - componente faltante: SQS
resource "aws_sqs_queue" "auto_generated" {
  name = "auto-queue"
}
''',
    "SNS": '''
# Gerado automaticamente - componente faltante: SNS
resource "aws_sns_topic" "auto_generated" {
  name = "auto-topic"
}
''',
    "Lambda": '''
# Gerado automaticamente - componente faltante: Lambda
resource "aws_lambda_function" "auto_generated" {
  filename         = "function.zip"
  function_name    = "auto-lambda"
  role             = "arn:aws:iam::123456789012:role/auto-lambda-role" # Substitua por um role válido!
  handler          = "index.handler"
  runtime          = "python3.9"
  source_code_hash = filebase64sha256("function.zip")
}
''',
    "Secrets Manager": '''
# Gerado automaticamente - componente faltante: Secrets Manager
resource "aws_secretsmanager_secret" "auto_generated" {
  name        = "auto-secret"
  description = "Secret gerado automaticamente"
}
''',
    "IAM": '''
# Gerado automaticamente - componente faltante: IAM
resource "aws_iam_role" "auto_generated" {
  name = "auto-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "ec2.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}
''',
    "CloudWatch": '''
# Gerado automaticamente - componente faltante: CloudWatch
resource "aws_cloudwatch_log_group" "auto_generated" {
  name              = "auto-log-group"
  retention_in_days = 7
}
''',
    "X-Ray": '''
# Gerado automaticamente - componente faltante: X-Ray
resource "aws_xray_group" "auto_generated" {
  group_name = "auto-xray-group"
}
''',
    "CloudFront": '''
# Gerado automaticamente - componente faltante: CloudFront
resource "aws_cloudfront_distribution" "auto_generated" {
  origin {
    domain_name = "auto-s3-bucket.s3.amazonaws.com"
    origin_id   = "S3-auto"
  }
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-auto"
    viewer_protocol_policy = "redirect-to-https"
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
''',
    "WAF": '''
# Gerado automaticamente - componente faltante: WAF
resource "aws_wafv2_web_acl" "auto_generated" {
  name        = "auto-waf"
  scope       = "REGIONAL"
  default_action {
    allow {}
  }
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "auto-waf"
    sampled_requests_enabled   = true
  }
  rule {
    name     = "example-rule"
    priority = 1
    action {
      block {}
    }
    statement {
      byte_match_statement {
        search_string = "bad"
        field_to_match { method {} }
        positional_constraint = "CONTAINS"
        text_transformation { priority = 0, type = "NONE" }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "example-rule"
      sampled_requests_enabled   = true
    }
  }
}
''',
    "Backup": '''
# Gerado automaticamente - componente faltante: Backup
resource "aws_backup_vault" "auto_generated" {
  name = "auto-backup-vault"
}
''',
    "KMS": '''
# Gerado automaticamente - componente faltante: KMS
resource "aws_kms_key" "auto_generated" {
  description             = "Chave KMS gerada automaticamente"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}
''',
    "S3": '''
# Gerado automaticamente - componente faltante: S3
resource "aws_s3_bucket" "auto_generated" {
  bucket = "auto-bucket-${random_id.sufixo.hex}"
  acl    = "private"
  tags = {
    Name = "auto-bucket"
  }
}
''',
    "ALB": '''
# Gerado automaticamente - componente faltante: ALB
resource "aws_lb" "auto_generated" {
  name               = "auto-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = ["subnet-xxxxxx"] # Substitua por subnets reais!
}
''',
    "ELB": '''
# Gerado automaticamente - componente faltante: ELB
resource "aws_elb" "auto_generated" {
  name = "auto-elb"
  availability_zones = ["us-east-1a"]
  listener {
    instance_port     = 80
    instance_protocol = "http"
    lb_port           = 80
    lb_protocol       = "http"
  }
  health_check {
    target              = "HTTP:80/"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 3
  }
}
''',
    "EC2 Instance": '''
# Gerado automaticamente - componente faltante: EC2 Instance
resource "aws_instance" "auto_generated" {
  ami           = "ami-0c55b159cbfafe1f0"  # Exemplo para us-east-1
  instance_type = "t3.micro"
  tags = {
    Name = "auto-instance"
  }
}
'''
}

def extrair_componentes_solucao_aws(arquivo_solucao):
    with open(arquivo_solucao, encoding="utf-8") as f:
        texto = f.read().lower()
    encontrados = []
    for recurso in RECURSOS_AWS:
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
    relatorio.append("==== Resumo do Refino AWS ====\n")
    relatorio.append(f"Componentes previstos na solução: {sorted(componentes_previstos)}")
    relatorio.append(f"\nComponentes encontrados nos arquivos .tf: {sorted(componentes_encontrados)}")
    relatorio.append(f"\nComponentes faltantes (gerados em auto_generated.tf): {sorted(componentes_faltantes)}")
    relatorio.append(f"\nComponentes extras (presentes mas não previstos): {sorted(componentes_extras)}")
    relatorio.append("\nNenhum arquivo .tf existente foi alterado.")
    path_relatorio = os.path.join(pasta_terraform, "resumo_refino_aws.log")
    with open(path_relatorio, "w", encoding="utf-8") as f:
        f.write("\n".join(relatorio))

def refinar_terraform_aws(pasta_terraform, arquivo_solucao_tecnica):
    logger = logging.getLogger(__name__)
    arquivos_tf = [f for f in os.listdir(pasta_terraform) if f.endswith('.tf')]
    if not arquivos_tf:
        print("Nenhum arquivo .tf encontrado para análise.")
        return

    componentes_previstos = set(extrair_componentes_solucao_aws(arquivo_solucao_tecnica))
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

    print(f"Refino AWS concluído. Nenhum arquivo .tf original alterado. Relatório salvo em: resumo_refino_aws.log")
    logger.info("Refino AWS (não-destrutivo) concluído. Relatório salvo.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Refinador NÃO-DESTRUTIVO de arquivos Terraform para AWS.")
    parser.add_argument("--tf_dir", required=True, help="Pasta com arquivos .tf para analisar")
    parser.add_argument("--solucao", required=True, help="Caminho do arquivo da solução técnica (GEM - Solucao Tecnica AWS)")
    args = parser.parse_args()
    refinar_terraform_aws(args.tf_dir, args.solucao)
