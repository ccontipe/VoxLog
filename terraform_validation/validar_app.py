import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import glob
import time
import threading
import sys
import logging

from terraform_artifact_generator import generate_terraform_artifacts
import refinador_terraform_aws
import refinador_terraform_azu
import refinador_terraform_gcp

class ValidarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VALIDAR_APP - Validador de Soluções Terraform")
        self.root.geometry("600x480")
        self.root.resizable(False, False)

        self._configura_log()
        logging.info("Aplicação iniciada.")

        self.pasta_tf = tk.StringVar()
        self.arquivo_gem = tk.StringVar()
        self.status_text = tk.StringVar(value="Aguardando seleção dos arquivos...")
        self.tempo_decorrido = tk.StringVar(value="Tempo decorrido: 00:00:00")
        self.tf_files = []
        self.cloud_selected = tk.StringVar(value="Azure")

        frame_principal = tk.Frame(self.root)
        frame_principal.pack(anchor="w", fill=tk.BOTH, expand=True, padx=12, pady=10)

        frame_tf = tk.Frame(frame_principal)
        frame_tf.pack(anchor="w", pady=2, fill=tk.X)
        self.btn_tf = tk.Button(
            frame_tf, text="Terraform(s)", fg="blue",
            width=12, height=1, font=('Arial', 9, 'bold'),
            command=self.selecionar_pasta_tf
        )
        self.btn_tf.pack(side=tk.LEFT)
        tk.Label(frame_tf, text="Pasta .tf:").pack(side=tk.LEFT, padx=5)
        tk.Entry(frame_tf, textvariable=self.pasta_tf, width=38, state='readonly').pack(side=tk.LEFT, fill=tk.X, expand=True)

        frame_gem = tk.Frame(frame_principal)
        frame_gem.pack(anchor="w", pady=2, fill=tk.X)
        self.btn_gem = tk.Button(
            frame_gem, text="Sol. Técnica", fg="green",
            width=12, height=1, font=('Arial', 9, 'bold'),
            command=self.selecionar_arquivo_gem
        )
        self.btn_gem.pack(side=tk.LEFT)
        tk.Label(frame_gem, text="Solução Técnica:").pack(side=tk.LEFT, padx=5)
        tk.Entry(frame_gem, textvariable=self.arquivo_gem, width=38, state='readonly').pack(side=tk.LEFT, fill=tk.X, expand=True)

        frame_files = tk.LabelFrame(frame_principal, text="Arquivos Localizados", padx=8, pady=4)
        frame_files.pack(anchor="w", fill=tk.X, pady=8)
        self.label_num_tf = tk.Label(frame_files, text="Arquivos .tf encontrados: 0")
        self.label_num_tf.pack(anchor="w", pady=(0, 4))

        tk.Label(frame_files, text="Arquivo de Referência:").pack(anchor="w", pady=(2,0))
        self.gem_label = tk.Label(frame_files, text="", anchor="w")
        self.gem_label.pack(anchor="w", fill=tk.X)

        frame_cloud = tk.Frame(frame_principal)
        frame_cloud.pack(anchor="w", fill=tk.X, pady=(5, 12))
        tk.Label(frame_cloud, text="Cloud:").pack(anchor="w")
        self.cloud_combobox = ttk.Combobox(frame_cloud, textvariable=self.cloud_selected, state="readonly", width=15)
        self.cloud_combobox['values'] = ("Azure", "AWS", "GCP")
        self.cloud_combobox.current(0)
        self.cloud_combobox.pack(anchor="w", padx=4, pady=2)
        self.cloud_combobox.bind("<<ComboboxSelected>>", self.atualiza_cloud)

        frame_botoes = tk.Frame(frame_principal)
        frame_botoes.pack(anchor="w", pady=(14, 3), fill=tk.X)
        self.btn_validate = tk.Button(
            frame_botoes, text="Validar", fg="green",
            font=('Arial', 10, 'bold'), command=self.validar, state='disabled', width=12
        )
        self.btn_validate.pack(side=tk.LEFT, padx=(0, 5))
        self.btn_fechar = tk.Button(
            frame_botoes, text="Fechar", fg="red",
            font=('Arial', 10, 'bold'), command=self.fechar_app, width=12
        )
        self.btn_fechar.pack(side=tk.LEFT)

        self.tempo_label = tk.Label(frame_principal, textvariable=self.tempo_decorrido, font=('Arial', 10))
        self.tempo_label.pack(anchor="w")

        tk.Label(frame_principal, text="").pack(anchor="w")  # Espaço extra

        self.status_bar = tk.Label(self.root, textvariable=self.status_text, bd=1, relief=tk.SUNKEN, anchor="w")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.rodando = False
        self.tempo_inicial = 0

    def _configura_log(self):
        logging.basicConfig(
            filename='validarLog.txt',
            filemode='a',
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        logging.info("Log configurado.")

    def limpar_variaveis_memoria(self):
        self.pasta_tf.set("")
        self.arquivo_gem.set("")
        self.status_text.set("")
        self.tempo_decorrido.set("Tempo decorrido: 00:00:00")
        self.tf_files.clear()
        self.label_num_tf.config(text="Arquivos .tf encontrados: 0")
        self.gem_label.config(text="")
        self.rodando = False
        self.tempo_inicial = 0
        self.cloud_selected.set("Azure")
        if hasattr(self, 'cloud_combobox'):
            self.cloud_combobox.current(0)
        self.root.update_idletasks()
        logging.info("Variáveis de memória e referências de arquivos limpas.")

    def selecionar_pasta_tf(self):
        pasta = filedialog.askdirectory(title="Local TERRAFORM")
        if pasta:
            self.pasta_tf.set(pasta)
            self.listar_arquivos_tf(pasta)
            logging.info(f"Pasta de arquivos .tf selecionada: {pasta}")
        else:
            self.status_text.set("Seleção da pasta dos .tf cancelada.")
            self.tf_files = []
            self.label_num_tf.config(text="Arquivos .tf encontrados: 0")
            logging.warning("Seleção da pasta dos arquivos .tf foi cancelada pelo usuário.")
        self._atualiza_estado_botao()

    def listar_arquivos_tf(self, pasta):
        self.tf_files = glob.glob(os.path.join(pasta, "*.tf"))
        total = len(self.tf_files)
        if total:
            self.label_num_tf.config(text=f"Arquivos .tf encontrados: {total}")
            self.status_text.set(f"{total} arquivos .tf encontrados.")
            logging.info(f"{total} arquivos .tf encontrados.")
        else:
            self.label_num_tf.config(text="Nenhum arquivo .tf encontrado.")
            self.status_text.set("Nenhum arquivo .tf encontrado.")
            logging.warning("Nenhum arquivo .tf encontrado na pasta selecionada.")

    def selecionar_arquivo_gem(self):
        arq = filedialog.askopenfilename(
            title="Selecione o arquivo de referência GEM Solução",
            filetypes=[("Arquivos GEM", "GEM - Solucao*"), ("Todos os arquivos", "*.*")]
        )
        if arq:
            self.arquivo_gem.set(arq)
            self.gem_label.config(text=os.path.basename(arq))
            self.status_text.set("Arquivo de referência selecionado.")
            logging.info(f"Arquivo de referência selecionado: {arq}")
        else:
            self.gem_label.config(text="")
            self.arquivo_gem.set("")
            self.status_text.set("Seleção do arquivo de referência cancelada.")
            logging.warning("Seleção do arquivo de referência GEM Solução foi cancelada pelo usuário.")
        self._atualiza_estado_botao()

    def atualiza_cloud(self, event):
        cloud = self.cloud_combobox.get()
        self.cloud_selected.set(cloud)
        logging.info(f"Cloud selecionada: {cloud}")
        self._atualiza_estado_botao()

    def _cloud_no_nome_arquivo(self):
        nome = self.arquivo_gem.get().lower()
        cloud = self.cloud_selected.get().lower()
        if not nome:
            return False
        if cloud == "aws" and "aws" in nome:
            return True
        elif cloud == "azure" and "azure" in nome:
            return True
        elif cloud == "gcp" and "gcp" in nome:
            return True
        else:
            return False

    def _atualiza_estado_botao(self):
        if not self.tf_files:
            self.btn_validate.config(state='disabled')
            self.status_text.set("Selecione a pasta dos arquivos .tf.")
            return
        if not self.arquivo_gem.get():
            self.btn_validate.config(state='disabled')
            self.status_text.set("Selecione o arquivo de referência GEM Solução.")
            return
        if not self._cloud_no_nome_arquivo():
            self.btn_validate.config(state='disabled')
            self.status_text.set("Cloud selecionada não corresponde ao arquivo de solução técnica.")
            return
        self.btn_validate.config(state='normal')
        self.status_text.set("Pronto para validação.")
        logging.info("Interface pronta para validação.")

    def validar(self):
        self.btn_validate.config(state='disabled')
        self.status_text.set(f"Iniciando validação para cloud: {self.cloud_selected.get()} ...")
        self.rodando = True
        self.tempo_inicial = time.time()
        self.atualiza_tempo()
        logging.info(f"Validação iniciada para cloud: {self.cloud_selected.get()}.")
        thread = threading.Thread(target=self.pipeline_validacao)
        thread.start()

    def pipeline_validacao(self):
        try:
            pasta_tf = self.pasta_tf.get()
            arquivo_gem = self.arquivo_gem.get()
            cloud = self.cloud_selected.get().lower()
            self.status_text.set("Iniciando parsing/validação dos arquivos .tf...")
            logging.info("Iniciando parsing/validação dos arquivos .tf...")
            arquivos_gerados = generate_terraform_artifacts(
                gemini_output=open(arquivo_gem, encoding="utf-8").read(),
                output_dir=pasta_tf,
                cloud_provider=cloud,
                run_lint=True
            )
            self.status_text.set("Iniciando refinamento dos arquivos Terraform...")
            logging.info(f"Iniciando refinamento dos arquivos para: {cloud.upper()}")
            if cloud == "aws":
                refinador_terraform_aws.refinar_terraform_aws(pasta_tf, arquivo_gem)
            elif cloud == "azure":
                refinador_terraform_azu.refinar_terraform_azure(pasta_tf, arquivo_gem)
            elif cloud == "gcp":
                refinador_terraform_gcp.refinar_terraform_gcp(pasta_tf, arquivo_gem)
            else:
                logging.error("Cloud não suportada.")
                self.status_text.set("Erro: Cloud não suportada.")
                self.limpar_variaveis_memoria()
                return

            self.status_text.set(f"Validação/refino concluído para cloud: {self.cloud_selected.get()}.")
            logging.info(f"Validação/refino concluído para cloud: {self.cloud_selected.get()}.")
            messagebox.showinfo("Validação/refino concluído", f"Processo concluído para cloud: {self.cloud_selected.get()}.\nConfira o relatório na pasta dos arquivos .tf.")
        except Exception as e:
            logging.exception("Erro no pipeline de validação/refino.")
            self.status_text.set(f"Erro: {str(e)}")
            messagebox.showerror("Erro na Validação", f"Ocorreu um erro: {str(e)}")
        finally:
            self.rodando = False
            self.limpar_variaveis_memoria()

    def atualiza_tempo(self):
        if self.rodando:
            elapsed = int(time.time() - self.tempo_inicial)
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            s = elapsed % 60
            self.tempo_decorrido.set(f"Tempo decorrido: {h:02}:{m:02}:{s:02}")
            self.root.after(200, self.atualiza_tempo)
        else:
            self.tempo_decorrido.set("Tempo decorrido: 00:00:00")

    def fechar_app(self):
        logging.info("Fechamento da aplicação solicitado pelo usuário.")
        self.limpar_variaveis_memoria()
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = ValidarApp(root)
    root.mainloop()
