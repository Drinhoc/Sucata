"""
Módulo de serviços e lógica de negócio
Contém todas as operações relacionadas a materiais, parceiros e transações
"""

import json
import random
import string
import bcrypt as _bcrypt
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from db import execute_query, execute_insert, execute_update, execute_in_transaction


# ============================================
# AUTENTICAÇÃO E USUÁRIOS
# ============================================

def seed_initial_data():
    """Cria o usuário admin padrão se não houver nenhum usuário cadastrado"""
    existing = execute_query("SELECT id FROM users LIMIT 1")
    if not existing:
        password_hash = _bcrypt.hashpw(b"admin", _bcrypt.gensalt()).decode()
        execute_insert(
            "INSERT INTO users (username, name, password_hash, role) VALUES (%s, %s, %s, %s)",
            ("admin", "Administrador", password_hash, "admin")
        )


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Autentica um usuário pelo username e senha. Retorna o dict do usuário ou None."""
    rows = execute_query(
        "SELECT * FROM users WHERE username = %s AND active = 1",
        (username.strip().lower(),)
    )
    if not rows:
        return None
    user = rows[0]
    if _bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
        execute_update("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
        return user
    return None


def get_all_users() -> List[Dict[str, Any]]:
    """Retorna todos os usuários cadastrados (sem o hash de senha)"""
    return execute_query(
        "SELECT id, username, name, role, active, created_at, last_login "
        "FROM users ORDER BY name"
    )


def create_user(username: str, name: str, password: str, role: str) -> Tuple[bool, str]:
    """Cria um novo usuário"""
    try:
        password_hash = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
        execute_insert(
            "INSERT INTO users (username, name, password_hash, role) VALUES (%s, %s, %s, %s)",
            (username.strip().lower(), name.strip(), password_hash, role)
        )
        return True, "Usuário criado com sucesso!"
    except Exception as e:
        return False, f"Erro ao criar usuário: {str(e)}"


def update_user(user_id: int, name: str, role: str, active: int) -> bool:
    """Atualiza nome, perfil e status de um usuário"""
    rows = execute_update(
        "UPDATE users SET name = %s, role = %s, active = %s WHERE id = %s",
        (name.strip(), role, active, user_id)
    )
    return rows > 0


def reset_user_password(user_id: int, new_password: str) -> bool:
    """Redefine a senha de um usuário"""
    password_hash = _bcrypt.hashpw(new_password.encode(), _bcrypt.gensalt()).decode()
    rows = execute_update(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (password_hash, user_id)
    )
    return rows > 0


# ============================================
# AUDIT LOG
# ============================================

def log_action(
    user_id: int,
    username: str,
    action: str,
    entity: str,
    entity_id: Optional[int] = None,
    details: Optional[dict] = None
) -> None:
    """
    Registra uma ação no log de auditoria.
    Nunca lança exceções — falhas de log não devem interromper operações.
    """
    try:
        execute_insert(
            """INSERT INTO audit_logs (user_id, username, action, entity, entity_id, details)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (user_id, username, action, entity, entity_id,
             json.dumps(details or {}, ensure_ascii=False))
        )
    except Exception:
        pass


