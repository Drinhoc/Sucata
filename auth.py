"""
Módulo de autenticação compartilhado
Usado por todas as páginas para verificar sessão e restaurar via cookie
"""

import os
import streamlit as st

COOKIE_NAME = "auth_token"
AUTH_COOKIE_SECRET = os.getenv("AUTH_COOKIE_SECRET", "sucata-cookie-secret-change-me")
AUTH_DAYS = int(os.getenv("AUTH_DAYS", "7"))


def _get_serializer():
    from itsdangerous import URLSafeTimedSerializer
    return URLSafeTimedSerializer(AUTH_COOKIE_SECRET)


def _restore_from_token(token: str) -> bool:
    """Valida o token e rehidrata o session_state. Retorna True se bem-sucedido."""
    try:
        from itsdangerous import SignatureExpired, BadSignature
        data = _get_serializer().loads(token, max_age=AUTH_DAYS * 86400)
        st.session_state.authenticated = True
        st.session_state.user_id = data["user_id"]
        st.session_state.username = data["username"]
        st.session_state.user_name = data["user_name"]
        st.session_state.role = data["role"]
        return True
    except SignatureExpired:
        return False
    except Exception:
        return False


def get_controller():
    """Retorna uma instância do CookieController."""
    from streamlit_cookies_controller import CookieController
    return CookieController()


def set_auth_cookie(controller, user: dict) -> None:
    """Grava o cookie de autenticação assinado com os dados do usuário."""
    payload = {
        "user_id": user["id"],
        "username": user["username"],
        "user_name": user["name"],
        "role": user["role"],
    }
    token = _get_serializer().dumps(payload)
    controller.set(COOKIE_NAME, token, max_age=AUTH_DAYS * 86400)


def clear_auth_cookie(controller) -> None:
    """Remove o cookie de autenticação."""
    try:
        controller.remove(COOKIE_NAME)
    except Exception:
        pass


def require_auth(required_role: str = None) -> None:
    """
    Verifica autenticação e role. Chame no início de cada página.

    Fluxo:
    1. Se já autenticado no session_state → segue.
    2. Se não, tenta restaurar do cookie:
       - Frame 1: controller monta (async); sem token ainda → para silenciosamente.
       - Frame 2 (trigger do componente): token disponível → restaura → rerun.
       - Frame 3: autenticado → página carrega.
    3. Se sem cookie ou token inválido → mostra aviso e para.
    """
    if st.session_state.get("authenticated"):
        if required_role and st.session_state.get("role") != required_role:
            st.error("🚫 Acesso restrito a administradores.")
            st.stop()
        return

    # Renderiza o controller (DEVE vir antes de qualquer st.stop())
    controller = get_controller()
    token = controller.get(COOKIE_NAME)

    if token:
        if _restore_from_token(token):
            # Sessão restaurada — rerun para exibir a página autenticada
            st.session_state.pop("_cookie_checked", None)
            st.rerun()
        else:
            # Token inválido ou expirado
            clear_auth_cookie(controller)
            st.error("⚠️ Sessão expirada. Faça login na página principal.")
            st.stop()

    # Sem token ainda — pode ser o primeiro frame (cookie carregando async)
    if not st.session_state.get("_cookie_checked"):
        st.session_state["_cookie_checked"] = True
        # Parada silenciosa: o componente montado vai disparar um rerun
        st.stop()

    # Confirmado: sem cookie válido
    st.warning("🔐 Você não está autenticado.")
    st.info("👆 Acesse a **página inicial** no menu lateral para fazer login.")
    st.stop()
