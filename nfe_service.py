"""
Módulo de emissão de NF-e via Nuvem Fiscal API
Gerencia autenticação OAuth2, emissão, consulta e cancelamento de notas fiscais.

Variáveis de ambiente necessárias:
    NUVEM_FISCAL_CLIENT_ID      — Client ID da aplicação na Nuvem Fiscal
    NUVEM_FISCAL_CLIENT_SECRET  — Client Secret (exibido apenas uma vez no console)

Ambiente (homologacao/producao) é configurado em Cadastros > Config. Fiscal.
"""

import os
import time
import logging
import requests
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

from db import execute_query, execute_insert, execute_update

# ============================================
# CONFIGURAÇÃO
# ============================================

NUVEM_FISCAL_CLIENT_ID = os.getenv("NUVEM_FISCAL_CLIENT_ID", "")
NUVEM_FISCAL_CLIENT_SECRET = os.getenv("NUVEM_FISCAL_CLIENT_SECRET", "")

_BASE_URLS = {
    "homologacao": "https://api.sandbox.nuvemfiscal.com.br",
    "producao":    "https://api.nuvemfiscal.com.br",
}

_AUTH_URL = "https://auth.nuvemfiscal.com.br/oauth/token"

# Cache de token em memória: persiste entre reruns do Streamlit no mesmo worker
_token_cache: Dict[str, Any] = {"token": None, "expires_at": 0.0}

# Mapa UF → código IBGE do estado (cUF)
_CUF_MAP = {
    "AC": "12", "AL": "27", "AP": "16", "AM": "13", "BA": "29",
    "CE": "23", "DF": "53", "ES": "32", "GO": "52", "MA": "21",
    "MT": "51", "MS": "50", "MG": "31", "PA": "15", "PB": "25",
    "PR": "41", "PE": "26", "PI": "22", "RJ": "33", "RN": "24",
    "RS": "43", "RO": "11", "RR": "14", "SC": "42", "SP": "35",
    "SE": "28", "TO": "17",
}


# ============================================
# CONFIG FISCAL (emitente)
# ============================================

def get_fiscal_config() -> Optional[Dict[str, Any]]:
    """Retorna a configuração fiscal da empresa (sempre 1 linha)."""
    rows = execute_query("SELECT * FROM fiscal_config ORDER BY id LIMIT 1")
    return rows[0] if rows else None