def get_audit_logs(
    start_date: Optional[date] = None,
    user_id_filter: Optional[int] = None,
    action_filter: Optional[str] = None,
    entity_filter: Optional[str] = None,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """Retorna logs de auditoria com filtros opcionais"""
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []

    if start_date:
        query += " AND created_at >= %s"
        params.append(start_date)

    if user_id_filter:
        query += " AND user_id = %s"
        params.append(user_id_filter)

    if action_filter:
        query += " AND action = %s"
        params.append(action_filter)

    if entity_filter:
        query += " AND entity = %s"
        params.append(entity_filter)

    query += f" ORDER BY created_at DESC LIMIT {limit}"

    return execute_query(query, tuple(params))


# ============================================
# MATERIAIS
# ============================================

def get_all_materials(active_only: bool = True) -> List[Dict[str, Any]]:
    """Retorna todos os materiais cadastrados"""
    if active_only:
        query = "SELECT * FROM materials WHERE active = 1 ORDER BY name"
    else:
        query = "SELECT * FROM materials ORDER BY name"
    return execute_query(query)


def get_material_by_id(material_id: int) -> Optional[Dict[str, Any]]:
    """Retorna um material específico pelo ID"""
    query = "SELECT * FROM materials WHERE id = %s"
    results = execute_query(query, (material_id,))
    return results[0] if results else None


def create_material(name: str, unit: str = "kg") -> int:
    """Cria um novo material"""
    query = """
        INSERT INTO materials (name, unit, active)
        VALUES (%s, %s, 1)
    """
    return execute_insert(query, (name.strip(), unit.strip()))


def update_material(material_id: int, name: str, unit: str) -> bool:
    """Atualiza um material existente"""
    query = """
        UPDATE materials
        SET name = %s, unit = %s
        WHERE id = %s
    """
    rows_affected = execute_update(query, (name.strip(), unit.strip(), material_id))
    return rows_affected > 0


def deactivate_material(material_id: int) -> bool:
    """Desativa um material (soft delete)"""
    query = "UPDATE materials SET active = 0 WHERE id = %s"
    rows_affected = execute_update(query, (material_id,))
    return rows_affected > 0


def activate_material(material_id: int) -> bool:
    """Reativa um material"""
    query = "UPDATE materials SET active = 1 WHERE id = %s"
    rows_affected = execute_update(query, (material_id,))
    return rows_affected > 0


# ============================================
# PARCEIROS
# ============================================

def get_all_partners(active_only: bool = True, partner_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna todos os parceiros cadastrados"""
    query = "SELECT * FROM partners WHERE 1=1"
    params = []

    if active_only:
        query += " AND active = 1"

    if partner_type:
        query += " AND (type = %s OR type = 'ambos')"
        params.append(partner_type)

    query += " ORDER BY name"

    return execute_query(query, tuple(params))


def get_partner_by_id(partner_id: int) -> Optional[Dict[str, Any]]:
    """Retorna um parceiro específico pelo ID"""
    query = "SELECT * FROM partners WHERE id = %s"
    results = execute_query(query, (partner_id,))
    return results[0] if results else None


def create_partner(name: str, partner_type: str, phone: str = "") -> int:
    """Cria um novo parceiro"""
    query = """
        INSERT INTO partners (name, type, phone, active)
        VALUES (%s, %s, %s, 1)
    """
    return execute_insert(query, (name.strip(), partner_type, phone.strip()))


def update_partner(partner_id: int, name: str, partner_type: str, phone: str) -> bool:
    """Atualiza um parceiro existente"""
    query = """
        UPDATE partners
        SET name = %s, type = %s, phone = %s
        WHERE id = %s
    """
    rows_affected = execute_update(query, (name.strip(), partner_type, phone.strip(), partner_id))
    return rows_affected > 0


def deactivate_partner(partner_id: int) -> bool:
    """Desativa um parceiro (soft delete)"""
    query = "UPDATE partners SET active = 0 WHERE id = %s"
    rows_affected = execute_update(query, (partner_id,))
    return rows_affected > 0


def activate_partner(partner_id: int) -> bool:
    """Reativa um parceiro"""
    query = "UPDATE partners SET active = 1 WHERE id = %s"
    rows_affected = execute_update(query, (partner_id,))
    return rows_affected > 0


# ============================================
# TRANSAÇÕES
# ============================================

def get_current_stock(material_id: int) -> float:
    """Calcula o estoque atual de um material (entradas - saídas)"""
    query = """
        SELECT
            COALESCE(SUM(CASE WHEN type = 'entrada' THEN weight_kg ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN type = 'saida' THEN weight_kg ELSE 0 END), 0) as stock
        FROM transactions
        WHERE material_id = %s
    """
    result = execute_query(query, (material_id,))
    return result[0]['stock'] if result else 0.0


def get_all_stock() -> List[Dict[str, Any]]:
    """Retorna o estoque atual de todos os materiais ativos com informações adicionais"""
    query = """
        SELECT
            m.id,
            m.name,
            m.unit,
            COALESCE(SUM(CASE WHEN t.type = 'entrada' THEN t.weight_kg ELSE 0 END), 0) as total_in,
            COALESCE(SUM(CASE WHEN t.type = 'saida' THEN t.weight_kg ELSE 0 END), 0) as total_out,
            COALESCE(SUM(CASE WHEN t.type = 'entrada' THEN t.weight_kg ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN t.type = 'saida' THEN t.weight_kg ELSE 0 END), 0) as current_stock,
            COALESCE(AVG(CASE WHEN t.type = 'entrada' THEN t.price_per_kg END), 0) as avg_buy_price,
            COALESCE(AVG(CASE WHEN t.type = 'saida' THEN t.price_per_kg END), 0) as avg_sell_price
        FROM materials m
        LEFT JOIN transactions t ON m.id = t.material_id
        WHERE m.active = 1
        GROUP BY m.id, m.name, m.unit
        ORDER BY m.name
    """
    return execute_query(query)


def create_transaction(
    transaction_date: date,
    transaction_type: str,
    material_id: int,
    partner_id: int,
    weight_kg: float,
    price_per_kg: float,
    notes: str = "",
    role: str = "admin"
) -> Tuple[bool, str, Optional[int]]:
    """Cria uma nova transação (entrada ou saída).

    O parâmetro `role` aplica controle de permissão na camada de serviço:
    operadores NÃO podem criar saídas normais (apenas via process_internal).
    """
    # T3 — Permissão por role
    if transaction_type == "saida" and role != "admin":
        return False, "Sem permissão para registrar saídas. Contacte um administrador.", None

    if transaction_type not in ['entrada', 'saida']:
        return False, "Tipo de transação inválido", None

    if weight_kg <= 0:
        return False, "O peso deve ser maior que zero", None

    if price_per_kg < 0:
        return False, "O preço não pode ser negativo", None

    if transaction_type == 'saida':
        current_stock = get_current_stock(material_id)
        if weight_kg > current_stock:
            return False, f"Estoque insuficiente. Disponível: {current_stock:.2f} kg", None

    total_value = weight_kg * price_per_kg

    query = """
        INSERT INTO transactions
        (date, type, material_id, partner_id, weight_kg, price_per_kg, total_value, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    transaction_id = execute_insert(
        query,
        (transaction_date, transaction_type, material_id, partner_id,
         weight_kg, price_per_kg, total_value, notes.strip())
    )

    return True, "Transação registrada com sucesso", transaction_id


def get_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    transaction_type: Optional[str] = None,
    material_id: Optional[int] = None,
    partner_id: Optional[int] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Retorna transações com filtros opcionais"""
    query = """
        SELECT
            t.*,
            m.name as material_name,
            m.unit as material_unit,
            p.name as partner_name,
            p.type as partner_type
        FROM transactions t
        JOIN materials m ON t.material_id = m.id
        JOIN partners p ON t.partner_id = p.id
        WHERE 1=1
    """
    params = []

    if start_date:
        query += " AND t.date >= %s"
        params.append(start_date)

    if end_date:
        query += " AND t.date <= %s"
        params.append(end_date)

    if transaction_type:
        query += " AND t.type = %s"
        params.append(transaction_type)

    if material_id:
        query += " AND t.material_id = %s"
        params.append(material_id)

    if partner_id:
        query += " AND t.partner_id = %s"
        params.append(partner_id)

    query += " ORDER BY t.date DESC, t.created_at DESC"

    if limit:
        query += f" LIMIT {limit}"

    return execute_query(query, tuple(params))


def delete_transaction(transaction_id: int) -> bool:
    """Deleta uma transação"""
    query = "DELETE FROM transactions WHERE id = %s"
    rows_affected = execute_update(query, (transaction_id,))
    return rows_affected > 0


# ============================================
# RELATÓRIOS E MÉTRICAS
# ============================================

def get_monthly_metrics(year: int, month: int) -> Dict[str, float]:
    """Retorna métricas do mês (compras, vendas, lucro bruto)"""
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    query = """
        SELECT
            COALESCE(SUM(CASE WHEN type = 'entrada' THEN total_value END), 0) as total_purchases,
            COALESCE(SUM(CASE WHEN type = 'saida' THEN total_value END), 0) as total_sales,
            COALESCE(SUM(CASE WHEN type = 'entrada' THEN weight_kg END), 0) as weight_in,
            COALESCE(SUM(CASE WHEN type = 'saida' THEN weight_kg END), 0) as weight_out
        FROM transactions
        WHERE date >= %s AND date < %s
    """
    result = execute_query(query, (start_date, end_date))

    if result:
        data = result[0]
        return {
            'total_purchases': data['total_purchases'],
            'total_sales': data['total_sales'],
            'gross_profit': data['total_sales'] - data['total_purchases'],
            'weight_in': data['weight_in'],
            'weight_out': data['weight_out']
        }

    return {
        'total_purchases': 0.0,
        'total_sales': 0.0,
        'gross_profit': 0.0,
        'weight_in': 0.0,
        'weight_out': 0.0
    }


def get_stock_value_estimate() -> float:
    """Calcula uma estimativa do valor total em estoque baseado no preço médio de compra"""
    query = """
        SELECT
            SUM(stock * avg_price) as total_value
        FROM (
            SELECT
                m.id,
                COALESCE(SUM(CASE WHEN t.type = 'entrada' THEN t.weight_kg ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN t.type = 'saida' THEN t.weight_kg ELSE 0 END), 0) as stock,
                COALESCE(AVG(CASE WHEN t.type = 'entrada' THEN t.price_per_kg END), 0) as avg_price
            FROM materials m
            LEFT JOIN transactions t ON m.id = t.material_id
            WHERE m.active = 1
            GROUP BY m.id
        ) AS stock_calc
    """
    result = execute_query(query)
    return result[0]['total_value'] if result and result[0]['total_value'] else 0.0


# ============================================
# PREÇOS VIGENTES
# ============================================

def get_current_prices() -> List[Dict[str, Any]]:
    """Retorna todos os materiais ativos com seus preços vigentes"""
    query = """
        SELECT
            m.id,
            m.name,
            m.unit,
            COALESCE(p.price_per_kg, 0) as price_per_kg,
            p.updated_at
        FROM materials m
        LEFT JOIN prices p ON m.id = p.material_id
        WHERE m.active = 1
        ORDER BY m.name
    """
    return execute_query(query)


def get_price_for_material(material_id: int) -> float:
    """Retorna o preço vigente por kg de um material"""
    result = execute_query(
        "SELECT price_per_kg FROM prices WHERE material_id = %s", (material_id,)
    )
    return result[0]['price_per_kg'] if result else 0.0


def update_price(material_id: int, price_per_kg: float, role: str = "admin") -> bool:
    """Cria ou atualiza o preço vigente de um material.
    Apenas administradores podem alterar preços.
    """
    if role != "admin":
        return False

    existing = execute_query(
        "SELECT id FROM prices WHERE material_id = %s", (material_id,)
    )
    if existing:
        execute_update(
            "UPDATE prices SET price_per_kg = %s, updated_at = NOW() WHERE material_id = %s",
            (price_per_kg, material_id)
        )
    else:
        execute_insert(
            "INSERT INTO prices (material_id, price_per_kg) VALUES (%s, %s)",
            (material_id, price_per_kg)
        )
    return True


# ============================================
# T4 — PROCESSAMENTO INTERNO
# ============================================

_INTERNAL_PARTNER_NAME = "PROCESSAMENTO / PRENSA (INTERNO)"


def ensure_internal_partner() -> int:
    """Retorna o ID do parceiro interno de processamento, criando-o se necessário."""
    existing = execute_query(
        "SELECT id FROM partners WHERE name = %s LIMIT 1",
        (_INTERNAL_PARTNER_NAME,)
    )
    if existing:
        return existing[0]["id"]
    return execute_insert(
        "INSERT INTO partners (name, type, phone, active) VALUES (%s, 'ambos', '', 1)",
        (_INTERNAL_PARTNER_NAME,)
    )


def _generate_proc_code() -> str:
    """Gera um código único de processamento: PROC#YYYYMMDDHHMMSS-XXXX"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"PROC#{timestamp}-{suffix}"


def process_internal(
    material_from_id: int,
    material_to_id: int,
    weight_kg: float,
    user_id: int,
    username: str,
) -> Tuple[bool, str, str]:
    """
    Realiza um processamento interno: converte peso de um material em outro.

    Cria atomicamente:
      - 1 transação SAÍDA do material de origem (preço 0, valor 0)
      - 1 transação ENTRADA no material de destino (preço 0, valor 0)

    Ambas vinculadas ao mesmo código PROC# e ao parceiro interno fixo.
    Acessível a admins e operadores.

    Retorna (success, message, proc_code).
    """
    if material_from_id == material_to_id:
        return False, "Material de origem e destino devem ser diferentes.", ""

    if weight_kg <= 0:
        return False, "O peso deve ser maior que zero.", ""

    stock = get_current_stock(material_from_id)
    if weight_kg > stock:
        return False, f"Estoque insuficiente. Disponível: {stock:.2f} kg.", ""

    partner_id = ensure_internal_partner()
    proc_code = _generate_proc_code()
    today = date.today()

    saida_q = (
        """INSERT INTO transactions
               (date, type, material_id, partner_id, weight_kg, price_per_kg, total_value, notes)
           VALUES (%s, 'saida', %s, %s, %s, 0, 0, %s)""",
        (today, material_from_id, partner_id, weight_kg, proc_code),
    )
    entrada_q = (
        """INSERT INTO transactions
               (date, type, material_id, partner_id, weight_kg, price_per_kg, total_value, notes)
           VALUES (%s, 'entrada', %s, %s, %s, 0, 0, %s)""",
        (today, material_to_id, partner_id, weight_kg, proc_code),
    )

    try:
        ids = execute_in_transaction([saida_q, entrada_q])
        log_action(
            user_id, username, "CREATE", "processamento", ids[0],
            {
                "proc_code": proc_code,
                "material_from_id": material_from_id,
                "material_to_id": material_to_id,
                "peso_kg": weight_kg,
            },
        )
        return True, "Processamento concluído com sucesso!", proc_code
    except Exception as e:
        return False, f"Erro no processamento: {str(e)}", ""


# ============================================
# CANHOTOS
# ============================================

def _get_next_canhoto_number() -> str:
    """Gera o próximo número sequencial de canhoto (ex: 0001, 0047)"""
    result = execute_query("SELECT COUNT(*) as total FROM canhotos")
    next_num = (result[0]['total'] if result else 0) + 1
    return f"{next_num:04d}"


def create_canhoto(
    items: List[Dict[str, Any]],
    client_name: str = "",
    partner_id: Optional[int] = None
) -> int:
    """Cria um novo canhoto pendente com os itens fornecidos"""
    number = _get_next_canhoto_number()
    total_value = sum(item['total_value'] for item in items)
    today = date.today()

    canhoto_id = execute_insert(
        """
        INSERT INTO canhotos (number, date, client_name, partner_id, status, total_value)
        VALUES (%s, %s, %s, %s, 'pendente', %s)
        """,
        (number, today, client_name.strip() or None, partner_id, total_value)
    )

    for item in items:
        execute_insert(
            """
            INSERT INTO canhoto_items (canhoto_id, material_id, weight_kg, price_per_kg, total_value)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (canhoto_id, item['material_id'], item['weight_kg'],
             item['price_per_kg'], item['total_value'])
        )

    return canhoto_id


def get_canhotos(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna canhotos com filtro opcional de status"""
    query = """
        SELECT
            c.id,
            c.number,
            c.date,
            c.client_name,
            c.partner_id,
            c.status,
            c.total_value,
            c.created_at,
            COUNT(ci.id) as items_count
        FROM canhotos c
        LEFT JOIN canhoto_items ci ON c.id = ci.canhoto_id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND c.status = %s"
        params.append(status)

    query += """
        GROUP BY c.id, c.number, c.date, c.client_name, c.partner_id,
                 c.status, c.total_value, c.created_at
        ORDER BY c.created_at DESC
    """
    return execute_query(query, tuple(params))


def get_canhoto_with_items(canhoto_id: int) -> Optional[Dict[str, Any]]:
    """Retorna um canhoto com todos os seus itens"""
    canhoto = execute_query("SELECT * FROM canhotos WHERE id = %s", (canhoto_id,))
    if not canhoto:
        return None

    items = execute_query(
        """
        SELECT ci.*, m.name as material_name, m.unit as material_unit
        FROM canhoto_items ci
        JOIN materials m ON ci.material_id = m.id
        WHERE ci.canhoto_id = %s
        ORDER BY ci.id
        """,
        (canhoto_id,)
    )

    result = dict(canhoto[0])
    result['items'] = items
    return result


def confirm_canhoto(canhoto_id: int) -> Tuple[bool, str]:
    """Confirma o pagamento de um canhoto e registra as transações de entrada"""
    canhoto = get_canhoto_with_items(canhoto_id)
    if not canhoto:
        return False, "Canhoto não encontrado"
    if canhoto['status'] != 'pendente':
        return False, f"Canhoto já está {canhoto['status']}"

    partner_id = canhoto['partner_id']
    if not partner_id:
        existing = execute_query(
            "SELECT id FROM partners WHERE name = 'Cliente Avulso' LIMIT 1"
        )
        if existing:
            partner_id = existing[0]['id']
        else:
            partner_id = execute_insert(
                "INSERT INTO partners (name, type, phone, active) VALUES ('Cliente Avulso', 'fornecedor', '', 1)",
                ()
            )

    today = date.today()
    notes_base = f"Canhoto #{canhoto['number']}"
    if canhoto['client_name']:
        notes_base += f" — {canhoto['client_name']}"

    for item in canhoto['items']:
        execute_insert(
            """
            INSERT INTO transactions
                (date, type, material_id, partner_id, weight_kg, price_per_kg, total_value, notes)
            VALUES (%s, 'entrada', %s, %s, %s, %s, %s, %s)
            """,
            (today, item['material_id'], partner_id,
             item['weight_kg'], item['price_per_kg'], item['total_value'], notes_base)
        )

    execute_update(
        "UPDATE canhotos SET status = 'confirmado' WHERE id = %s", (canhoto_id,)
    )
    return True, "Pagamento confirmado e transações registradas!"


def cancel_canhoto(canhoto_id: int) -> bool:
    """Cancela um canhoto pendente"""
    rows = execute_update(
        "UPDATE canhotos SET status = 'cancelado' WHERE id = %s", (canhoto_id,)
    )
    return rows > 0


def get_material_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """Retorna resumo por material com entradas, saídas e lucro"""
    query = """
        SELECT
            m.name as material,
            COALESCE(SUM(CASE WHEN t.type = 'entrada' THEN t.weight_kg END), 0) as weight_in,
            COALESCE(SUM(CASE WHEN t.type = 'saida' THEN t.weight_kg END), 0) as weight_out,
            COALESCE(SUM(CASE WHEN t.type = 'entrada' THEN t.total_value END), 0) as value_in,
            COALESCE(SUM(CASE WHEN t.type = 'saida' THEN t.total_value END), 0) as value_out,
            COALESCE(SUM(CASE WHEN t.type = 'saida' THEN t.total_value END), 0) -
            COALESCE(SUM(CASE WHEN t.type = 'entrada' THEN t.total_value END), 0) as profit
        FROM materials m
        LEFT JOIN transactions t ON m.id = t.material_id
        WHERE m.active = 1
    """
    params = []

    if start_date:
        query += " AND t.date >= %s"
        params.append(start_date)

    if end_date:
        query += " AND t.date <= %s"
        params.append(end_date)

    query += """
        GROUP BY m.id, m.name
        HAVING (
            COALESCE(SUM(CASE WHEN t.type = 'entrada' THEN t.weight_kg END), 0) > 0
            OR COALESCE(SUM(CASE WHEN t.type = 'saida' THEN t.weight_kg END), 0) > 0
        )
        ORDER BY profit DESC
    """

    return execute_query(query, tuple(params))


def get_period_comparison(start_date: date, end_date: date) -> Dict[str, Any]:
    """Retorna métricas do período atual e do período anterior para comparação"""
    delta = end_date - start_date
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - delta

    query = """
        SELECT
            COALESCE(SUM(CASE WHEN type = 'entrada' THEN total_value END), 0) as compras,
            COALESCE(SUM(CASE WHEN type = 'saida' THEN total_value END), 0) as vendas,
            COALESCE(SUM(CASE WHEN type = 'entrada' THEN weight_kg END), 0) as peso_in,
            COALESCE(SUM(CASE WHEN type = 'saida' THEN weight_kg END), 0) as peso_out,
            COUNT(*) as transacoes
        FROM transactions
        WHERE date >= %s AND date <= %s
    """

    def parse(rows):
        r = rows[0] if rows else {}
        compras = r.get('compras', 0) or 0
        vendas = r.get('vendas', 0) or 0
        transacoes = r.get('transacoes', 0) or 0
        return {
            'compras': compras,
            'vendas': vendas,
            'peso_in': r.get('peso_in', 0) or 0,
            'peso_out': r.get('peso_out', 0) or 0,
            'transacoes': transacoes,
            'lucro': vendas - compras,
            'margem_pct': (vendas - compras) / vendas * 100 if vendas > 0 else 0,
            'ticket_medio': compras / transacoes if transacoes > 0 else 0,
        }

    current = parse(execute_query(query, (start_date, end_date)))
    previous = parse(execute_query(query, (prev_start, prev_end)))
    current['anterior'] = previous
    current['prev_start'] = prev_start
    current['prev_end'] = prev_end
    return current


def get_temporal_evolution(
    start_date: date,
    end_date: date,
    granularity: str = 'month'
) -> List[Dict[str, Any]]:
    """Retorna evolução temporal das transações agrupada por dia, semana ou mês"""
    fmt_map = {
        'day': 'YYYY-MM-DD',
        'week': 'IYYY-"W"IW',
        'month': 'YYYY-MM'
    }
    fmt = fmt_map.get(granularity, 'YYYY-MM')

    query = f"""
        SELECT
            TO_CHAR(date, '{fmt}') as periodo,
            COALESCE(SUM(CASE WHEN type = 'entrada' THEN total_value END), 0) as compras,
            COALESCE(SUM(CASE WHEN type = 'saida' THEN total_value END), 0) as vendas,
            COALESCE(SUM(CASE WHEN type = 'entrada' THEN weight_kg END), 0) as peso_comprado,
            COALESCE(SUM(CASE WHEN type = 'saida' THEN weight_kg END), 0) as peso_vendido,
            COUNT(*) as transacoes
        FROM transactions
        WHERE date >= %s AND date <= %s
        GROUP BY periodo
        ORDER BY periodo
    """
    rows = execute_query(query, (start_date, end_date))
    for r in rows:
        r['lucro'] = r['vendas'] - r['compras']
    return rows


def get_material_analysis(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """Retorna análise detalhada por material com preços médios e margens"""
    date_cond = ""
    params: list = []
    if start_date:
        date_cond += " AND t.date >= %s"
        params.append(start_date)
    if end_date:
        date_cond += " AND t.date <= %s"
        params.append(end_date)

    query = f"""
        SELECT
            m.name as material,
            COUNT(CASE WHEN t.type = 'entrada' THEN 1 END) as qtd_entradas,
            COUNT(CASE WHEN t.type = 'saida' THEN 1 END) as qtd_saidas,
            COALESCE(SUM(CASE WHEN t.type = 'entrada' THEN t.weight_kg END), 0) as peso_comprado,
            COALESCE(SUM(CASE WHEN t.type = 'saida' THEN t.weight_kg END), 0) as peso_vendido,
            COALESCE(SUM(CASE WHEN t.type = 'entrada' THEN t.total_value END), 0) as valor_compras,
            COALESCE(SUM(CASE WHEN t.type = 'saida' THEN t.total_value END), 0) as valor_vendas,
            COALESCE(AVG(CASE WHEN t.type = 'entrada' THEN t.price_per_kg END), 0) as preco_medio_compra,
            COALESCE(AVG(CASE WHEN t.type = 'saida' THEN t.price_per_kg END), 0) as preco_medio_venda
        FROM materials m
        LEFT JOIN transactions t ON m.id = t.material_id{date_cond}
        WHERE m.active = 1
        GROUP BY m.id, m.name
        HAVING (
            COALESCE(SUM(CASE WHEN t.type = 'entrada' THEN t.weight_kg END), 0) > 0
            OR COALESCE(SUM(CASE WHEN t.type = 'saida' THEN t.weight_kg END), 0) > 0
        )
        ORDER BY valor_compras DESC
    """
    results = execute_query(query, tuple(params))
    for r in results:
        r['lucro'] = r['valor_vendas'] - r['valor_compras']
        r['margem_pct'] = (r['lucro'] / r['valor_vendas'] * 100) if r['valor_vendas'] > 0 else 0
        r['spread_kg'] = (
            r['preco_medio_venda'] - r['preco_medio_compra']
            if r['preco_medio_venda'] > 0 and r['preco_medio_compra'] > 0
            else 0
        )
    return results


def get_partner_analysis(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """Retorna análise por parceiro com totais de compras, vendas e volume no período"""
    date_cond = ""
    params: list = []
    if start_date:
        date_cond += " AND t.date >= %s"
        params.append(start_date)
    if end_date:
        date_cond += " AND t.date <= %s"
        params.append(end_date)

    query = f"""
        SELECT
            p.id,
            p.name as parceiro,
            p.type as tipo,
            p.phone as telefone,
            COUNT(CASE WHEN t.type = 'entrada' THEN 1 END) as qtd_entradas,
            COUNT(CASE WHEN t.type = 'saida' THEN 1 END) as qtd_saidas,
            COALESCE(SUM(CASE WHEN t.type = 'entrada' THEN t.weight_kg END), 0) as peso_fornecido,
            COALESCE(SUM(CASE WHEN t.type = 'saida' THEN t.weight_kg END), 0) as peso_vendido,
            COALESCE(SUM(CASE WHEN t.type = 'entrada' THEN t.total_value END), 0) as valor_pago,
            COALESCE(SUM(CASE WHEN t.type = 'saida' THEN t.total_value END), 0) as valor_recebido,
            MAX(t.date) as ultima_transacao
        FROM partners p
        LEFT JOIN transactions t ON p.id = t.partner_id{date_cond}
        WHERE p.active = 1
        GROUP BY p.id, p.name, p.type, p.phone
        HAVING (
            COALESCE(SUM(CASE WHEN t.type = 'entrada' THEN t.weight_kg END), 0) > 0
            OR COALESCE(SUM(CASE WHEN t.type = 'saida' THEN t.weight_kg END), 0) > 0
        )
        ORDER BY valor_pago DESC
    """
    return execute_query(query, tuple(params))
