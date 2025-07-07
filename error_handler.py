# error_handler.py

import logging
import sys

class AppError(Exception):
    """
    Exceção base para erros internos da aplicação.
    Permite customização de mensagem e nível de severidade.
    """
    def __init__(self, message, level="error", user_message=None):
        super().__init__(message)
        self.level = level  # "error", "warning", "info"
        self.user_message = user_message or message

def handle_error(e, show_messagebox=True, force_log_level=None):
    """
    Manipula erros/exceções de forma padronizada.
    - Loga sempre.
    - Exibe messagebox (Tkinter) apenas se show_messagebox=True e ambiente permitir.
    - Se usado em CLI/servidor, suprime GUI e mostra mensagem no stderr/stdout.

    Args:
        e: Exception (AppError ou qualquer outra)
        show_messagebox: Se True, tenta mostrar popup caso esteja em modo GUI
        force_log_level: Se definido, força nível de log ("error", "warning", "info")
    """
    # Determinar mensagem e nível
    if isinstance(e, AppError):
        msg = e.user_message
        log_level = force_log_level or e.level
    else:
        msg = str(e)
        log_level = force_log_level or "error"

    # Log
    log_func = getattr(logging, log_level, logging.error)
    log_func(f"[{log_level.upper()}] {msg}", exc_info=True)

    # Messagebox (apenas se explícito e ambiente permitir)
    if show_messagebox:
        try:
            from tkinter import messagebox
            # Verifica se há mainloop ativo para evitar erro em ambiente headless
            if log_level == "info":
                messagebox.showinfo("Informação", msg)
            elif log_level == "warning":
                messagebox.showwarning("Aviso", msg)
            else:
                messagebox.showerror("Erro", msg)
        except Exception:
            # Ambiente headless ou erro em Tkinter
            print(f"[{log_level.upper()}] {msg}", file=sys.stderr if log_level == "error" else sys.stdout)
    else:
        # CLI/server: imprime direto
        print(f"[{log_level.upper()}] {msg}", file=sys.stderr if log_level == "error" else sys.stdout)