def save_fiscal_config(data: Dict[str, Any]) -> bool:
    """Insere ou atualiza a configuração fiscal do emitente."""
    existing = get_fiscal_config()
    if existing:
        execute_update("""
            UPDATE fiscal_config SET
                cnpj=%s, razao_social=%s, nome_fantasia=%s, ie=%s, crt=%s,
                logradouro=%s, numero=%s, complemento=%s, bairro=%s,
                municipio=%s, municipio_ibge=%s, uf=%s, cep=%s,
                telefone=%s, email=%s, ambiente=%s, updated_at=NOW()
            WHERE id=%s
        """, (
            data["cnpj"], data["razao_social"], data.get("nome_fantasia"),
            data.get("ie"), data["crt"],
            data["logradouro"], data["numero"], data.get("complemento"),
            data["bairro"], data["municipio"], data["municipio_ibge"],
            data["uf"], data["cep"],
            data.get("telefone"), data.get("email"), data["ambiente"],
            existing["id"],
        ))
    else:
        execute_insert("""
            INSERT INTO fiscal_config
                (cnpj, razao_social, nome_fantasia, ie, crt,
                 logradouro, numero, complemento, bairro,
                 municipio, municipio_ibge, uf, cep,
                 telefone, email, ambiente)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data["cnpj"], data["razao_social"], data.get("nome_fantasia"),
            data.get("ie"), data["crt"],
            data["logradouro"], data["numero"], data.get("complemento"),
            data["bairro"], data["municipio"], data["municipio_ibge"],
            data["uf"], data["cep"],
            data.get("telefone"), data.get("email"), data["ambiente"],
        ))
    return True


# ============================================
# AUTENTICAÇÃO OAuth2
# ============================================

def _get_access_token() -> str:
    """
    Retorna um token OAuth2 válido para a Nuvem Fiscal.
    Cacheia em memória e renova 60s antes de expirar.
    Raises RuntimeError se credenciais não estiverem configuradas.
    """
    global _token_cache
    now = time.time()

    if _token_cache["token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["token"]

    if not NUVEM_FISCAL_CLIENT_ID or not NUVEM_FISCAL_CLIENT_SECRET:
        raise RuntimeError(
            "NUVEM_FISCAL_CLIENT_ID e NUVEM_FISCAL_CLIENT_SECRET não configurados. "
            "Adicione nas variáveis de ambiente do Railway."
        )

    resp = requests.post(
        _AUTH_URL,
        data={
            "grant_type":    "client_credentials",
            "client_id":     NUVEM_FISCAL_CLIENT_ID,
            "client_secret": NUVEM_FISCAL_CLIENT_SECRET,
            "scope":         "nfe",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    resp.raise_for_status()
    token_data = resp.json()

    _token_cache["token"]      = token_data["access_token"]
    _token_cache["expires_at"] = now + int(token_data.get("expires_in", 3600))
    return _token_cache["token"]


def test_connection() -> Tuple[bool, str]:
    """Testa a conexão com a API da Nuvem Fiscal. Usado na UI de Config. Fiscal."""
    try:
        token = _get_access_token()
        return True, f"Conexão OK. Token obtido ({token[:8]}...)"
    except Exception as e:
        return False, f"Falha: {str(e)}"


# ============================================
# MONTAGEM DO PAYLOAD NF-e
# ============================================

def _digits(value: str) -> str:
    """Retorna apenas dígitos de uma string."""
    return "".join(c for c in (value or "") if c.isdigit())


def _build_nfe_payload(
    transaction: Dict[str, Any],
    config: Dict[str, Any],
    partner: Dict[str, Any],
    material: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Monta o payload JSON para emissão de NF-e via Nuvem Fiscal.
    Raises ValueError se campos obrigatórios estiverem faltando.
    """
    # --- Validações ---
    missing_emit = [f for f in ["cnpj", "razao_social", "crt", "logradouro",
                                 "numero", "bairro", "municipio", "municipio_ibge",
                                 "uf", "cep"] if not config.get(f)]
    if missing_emit:
        raise ValueError(f"Config. fiscal incompleta: {missing_emit}")

    missing_dest = [f for f in ["cnpj_cpf", "logradouro", "numero", "bairro",
                                  "municipio", "municipio_ibge", "uf", "cep"]
                    if not partner.get(f)]
    if missing_dest:
        raise ValueError(
            f"Dados fiscais do cliente '{partner.get('name', '?')}' incompletos: {missing_dest}. "
            "Configure em Cadastros > Parceiros."
        )

    missing_mat = [f for f in ["ncm", "cfop", "csosn"] if not material.get(f)]
    if missing_mat:
        raise ValueError(
            f"Dados fiscais do material '{material.get('name', '?')}' incompletos: {missing_mat}. "
            "Configure em Cadastros > Materiais."
        )

    # --- Documento do destinatário ---
    doc_clean = _digits(partner["cnpj_cpf"])
    dest_doc  = {"CNPJ": doc_clean} if len(doc_clean) == 14 else {"CPF": doc_clean}
    dest_ie   = partner.get("ie") or ""
    ind_ie    = "1" if (len(doc_clean) == 14 and dest_ie and dest_ie.upper() != "ISENTO") else "9"

    # --- Valores ---
    qtd        = Decimal(str(transaction["weight_kg"]))
    preco_unit = Decimal(str(transaction["price_per_kg"]))
    v_prod     = (qtd * preco_unit).quantize(Decimal("0.01"))

    # --- Datas ---
    now_str   = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
    saida_str = datetime.combine(
        transaction["date"], datetime.min.time()
    ).strftime("%Y-%m-%dT00:00:00-03:00")

    # --- ICMS: Simples Nacional (CRT 1/2) usa CSOSN; Regime Normal (CRT 3) usa CST ---
    crt    = config["crt"]
    csosn  = material["csosn"]
    if crt in ("1", "2"):
        icms_key   = f"ICMSSN{csosn}"
        icms_block = {"orig": "0", "CSOSN": csosn}
    else:
        icms_key   = f"ICMS{csosn.zfill(2)}"
        icms_block = {"orig": "0", "CST": csosn, "modBC": "3",
                      "vBC": "0.00", "pICMS": "0.00", "vICMS": "0.00"}

    # --- idDest: 1 intraestadual, 2 interestadual ---
    id_dest = "1" if config["uf"].upper() == (partner.get("uf") or "").upper() else "2"

    return {
        "ambiente": config["ambiente"],
        "idLote":   str(int(time.time() * 1000)),
        "indSinc":  1,  # síncrono — resposta imediata da SEFAZ
        "notas": [{
            "infNFe": {
                "versao": "4.00",
                "ide": {
                    "cUF":    _CUF_MAP.get(config["uf"].upper(), "35"),
                    "natOp":  "VENDA DE SUCATA",
                    "mod":    "55",
                    "serie":  "1",
                    "nNF":    "",        # Nuvem Fiscal atribui automaticamente
                    "dhEmi":  now_str,
                    "dhSaiEnt": saida_str,
                    "tpNF":   "1",       # saída
                    "idDest": id_dest,
                    "cMunFG": config["municipio_ibge"],
                    "tpImp":  "1",       # DANFE paisagem
                    "tpEmis": "1",       # emissão normal
                    "finNFe": "1",       # NF normal
                    "indFinal": "0",     # não consumidor final (B2B)
                    "indPres": "9",      # outros
                    "procEmi": "0",
                    "verProc": "1.0",
                },
                "emit": {
                    "CNPJ":   _digits(config["cnpj"]),
                    "xNome":  config["razao_social"],
                    "xFant":  config.get("nome_fantasia") or config["razao_social"],
                    "enderEmit": {
                        "xLgr":   config["logradouro"],
                        "nro":    config["numero"],
                        "xCpl":   config.get("complemento") or "",
                        "xBairro": config["bairro"],
                        "cMun":   config["municipio_ibge"],
                        "xMun":   config["municipio"],
                        "UF":     config["uf"].upper(),
                        "CEP":    _digits(config["cep"]),
                        "cPais":  "1058",
                        "xPais":  "Brasil",
                        "fone":   _digits(config.get("telefone") or ""),
                    },
                    "IE":  _digits(config.get("ie") or ""),
                    "CRT": crt,
                },
                "dest": {
                    **dest_doc,
                    "xNome": partner["name"],
                    "enderDest": {
                        "xLgr":   partner["logradouro"],
                        "nro":    partner["numero"],
                        "xCpl":   partner.get("complemento") or "",
                        "xBairro": partner["bairro"],
                        "cMun":   partner["municipio_ibge"],
                        "xMun":   partner["municipio"],
                        "UF":     partner["uf"].upper(),
                        "CEP":    _digits(partner["cep"]),
                        "cPais":  partner.get("pais") or "1058",
                        "xPais":  "Brasil",
                    },
                    "indIEDest": ind_ie,
                    "IE": dest_ie,
                },
                "det": [{
                    "nItem": "1",
                    "prod": {
                        "cProd":   material.get("sku") or str(material["id"]),
                        "cEAN":    "SEM GTIN",
                        "xProd":   material["name"].upper(),
                        "NCM":     _digits(material["ncm"]),
                        "CFOP":    material["cfop"],
                        "uCom":    material.get("unidade_fiscal") or "KG",
                        "qCom":    str(qtd),
                        "vUnCom":  str(preco_unit),
                        "vProd":   str(v_prod),
                        "cEANTrib": "SEM GTIN",
                        "uTrib":   material.get("unidade_fiscal") or "KG",
                        "qTrib":   str(qtd),
                        "vUnTrib": str(preco_unit),
                        "indTot":  "1",
                    },
                    "imposto": {
                        "ICMS": {icms_key: icms_block},
                        "PIS": {
                            "PISAliq": {   # CST 07 = isento (sucata)
                                "CST": "07", "vBC": "0.00",
                                "pPIS": "0.00", "vPIS": "0.00",
                            }
                        },
                        "COFINS": {
                            "COFINSAliq": {
                                "CST": "07", "vBC": "0.00",
                                "pCOFINS": "0.00", "vCOFINS": "0.00",
                            }
                        },
                    },
                }],
                "total": {
                    "ICMSTot": {
                        "vBC": "0.00",        "vICMS": "0.00",
                        "vICMSDeson": "0.00", "vFCP": "0.00",
                        "vBCST": "0.00",      "vST": "0.00",
                        "vFCPST": "0.00",     "vFCPSTRet": "0.00",
                        "vProd": str(v_prod), "vFrete": "0.00",
                        "vSeg": "0.00",       "vDesc": "0.00",
                        "vII": "0.00",        "vIPI": "0.00",
                        "vIPIDevol": "0.00",  "vPIS": "0.00",
                        "vCOFINS": "0.00",    "vOutro": "0.00",
                        "vNF": str(v_prod),
                    }
                },
                "transp": {"modFrete": "9"},  # sem frete
                "pag": {
                    "detPag": [{"tPag": "01", "vPag": str(v_prod)}]
                },
                "infAdic": {
                    "infCpl": (
                        f"Ref. transacao #{transaction['id']}"
                        + (f" | {transaction['notes']}" if transaction.get("notes") else "")
                    ).strip(" |"),
                },
            }
        }],
    }


# ============================================
# EMISSÃO
# ============================================

def emit_nfe(transaction_id: int) -> Tuple[bool, str, Optional[Dict]]:
    """
    Emite NF-e para uma transação de saída.
    Retorna (sucesso, mensagem, dict com nf_numero/nf_chave/nf_danfe_url/nf_xml_url).
    """
    rows = execute_query("""
        SELECT t.*,
               m.name AS material_name, m.sku, m.ncm, m.cfop, m.csosn,
               m.unidade_fiscal, m.id AS material_id,
               p.name AS partner_name, p.cnpj_cpf, p.ie,
               p.logradouro, p.numero, p.complemento, p.bairro,
               p.municipio, p.municipio_ibge, p.uf, p.cep, p.pais,
               p.id AS partner_id
        FROM transactions t
        JOIN materials m ON t.material_id = m.id
        LEFT JOIN partners p ON t.partner_id = p.id
        WHERE t.id = %s AND t.type = 'saida'
    """, (transaction_id,))

    if not rows:
        return False, "Transação não encontrada ou não é uma saída.", None

    tx = rows[0]

    if tx.get("nf_chave"):
        return False, f"NF-e já emitida (chave: {tx['nf_chave']}).", None

    if not tx.get("partner_id"):
        return False, "Saída de ajuste manual não pode ter NF-e. Vincule um cliente.", None

    config = get_fiscal_config()
    if not config:
        return False, "Configure os dados fiscais em Cadastros → Config. Fiscal.", None

    material = {
        "id": tx["material_id"], "name": tx["material_name"],
        "sku": tx.get("sku"), "ncm": tx.get("ncm"),
        "cfop": tx.get("cfop"), "csosn": tx.get("csosn"),
        "unidade_fiscal": tx.get("unidade_fiscal"),
    }
    partner = {
        "name": tx["partner_name"], "cnpj_cpf": tx.get("cnpj_cpf"),
        "ie": tx.get("ie"), "logradouro": tx.get("logradouro"),
        "numero": tx.get("numero"), "complemento": tx.get("complemento"),
        "bairro": tx.get("bairro"), "municipio": tx.get("municipio"),
        "municipio_ibge": tx.get("municipio_ibge"), "uf": tx.get("uf"),
        "cep": tx.get("cep"), "pais": tx.get("pais"),
    }

    try:
        payload = _build_nfe_payload(tx, config, partner, material)
    except ValueError as e:
        return False, str(e), None

    try:
        token = _get_access_token()
    except RuntimeError as e:
        return False, str(e), None

    base_url = _BASE_URLS.get(config["ambiente"], _BASE_URLS["homologacao"])
    headers  = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    execute_update(
        "UPDATE transactions SET nf_status='processando' WHERE id=%s",
        (transaction_id,)
    )

    try:
        resp = requests.post(f"{base_url}/nfe", json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.HTTPError as e:
        execute_update(
            "UPDATE transactions SET nf_status='erro' WHERE id=%s",
            (transaction_id,)
        )
        try:
            detail = e.response.json()
        except Exception:
            detail = str(e)
        logging.error(f"[NF-e] HTTP error tx {transaction_id}: {detail}")
        return False, f"Erro na API Nuvem Fiscal: {detail}", None
    except Exception as e:
        execute_update(
            "UPDATE transactions SET nf_status='erro' WHERE id=%s",
            (transaction_id,)
        )
        return False, f"Erro de comunicação: {str(e)}", None

    # Nuvem Fiscal retorna lista 'notas' no lote síncrono
    nota    = (data.get("notas") or [{}])[0]
    c_stat  = str(nota.get("cStat", ""))
    autorizada = c_stat in ("100", "150")

    nf_status = "autorizada" if autorizada else "erro"
    nf_chave  = nota.get("chNFe") or nota.get("chave")
    nf_numero = nota.get("nNF")

    danfe_url = xml_url = None
    if autorizada and nf_chave:
        danfe_url = f"{base_url}/nfe/{nf_chave}/pdf"
        xml_url   = f"{base_url}/nfe/{nf_chave}/xml"

    execute_update("""
        UPDATE transactions SET
            nf_numero=%s, nf_chave=%s, nf_status=%s,
            nf_danfe_url=%s, nf_xml_url=%s, nf_emitida_em=NOW()
        WHERE id=%s
    """, (nf_numero, nf_chave, nf_status, danfe_url, xml_url, transaction_id))

    if autorizada:
        return True, f"NF-e autorizada! Número: {nf_numero}", {
            "nf_numero": nf_numero, "nf_chave": nf_chave,
            "nf_status": nf_status, "nf_danfe_url": danfe_url, "nf_xml_url": xml_url,
        }
    else:
        motivo = nota.get("xMotivo", "sem detalhe")
        return False, f"NF-e rejeitada (cStat {c_stat}): {motivo}", None


# ============================================
# DOWNLOAD (autenticado — DANFE/XML)
# ============================================

def download_nfe_file(nf_chave: str, file_type: str = "pdf") -> Tuple[bool, bytes, str]:
    """
    Baixa DANFE (PDF) ou XML da NF-e autenticado via Nuvem Fiscal.
    Retorna (sucesso, bytes_conteúdo, filename_ou_erro).
    """
    config = get_fiscal_config()
    if not config:
        return False, b"", "Config. fiscal não encontrada."

    try:
        token = _get_access_token()
    except RuntimeError as e:
        return False, b"", f"Erro de autenticação: {str(e)}"

    base_url = _BASE_URLS.get(config["ambiente"], _BASE_URLS["homologacao"])
    url      = f"{base_url}/nfe/{nf_chave}/{file_type}"

    try:
        resp = requests.get(
            url, headers={"Authorization": f"Bearer {token}"}, timeout=20
        )
        resp.raise_for_status()
        ext = "pdf" if file_type == "pdf" else "xml"
        filename = f"nfe_{nf_chave}.{ext}"
        return True, resp.content, filename
    except Exception as e:
        logging.error(f"[NF-e] Download {file_type} {nf_chave}: {e}")
        return False, b"", f"Erro ao baixar {file_type.upper()}: {str(e)}"


# ============================================
# CONSULTA E CANCELAMENTO
# ============================================

def get_nfe_status(transaction_id: int) -> Tuple[bool, str]:
    """Consulta o status atual da NF-e na Nuvem Fiscal e atualiza o banco."""
    rows = execute_query(
        "SELECT nf_chave, nf_status FROM transactions WHERE id=%s", (transaction_id,)
    )
    if not rows or not rows[0].get("nf_chave"):
        return False, "NF-e não emitida para esta transação."

    config = get_fiscal_config()
    if not config:
        return False, "Config. fiscal não encontrada."

    try:
        token = _get_access_token()
    except RuntimeError as e:
        return False, str(e)

    base_url = _BASE_URLS.get(config["ambiente"], _BASE_URLS["homologacao"])
    nf_chave = rows[0]["nf_chave"]

    try:
        resp = requests.get(
            f"{base_url}/nfe/{nf_chave}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return False, f"Erro ao consultar: {str(e)}"

    status_map = {
        "autorizada":  "autorizada",
        "cancelada":   "cancelada",
        "denegada":    "denegada",
        "processando": "processando",
    }
    api_status = data.get("status", "").lower()
    new_status = status_map.get(api_status, rows[0]["nf_status"])

    execute_update(
        "UPDATE transactions SET nf_status=%s WHERE id=%s", (new_status, transaction_id)
    )
    return True, f"Status: {new_status}"


def cancel_nfe(transaction_id: int, justificativa: str) -> Tuple[bool, str]:
    """
    Cancela uma NF-e autorizada.
    A justificativa deve ter entre 15 e 255 caracteres (exigência da SEFAZ).
    """
    if len(justificativa.strip()) < 15:
        return False, "Justificativa deve ter no mínimo 15 caracteres."

    rows = execute_query(
        "SELECT nf_chave, nf_status FROM transactions WHERE id=%s", (transaction_id,)
    )
    if not rows:
        return False, "Transação não encontrada."

    tx = rows[0]
    if tx.get("nf_status") != "autorizada":
        return False, f"Apenas NF-e autorizadas podem ser canceladas (status atual: {tx.get('nf_status')})."

    config = get_fiscal_config()
    if not config:
        return False, "Config. fiscal não encontrada."

    try:
        token = _get_access_token()
    except RuntimeError as e:
        return False, str(e)

    base_url = _BASE_URLS.get(config["ambiente"], _BASE_URLS["homologacao"])
    headers  = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        resp = requests.post(
            f"{base_url}/nfe/{tx['nf_chave']}/cancelamento",
            json={"justificativa": justificativa.strip()},
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
    except requests.HTTPError as e:
        try:
            detail = e.response.json()
        except Exception:
            detail = str(e)
        return False, f"Erro ao cancelar: {detail}"
    except Exception as e:
        return False, f"Erro de comunicação: {str(e)}"

    execute_update(
        "UPDATE transactions SET nf_status='cancelada' WHERE id=%s", (transaction_id,)
    )
    return True, "NF-e cancelada com sucesso."
