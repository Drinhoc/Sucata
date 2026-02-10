"""
Módulo de serviços e lógica de negócio
Contém todas as operações relacionadas a materiais, parceiros e transações
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
from db import execute_query, execute_insert, execute_update


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
    query = "SELECT * FROM materials WHERE id = ?"
    results = execute_query(query, (material_id,))
    return results[0] if results else None


def create_material(name: str, unit: str = "kg") -> int:
    """Cria um novo material"""
    query = """
        INSERT INTO materials (name, unit, active)
        VALUES (?, ?, 1)
    """
    return execute_insert(query, (name.strip(), unit.strip()))


def update_material(material_id: int, name: str, unit: str) -> bool:
    """Atualiza um material existente"""
    query = """
        UPDATE materials
        SET name = ?, unit = ?
        WHERE id = ?
    """
    rows_affected = execute_update(query, (name.strip(), unit.strip(), material_id))
    return rows_affected > 0


def deactivate_material(material_id: int) -> bool:
    """Desativa um material (soft delete)"""
    query = "UPDATE materials SET active = 0 WHERE id = ?"
    rows_affected = execute_update(query, (material_id,))
    return rows_affected > 0


def activate_material(material_id: int) -> bool:
    """Reativa um material"""
    query = "UPDATE materials SET active = 1 WHERE id = ?"
    rows_affected = execute_update(query, (material_id,))
    return rows_affected > 0


# ============================================
# PARCEIROS
# ============================================

def get_all_partners(active_only: bool = True, partner_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retorna todos os parceiros cadastrados

    Args:
        active_only: Se True, retorna apenas parceiros ativos
        partner_type: Filtra por tipo ('fornecedor', 'cliente', 'ambos')
    """
    query = "SELECT * FROM partners WHERE 1=1"
    params = []

    if active_only:
        query += " AND active = 1"

    if partner_type:
        query += " AND (type = ? OR type = 'ambos')"
        params.append(partner_type)

    query += " ORDER BY name"

    return execute_query(query, tuple(params))


def get_partner_by_id(partner_id: int) -> Optional[Dict[str, Any]]:
    """Retorna um parceiro específico pelo ID"""
    query = "SELECT * FROM partners WHERE id = ?"
    results = execute_query(query, (partner_id,))
    return results[0] if results else None


def create_partner(name: str, partner_type: str, phone: str = "") -> int:
    """Cria um novo parceiro"""
    query = """
        INSERT INTO partners (name, type, phone, active)
        VALUES (?, ?, ?, 1)
    """
    return execute_insert(query, (name.strip(), partner_type, phone.strip()))


def update_partner(partner_id: int, name: str, partner_type: str, phone: str) -> bool:
    """Atualiza um parceiro existente"""
    query = """
        UPDATE partners
        SET name = ?, type = ?, phone = ?
        WHERE id = ?
    """
    rows_affected = execute_update(query, (name.strip(), partner_type, phone.strip(), partner_id))
    return rows_affected > 0


def deactivate_partner(partner_id: int) -> bool:
    """Desativa um parceiro (soft delete)"""
    query = "UPDATE partners SET active = 0 WHERE id = ?"
    rows_affected = execute_update(query, (partner_id,))
    return rows_affected > 0


def activate_partner(partner_id: int) -> bool:
    """Reativa um parceiro"""
    query = "UPDATE partners SET active = 1 WHERE id = ?"
    rows_affected = execute_update(query, (partner_id,))
    return rows_affected > 0


# ============================================
# TRANSAÇÕES
# ============================================

def get_current_stock(material_id: int) -> float:
    """
    Calcula o estoque atual de um material
    (soma de entradas - soma de saídas)
    """
    query = """
        SELECT
            COALESCE(SUM(CASE WHEN type = 'entrada' THEN weight_kg ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN type = 'saida' THEN weight_kg ELSE 0 END), 0) as stock
        FROM transactions
        WHERE material_id = ?
    """
    result = execute_query(query, (material_id,))
    return result[0]['stock'] if result else 0.0


def get_all_stock() -> List[Dict[str, Any]]:
    """
    Retorna o estoque atual de todos os materiais ativos
    com informações adicionais
    """
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
    notes: str = ""
) -> Tuple[bool, str, Optional[int]]:
    """
    Cria uma nova transação (entrada ou saída)

    Returns:
        Tuple[bool, str, Optional[int]]: (sucesso, mensagem, transaction_id)
    """
    # Validações
    if transaction_type not in ['entrada', 'saida']:
        return False, "Tipo de transação inválido", None

    if weight_kg <= 0:
        return False, "O peso deve ser maior que zero", None

    if price_per_kg < 0:
        return False, "O preço não pode ser negativo", None

    # Valida estoque para saídas
    if transaction_type == 'saida':
        current_stock = get_current_stock(material_id)
        if weight_kg > current_stock:
            return False, f"Estoque insuficiente. Disponível: {current_stock:.2f} kg", None

    # Calcula valor total
    total_value = weight_kg * price_per_kg

    # Insere a transação
    query = """
        INSERT INTO transactions
        (date, type, material_id, partner_id, weight_kg, price_per_kg, total_value, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
    """
    Retorna transações com filtros opcionais
    """
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
        query += " AND t.date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND t.date <= ?"
        params.append(end_date)

    if transaction_type:
        query += " AND t.type = ?"
        params.append(transaction_type)

    if material_id:
        query += " AND t.material_id = ?"
        params.append(material_id)

    if partner_id:
        query += " AND t.partner_id = ?"
        params.append(partner_id)

    query += " ORDER BY t.date DESC, t.created_at DESC"

    if limit:
        query += f" LIMIT {limit}"

    return execute_query(query, tuple(params))


def delete_transaction(transaction_id: int) -> bool:
    """Deleta uma transação"""
    query = "DELETE FROM transactions WHERE id = ?"
    rows_affected = execute_update(query, (transaction_id,))
    return rows_affected > 0


# ============================================
# RELATÓRIOS E MÉTRICAS
# ============================================

def get_monthly_metrics(year: int, month: int) -> Dict[str, float]:
    """
    Retorna métricas do mês (compras, vendas, lucro bruto)
    """
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
        WHERE date >= ? AND date < ?
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
    """
    Calcula uma estimativa do valor total em estoque
    baseado no preço médio de compra
    """
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
        )
    """
    result = execute_query(query)
    return result[0]['total_value'] if result and result[0]['total_value'] else 0.0


def get_material_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Retorna resumo por material com entradas, saídas e lucro
    """
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
        query += " AND t.date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND t.date <= ?"
        params.append(end_date)

    query += " GROUP BY m.id, m.name HAVING (weight_in > 0 OR weight_out > 0) ORDER BY profit DESC"

    return execute_query(query, tuple(params))
