# Copyright (c) 2025 Cesar Contipelli Neto
# Todos os direitos reservados.
# Proibida a modificação e distribuição sem autorização do autor.

# text_file_reader.py
import os
import logging

logger = logging.getLogger(__name__)

def read_text_file(file_path):
    """
    Lê arquivos de texto nos formatos suportados e retorna o conteúdo como string UTF-8.
    Suporta: .txt, .md, .docx, .doc, .rtf, .eml, .pdf (opcional), .html (opcional)
    """
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext in ('.txt', '.md', '.rtf'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        elif ext == '.docx':
            from docx import Document
            doc = Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs])
        elif ext == '.doc':
            try:
                import mammoth
                with open(file_path, "rb") as doc_file:
                    result = mammoth.convert_to_html(doc_file)
                    import re
                    return re.sub('<[^<]+?>', '', result.value)
            except ImportError:
                # fallback para textract se mammoth não estiver instalado
                import textract
                text = textract.process(file_path)
                return text.decode('utf-8')
        elif ext == '.eml':
            from email import policy
            from email.parser import BytesParser
            with open(file_path, 'rb') as f:
                msg = BytesParser(policy=policy.default).parse(f)
            return msg.get_body(preferencelist=('plain', 'html')).get_content()
        elif ext == '.pdf':
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    return "\n".join(page.extract_text() or '' for page in pdf.pages)
            except ImportError:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    return "\n".join(page.extract_text() or '' for page in reader.pages)
        elif ext == '.html':
            from bs4 import BeautifulSoup
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f, "html.parser")
                return soup.get_text()
        else:
            raise ValueError(f"Formato de arquivo não suportado: {ext}")
    except Exception as e:
        logger.error(f"Erro ao ler o arquivo '{file_path}': {e}", exc_info=True)
        raise RuntimeError(f"Não foi possível ler o arquivo: {file_path}. Erro: {e}")

if __name__ == "__main__":
    # Teste rápido
    print(read_text_file("exemplo.txt"))
