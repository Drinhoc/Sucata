"""
Módulo de gerenciamento do banco de dados SQLite
Responsável pela criação e gestão das tabelas do sistema
"""

import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Any
import os

_DATA_DIR = os.getenv("DATA_DIR", ".")
DB_PATH = os.path.join(_DATA_DIR, "data.db")


@contextmanager
def get_db_connection():
    """Context manager para conexões com o banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Inicializa o banco de dados criando todas as tabelas necessárias"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Tabela de materiais
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                unit TEXT NOT NULL DEFAULT 'kg',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de parceiros (fornecedores e clientes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('fornecedor', 'cliente', 'ambos')),
                phone TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de transações (entradas e saídas)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('entrada', 'saida')),
                material_id INTEGER NOT NULL,
                partner_id INTEGER NOT NULL,
                weight_kg REAL NOT NULL CHECK(weight_kg > 0),
                price_per_kg REAL NOT NULL CHECK(price_per_kg >= 0),
                total_value REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (material_id) REFERENCES materials(id),
                FOREIGN KEY (partner_id) REFERENCES partners(id)
            )
        """)

        # Tabela de preços vigentes por material
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER NOT NULL UNIQUE,
                price_per_kg REAL NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (material_id) REFERENCES materials(id)
            )
        """)

        # Tabela de canhotos (recibos de atendimento)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canhotos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT NOT NULL UNIQUE,
                date DATE NOT NULL,
                client_name TEXT,
                partner_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pendente'
                    CHECK(status IN ('pendente', 'confirmado', 'cancelado')),
                total_value REAL NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (partner_id) REFERENCES partners(id)
            )
        """)

        # Tabela de itens de cada canhoto
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canhoto_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canhoto_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                weight_kg REAL NOT NULL,
                price_per_kg REAL NOT NULL,
                total_value REAL NOT NULL,
                FOREIGN KEY (canhoto_id) REFERENCES canhotos(id),
                FOREIGN KEY (material_id) REFERENCES materials(id)
            )
        """)

        # Índices para melhor performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_date
            ON transactions(date)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_type
            ON transactions(type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_material
            ON transactions(material_id)
        """)

        conn.commit()


def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """
    Executa uma query SELECT e retorna os resultados como lista de dicionários

    Args:
        query: Query SQL a ser executada
        params: Parâmetros para a query

    Returns:
        Lista de dicionários com os resultados
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def execute_insert(query: str, params: tuple = ()) -> int:
    """
    Executa uma query INSERT e retorna o ID do registro inserido

    Args:
        query: Query SQL a ser executada
        params: Parâmetros para a query

    Returns:
        ID do registro inserido
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid


def execute_update(query: str, params: tuple = ()) -> int:
    """
    Executa uma query UPDATE ou DELETE e retorna o número de linhas afetadas

    Args:
        query: Query SQL a ser executada
        params: Parâmetros para a query

    Returns:
        Número de linhas afetadas
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount
