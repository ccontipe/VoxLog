# VoxLog

VoxLog é um projeto Python para automação de transcrição de áudio, análise de problemas, geração de soluções técnicas e integração com serviços de IA e infraestrutura como código.

## Descrição

O projeto automatiza o processamento e análise de arquivos de áudio, integração com APIs de IA (como Google Generative AI), geração e validação de arquivos Terraform, além de exportação de resultados em diferentes formatos. Ele é indicado para apoiar fluxos técnicos em equipes de DevOps, SRE e Arquitetura.

## Instalação

Clone este repositório e instale as dependências do projeto via pip.  
Guarde suas chaves e variáveis sensíveis em arquivos `.env` ou `API Key.txt`, conforme necessário.

git clone https://github.com/ccontipe/VoxLog.git
cd VoxLog
pip install -r requirements.txt

## Uso
Execute o script principal para iniciar o VoxLog:

'python main_app.py'

Scripts auxiliares podem ser executados conforme a necessidade:
python solution_generator.py

## Estrutura do Projeto
- main_app.py: Ponto de entrada principal
- audio_transcriber.py: Transcrição de áudio
- genai.py: Integração com Google Generative AI
- solution_generator.py: Geração de soluções técnicas
- model.py: Modelos e entidades de dados
- problem_analyzer.py: Análise automática de problemas
- output_writers/: Exportação de resultados (ex: PlantUML, Terraform)
- solution_modules/: Soluções específicas para AWS, Azure e GCP
- terraform_validation/: Validação e refinamento de arquivos Terraform
- utils_instalador.py: Utilitários de instalação
- Testes: test_audio_transcriber.py, test_gemini.py

## Contribuição
Pull requests são bem-vindos. Para sugerir melhorias ou reportar bugs, abra uma issue.

## Licença
Este projeto está licenciado sob a licença MIT.

Observações
Não faça commit de arquivos sensíveis ou chaves de API.

Variáveis de ambiente devem estar em arquivos .env, já ignorados pelo .gitignore.

Diretórios de histórico e saída são ignorados para manter o repositório limpo.
