"""
Módulo de gerenciamento do banco de dados PostgreSQL
Responsável pela criação e gestão das tabelas do sistema
"""

import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from typing import List, Dict, Any
import os

DATABASE_URL = os.getenv("DATABASE_URL", "")


@contextmanager
def get_db_connection():
    """Context manager para conexões com o banco de dados"""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Inicializa o banco de dados criando todas as tabelas necessárias"""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Tabela de usuários do sistema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'operador'
                    CHECK(role IN ('admin', 'operador')),
                active SMALLINT NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT NOW(),
                last_login TIMESTAMP
            )
        """)

        # Tabela de logs de auditoria
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                entity TEXT NOT NULL,
                entity_id INTEGER,
                details TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at
            ON audit_logs(created_at)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id
            ON audit_logs(user_id)
        """)

        # Tabela de materiais
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                unit TEXT NOT NULL DEFAULT 'kg',
                active SMALLINT NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Tabela de parceiros (fornecedores e clientes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partners (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('fornecedor', 'cliente', 'ambos')),
                phone TEXT,
                active SMALLINT NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Tabela de transações (entradas e saídas)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('entrada', 'saida')),
                material_id INTEGER NOT NULL,
                partner_id INTEGER,
                weight_kg REAL NOT NULL CHECK(weight_kg > 0),
                price_per_kg NUMERIC(12,2) NOT NULL CHECK(price_per_kg >= 0),
                total_value NUMERIC(12,2) NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (material_id) REFERENCES materials(id),
                FOREIGN KEY (partner_id) REFERENCES partners(id)
            )
        """)

        # Migration: permite partner_id nulo (ajuste manual sem comprador)
        cursor.execute("""
            ALTER TABLE transactions ALTER COLUMN partner_id DROP NOT NULL
        """)

        # Migration: colunas monetárias de REAL para NUMERIC(12,2)
        # Usar DO $$ para ser idempotente: só converte se ainda for REAL
        cursor.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='transactions' AND column_name='price_per_kg' AND data_type='real'
                ) THEN
                    ALTER TABLE transactions
                        ALTER COLUMN price_per_kg TYPE NUMERIC(12,2) USING price_per_kg::NUMERIC(12,2),
                        ALTER COLUMN total_value  TYPE NUMERIC(12,2) USING total_value::NUMERIC(12,2);
                END IF;
            END $$;
        """)

        cursor.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='prices' AND column_name='price_per_kg' AND data_type='real'
                ) THEN
                    ALTER TABLE prices
                        ALTER COLUMN price_per_kg TYPE NUMERIC(12,2) USING price_per_kg::NUMERIC(12,2);
                END IF;
            END $$;
        """)

        cursor.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='canhotos' AND column_name='total_value' AND data_type='real'
                ) THEN
                    ALTER TABLE canhotos
                        ALTER COLUMN total_value TYPE NUMERIC(12,2) USING total_value::NUMERIC(12,2);
                END IF;
            END $$;
        """)

        cursor.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='canhoto_items' AND column_name='price_per_kg' AND data_type='real'
                ) THEN
                    ALTER TABLE canhoto_items
                        ALTER COLUMN price_per_kg TYPE NUMERIC(12,2) USING price_per_kg::NUMERIC(12,2),
                        ALTER COLUMN total_value  TYPE NUMERIC(12,2) USING total_value::NUMERIC(12,2);
                END IF;
            END $$;
        """)

        # Tabela de preços vigentes por material
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id SERIAL PRIMARY KEY,
                material_id INTEGER NOT NULL UNIQUE,
                price_per_kg NUMERIC(12,2) NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (material_id) REFERENCES materials(id)
            )
        """)

        # Tabela de canhotos (recibos de atendimento)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canhotos (
                id SERIAL PRIMARY KEY,
                number TEXT NOT NULL UNIQUE,
                date DATE NOT NULL,
                client_name TEXT,
                partner_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pendente'
                    CHECK(status IN ('pendente', 'confirmado', 'cancelado')),
                total_value NUMERIC(12,2) NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (partner_id) REFERENCES partners(id)
            )
        """)

        # Tabela de itens de cada canhoto
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canhoto_items (
                id SERIAL PRIMARY KEY,
                canhoto_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                weight_kg REAL NOT NULL,
                price_per_kg NUMERIC(12,2) NOT NULL,
                total_value NUMERIC(12,2) NOT NULL,
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
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def execute_insert(query: str, params: tuple = ()) -> int:
    """
    Executa uma query INSERT e retorna o ID do registro inserido
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query.rstrip() + " RETURNING id", params)
        conn.commit()
        return cursor.fetchone()[0]


def execute_update(query: str, params: tuple = ()) -> int:
    """
    Executa uma query UPDATE ou DELETE e retorna o número de linhas afetadas
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount


def execute_in_transaction(queries_and_params: list) -> list:
    """
    Executa múltiplos INSERTs numa única transação atômica.
    Cada entrada da lista deve ser uma tupla (query_str, params_tuple).
    As queries NÃO devem incluir RETURNING — ele é adicionado automaticamente.
    Retorna lista de IDs inseridos na mesma ordem.
    Em caso de qualquer erro, faz rollback e re-lança a exceção.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        ids = []
        try:
            for query, params in queries_and_params:
                cursor.execute(query.rstrip() + " RETURNING id", params)
                ids.append(cursor.fetchone()[0])
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return ids
