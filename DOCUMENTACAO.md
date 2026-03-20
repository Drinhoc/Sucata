# Documentação Técnica — Sistema de Controle de Sucata

> Versão 4.0.0 — Março 2026

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Arquitetura](#2-arquitetura)
3. [Módulos e Páginas](#3-módulos-e-páginas)
4. [Banco de Dados](#4-banco-de-dados)
5. [Autenticação e Permissões](#5-autenticação-e-permissões)
6. [Integração NF-e (Nuvem Fiscal)](#6-integração-nf-e-nuvem-fiscal)
7. [Variáveis de Ambiente](#7-variáveis-de-ambiente)
8. [Deploy e Infraestrutura](#8-deploy-e-infraestrutura)
9. [Fluxos de Uso Principais](#9-fluxos-de-uso-principais)
10. [Decisões Técnicas](#10-decisões-técnicas)

---

## 1. Visão Geral

Sistema web multi-usuário para gestão operacional de depósitos de sucata (ferro-velho / reciclagem de metais). Gerencia compras de fornecedores, vendas a clientes, estoque, emissão de recibos e notas fiscais eletrônicas.

**Tecnologias principais:**
- Frontend/Backend: Streamlit (Python)
- Banco de dados: PostgreSQL
- Deploy: Railway
- Emissão fiscal: Nuvem Fiscal API (NF-e modelo 55)

---

## 2. Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                        Streamlit App                        │
│                                                             │
│  app.py (login/entry)     auth.py (session + cookies)      │
│                                                             │
│  pages/                                                     │
│    1_Dashboard   2_Operador   3_Entradas   4_Saídas        │
│    5_Estoque     6_Cadastros  7_Relatórios 8_Pagamentos     │
│    9_Logs        10_Processamento                           │
│                                                             │
│  services.py (business logic)   nfe_service.py (NF-e API)  │
│                                                             │
│  db.py (connection + schema + migrations)                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
              ┌─────────▼─────────┐     ┌──────────────────────┐
              │   PostgreSQL      │     │  Nuvem Fiscal API    │
              │  (Railway addon)  │     │  (OAuth2 + REST)     │
              └───────────────────┘     └──────────────────────┘
```

### Arquivos principais

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | Ponto de entrada; formulário de login; seed inicial do admin |
| `auth.py` | Sessão via cookie assinado (itsdangerous); `require_auth()` |
| `db.py` | Context manager de conexão; criação/migração de schema |
| `services.py` | Toda a lógica de negócio (sem SQL direto nas páginas) |
| `nfe_service.py` | Integração completa com a Nuvem Fiscal API |
| `pages/` | Interface Streamlit (1 arquivo = 1 página) |

---

## 3. Módulos e Páginas

### 3.1 Dashboard (`1_📊_Dashboard.py`)

Visão geral do negócio no mês corrente:
- Métricas: compras totais, vendas totais, lucro bruto, movimentações
- Comparativo com mês anterior (delta percentual)
- Últimas transações (entradas e saídas)
- Estoque atual resumido
- Acesso: todos os usuários

### 3.2 Operador / Canhotos (`2_🧾_Operador.py`)

Fluxo rápido para receber fornecedores no balcão:
1. Seleciona materiais, pesos e preços (pré-carregados da tabela de preços)
2. Gera um "canhoto" (recibo) com número sequencial
3. Canhoto fica em status `pendente` até confirmação em Pagamentos
- Acesso: todos os usuários

### 3.3 Entradas (`3_📥_Entradas.py`)

Registro direto de compras (fora do fluxo de canhoto):
- Seleciona material, fornecedor, data, peso e preço/kg
- Calcula valor total automaticamente
- Registra transação do tipo `entrada`
- Histórico com filtros por período, material e fornecedor
- Acesso: todos os usuários

### 3.4 Saídas (`4_📤_Saídas.py`)

Registro de vendas a clientes:
- Valida estoque disponível antes de registrar
- Modo "Ajuste Manual" (sem comprador) para correções
- **Painel NF-e** integrado no histórico:
  - Emitir NF-e para cada saída
  - Consultar status (autorizada, cancelada, denegada)
  - Download DANFE (PDF) e XML
  - Cancelar NF-e com justificativa
- Acesso: **somente admin**

### 3.5 Estoque (`5_📦_Estoque.py`)

Posição atual de cada material:
- Estoque calculado: entradas - saídas
- Valor estimado (peso × preço médio de compra)
- Acesso: todos os usuários

### 3.6 Cadastros (`6_📝_Cadastros.py`)

Central de configuração do sistema. 5 abas:

**Materiais:**
- Cadastro com nome, unidade, SKU
- Campos fiscais: NCM, CFOP, CSOSN, Unidade Fiscal
- Indicador 🟢/🔴 se dados fiscais estão completos
- Expander "Dados fiscais" para edição inline
- Ativar/Desativar (soft delete)

**Parceiros:**
- Cadastro com nome, tipo, telefone
- Dados fiscais: CNPJ/CPF, IE
- Endereço completo: logradouro, número, complemento, bairro, município, código IBGE, UF, CEP
- Indicador 🟢/🔴 de completude fiscal
- Expander "Dados fiscais/endereço" para edição inline

**Preços Vigentes:**
- Define o preço de compra por kg de cada material
- Usado automaticamente no módulo Operador
- Edição: somente admin

**Usuários** *(admin)*:
- Criar, ativar/desativar, alterar perfil, resetar senha
- Não é possível desativar ou rebaixar o próprio usuário

**Config. Fiscal** *(admin)*:
- Dados do emitente: CNPJ, Razão Social, IE, CRT, telefone, e-mail, endereço completo
- Seleção de ambiente: homologação ou produção
- Botão de teste de conexão com a API

### 3.7 Relatórios (`7_📈_Relatórios.py`)

Análises com filtros de período:
- Comparativo período atual vs anterior
- Evolução temporal (diária/semanal/mensal)
- Análise por material (preço médio, spread, margem)
- Análise por parceiro (volumes, valores)
- Exportação CSV de todas as tabelas
- Acesso: todos os usuários

### 3.8 Pagamentos (`8_💳_Pagamentos.py`)

Confirmação de canhotos pendentes:
- Lista canhotos em aberto
- Confirmar: cria transações de entrada no estoque
- Cancelar: remove o canhoto sem registrar no estoque
- Acesso: todos os usuários

### 3.9 Logs de Auditoria (`9_🔐_Logs.py`)

Histórico imutável de todas as ações:
- Filtros: usuário, ação, entidade, data
- Payload JSON com detalhes de cada operação
- Acesso: **somente admin**

### 3.10 Processamento Interno (`10_🔄_Processamento.py`)

Conversão de material para material (ex: lata de alumínio → alumínio limpo):
- Cria atomicamente uma saída do material de origem e uma entrada no material de destino
- Código único `PROC#YYYYMMDDHHMMSS-XXXX` vinculado às duas transações
- Valida estoque antes de processar
- Acesso: todos os usuários

---

## 4. Banco de Dados

### Schema completo

#### `users`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| username | TEXT UNIQUE NOT NULL | Login do usuário |
| name | TEXT NOT NULL | Nome completo |
| password_hash | TEXT NOT NULL | Hash bcrypt |
| role | TEXT DEFAULT 'operador' | `admin` ou `operador` |
| active | INTEGER DEFAULT 1 | Soft delete |
| created_at | TIMESTAMP | |
| last_login | TIMESTAMP | Atualizado a cada login |

#### `audit_logs`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| user_id | INTEGER | FK users.id (nullable) |
| username | TEXT | Snapshot do login |
| action | TEXT | CREATE, UPDATE, DEACTIVATE, etc. |
| entity | TEXT | material, partner, transaction, etc. |
| entity_id | INTEGER | ID da entidade afetada |
| details | TEXT | JSON com dados antes/depois |
| created_at | TIMESTAMP | |

#### `materials`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| name | TEXT NOT NULL | |
| unit | TEXT DEFAULT 'kg' | kg, ton, unidade, m², m³ |
| sku | TEXT UNIQUE | Código interno (opcional) |
| ncm | TEXT | Código NCM (8 dígitos) |
| cfop | TEXT | CFOP da operação |
| csosn | TEXT | CSOSN (Simples Nacional) ou CST |
| unidade_fiscal | TEXT DEFAULT 'KG' | Unidade para NF-e |
| active | INTEGER DEFAULT 1 | Soft delete |
| created_at | TIMESTAMP | |

#### `partners`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| name | TEXT NOT NULL | |
| type | TEXT | `fornecedor`, `cliente`, `ambos` |
| phone | TEXT | |
| cnpj_cpf | TEXT | CNPJ ou CPF |
| ie | TEXT | Inscrição Estadual |
| logradouro | TEXT | |
| numero | TEXT | |
| complemento | TEXT | |
| bairro | TEXT | |
| municipio | TEXT | |
| municipio_ibge | TEXT | Código IBGE de 7 dígitos |
| uf | TEXT | Sigla do estado |
| cep | TEXT | |
| pais | TEXT DEFAULT '1058' | Código do país (Brasil = 1058) |
| active | INTEGER DEFAULT 1 | Soft delete |
| created_at | TIMESTAMP | |

#### `transactions`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| date | DATE NOT NULL | Data da operação |
| type | TEXT | `entrada` ou `saida` |
| material_id | INTEGER FK | |
| partner_id | INTEGER FK | Nullable (ajuste manual) |
| weight_kg | NUMERIC(12,3) | |
| price_per_kg | NUMERIC(12,2) | |
| total_value | NUMERIC(12,2) | Calculado com Decimal |
| notes | TEXT | Observações livres |
| nf_numero | TEXT | Número sequencial da NF-e |
| nf_serie | TEXT DEFAULT '1' | Série da NF-e |
| nf_chave | TEXT UNIQUE | Chave de 44 dígitos |
| nf_status | TEXT | autorizada, cancelada, denegada, erro |
| nf_danfe_url | TEXT | URL do DANFE na Nuvem Fiscal |
| nf_xml_url | TEXT | URL do XML na Nuvem Fiscal |
| nf_emitida_em | TIMESTAMP | Timestamp da autorização |
| created_at | TIMESTAMP | |

#### `prices`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| material_id | INTEGER UNIQUE FK | |
| price_per_kg | NUMERIC(12,2) DEFAULT 0 | |
| updated_at | TIMESTAMP | Atualizado em cada mudança de preço |

#### `canhotos`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| number | TEXT UNIQUE | Número sequencial (0001, 0002...) |
| date | DATE | |
| client_name | TEXT | Nome livre (sem FK) |
| partner_id | INTEGER FK | Opcional |
| status | TEXT DEFAULT 'pendente' | pendente, confirmado, cancelado |
| total_value | NUMERIC(12,2) | Soma dos itens |
| created_at | TIMESTAMP | |

#### `canhoto_items`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| canhoto_id | INTEGER FK | |
| material_id | INTEGER FK | |
| weight_kg | NUMERIC(12,3) | |
| price_per_kg | NUMERIC(12,2) | |
| total_value | NUMERIC(12,2) | |

#### `fiscal_config`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | SERIAL PK | |
| cnpj | TEXT UNIQUE NOT NULL | CNPJ do emitente |
| razao_social | TEXT NOT NULL | |
| nome_fantasia | TEXT | |
| ie | TEXT | Inscrição Estadual |
| crt | TEXT DEFAULT '1' | Regime tributário (1=Simples, 3=Normal) |
| logradouro, numero, complemento | TEXT | Endereço |
| bairro, municipio, municipio_ibge | TEXT | |
| uf, cep | TEXT | |
| telefone, email | TEXT | |
| ambiente | TEXT DEFAULT 'homologacao' | homologacao ou producao |
| updated_at | TIMESTAMP | |

### Migrations

O sistema usa `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` para migrations automáticas. Ao iniciar, `db.py` verifica e adiciona colunas novas sem quebrar dados existentes.

---

## 5. Autenticação e Permissões

### Mecanismo

1. Login via `app.py` → verifica username/password_hash (bcrypt)
2. Gera token assinado com `itsdangerous.URLSafeTimedSerializer`
3. Token armazenado em cookie via `streamlit-cookies-controller`
4. Cada página chama `require_auth()` que valida o cookie e popula `st.session_state`

### Session State após login

```python
st.session_state['authenticated'] = True
st.session_state['user_id'] = int
st.session_state['username'] = str
st.session_state['name'] = str
st.session_state['role'] = 'admin' | 'operador'
```

### Controle de Acesso

| Recurso | Operador | Admin |
|---|---|---|
| Dashboard, Estoque, Relatórios | ✅ | ✅ |
| Entradas, Operador, Pagamentos, Processamento | ✅ | ✅ |
| Saídas (registrar) | ❌ | ✅ |
| Alterar preços | ❌ | ✅ |
| Gerenciar usuários | ❌ | ✅ |
| Config. Fiscal / NF-e | ❌ | ✅ |
| Logs de Auditoria | ❌ | ✅ |

---

## 6. Integração NF-e (Nuvem Fiscal)

### Visão Geral

O módulo `nfe_service.py` implementa a integração completa com a [Nuvem Fiscal API](https://dev.nuvemfiscal.com.br) para emissão de NF-e modelo 55, versão 4.00.

### Autenticação OAuth2

```python
# Endpoint: POST https://auth.nuvemfiscal.com.br/oauth/token
# grant_type: client_credentials
# scope: nfe

# Cache em memória (_token_cache) para reutilizar tokens
# dentro do mesmo processo sem nova requisição a cada chamada
```

### Fluxo de Emissão

```
emit_nfe(transaction_id)
    │
    ├── get_fiscal_config()         # Lê emitente do banco
    ├── get_partner_by_id()         # Lê destinatário do banco
    ├── get_material_by_id()        # Lê item (NCM, CFOP, etc.)
    │
    ├── _build_nfe_payload()        # Monta JSON NF-e 4.00
    │     ├── Identificação (cUF, cNF, natOp, mod=55, série, dhEmi)
    │     ├── Emitente (CNPJ, IE, endereço, CRT)
    │     ├── Destinatário (CNPJ/CPF, IE, endereço)
    │     ├── Produtos/Itens (NCM, CFOP, qCom, vUnCom, vProd)
    │     ├── ICMS (CSOSN se CRT=1, CST se CRT=3)
    │     ├── PIS/COFINS (CST 07 — isento, padrão sucata)
    │     └── Total e Transporte
    │
    ├── POST /nfe                   # Envia para Nuvem Fiscal
    ├── POST /nfe/{id}/emitir       # Solicita autorização SEFAZ
    │
    └── UPDATE transactions         # Salva número, chave, status
```

### Payload NF-e — Campos obrigatórios configurados

| Campo | Fonte |
|---|---|
| CNPJ emitente | `fiscal_config.cnpj` |
| CRT | `fiscal_config.crt` |
| Endereço emitente | Todos os campos de `fiscal_config` |
| NCM | `materials.ncm` |
| CFOP | `materials.cfop` |
| CSOSN (CRT=1) | `materials.csosn` |
| Unidade fiscal | `materials.unidade_fiscal` |
| CNPJ/CPF destinatário | `partners.cnpj_cpf` |
| Endereço destinatário | Campos `partners.logradouro`, `uf`, etc. |
| Peso / valor | `transactions.weight_kg`, `total_value` |

### Estados da NF-e

| Status | Descrição |
|---|---|
| `NULL` | Não emitida |
| `processando` | Aguardando resposta da SEFAZ |
| `autorizada` | NF-e válida, pode baixar DANFE/XML |
| `cancelada` | Cancelada dentro do prazo legal |
| `denegada` | Rejeitada pela SEFAZ (destinatário irregular) |
| `erro` | Falha na emissão, pode tentar novamente |

### Funções do módulo `nfe_service.py`

| Função | Descrição |
|---|---|
| `get_fiscal_config()` | Lê configuração do emitente |
| `save_fiscal_config(data)` | Salva/atualiza configuração |
| `_get_access_token()` | OAuth2 com cache em memória |
| `test_connection()` | Testa credenciais da API |
| `_build_nfe_payload(...)` | Monta payload JSON completo |
| `emit_nfe(transaction_id)` | Emite NF-e para uma transação |
| `get_nfe_status(transaction_id)` | Consulta status na SEFAZ |
| `cancel_nfe(transaction_id, justificativa)` | Cancela NF-e |
| `download_nfe_file(nf_chave, type)` | Baixa DANFE (pdf) ou XML |

### Configuração necessária antes de emitir

1. **Variáveis de ambiente** (Railway → Variables):
   - `NUVEM_FISCAL_CLIENT_ID`
   - `NUVEM_FISCAL_CLIENT_SECRET`

2. **Dados do emitente** (Cadastros → Config. Fiscal):
   - CNPJ, Razão Social, IE, CRT, endereço completo, ambiente

3. **Dados fiscais dos materiais** (Cadastros → Materiais):
   - NCM, CFOP, CSOSN (ou CST)

4. **Dados fiscais dos parceiros/clientes** (Cadastros → Parceiros):
   - CNPJ/CPF, endereço completo com código IBGE

---

## 7. Variáveis de Ambiente

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `DATABASE_URL` | Sim | — | PostgreSQL connection string |
| `AUTH_COOKIE_SECRET` | Sim | — | Segredo para assinatura de cookies |
| `NUVEM_FISCAL_CLIENT_ID` | Para NF-e | — | Client ID OAuth2 Nuvem Fiscal |
| `NUVEM_FISCAL_CLIENT_SECRET` | Para NF-e | — | Client Secret OAuth2 Nuvem Fiscal |
| `APP_NAME` | Não | `Sistema de Controle de Sucata` | Nome no cabeçalho |
| `AUTH_DAYS` | Não | `7` | Expiração da sessão em dias |

---

## 8. Deploy e Infraestrutura

### Railway

O projeto é configurado via `railway.toml`. A variável `DATABASE_URL` é injetada automaticamente pelo add-on PostgreSQL do Railway.

### Startup

Na inicialização (`app.py` → `init_db()`):
1. Cria todas as tabelas se não existirem
2. Executa migrations (ALTER TABLE ADD COLUMN IF NOT EXISTS)
3. Chama `seed_initial_data()` — cria admin padrão se não houver usuários

### Sem migrações manuais

Todas as alterações de schema são seguras e idempotentes. O sistema pode ser atualizado sem downtime:
```python
ALTER TABLE materials ADD COLUMN IF NOT EXISTS ncm TEXT;
```

---

## 9. Fluxos de Uso Principais

### Fluxo 1: Operador recebe fornecedor (canhoto)

```
Operador → Módulo Operador
  → Preenche nome do cliente (livre) ou seleciona parceiro
  → Adiciona itens: material + peso + preço
  → Clica "Emitir Canhoto"
  → Canhoto gerado com número sequencial (status: pendente)
  → Admin confirma em Pagamentos
  → Transações de entrada registradas no estoque
```

### Fluxo 2: Registrar entrada direta

```
Admin/Operador → Entradas
  → Seleciona material, fornecedor, data, peso, preço
  → Clica "Registrar Entrada"
  → Transação inserida, estoque atualizado
```

### Fluxo 3: Registrar saída + emitir NF-e

```
Admin → Saídas
  → Seleciona material, cliente, peso, preço
  → Clica "Registrar Saída"
  → Transação inserida (tipo: saída)
  → No histórico, expande a saída
  → Clica "Emitir NF-e"
  → Sistema monta payload e envia para Nuvem Fiscal
  → NF-e autorizada pela SEFAZ
  → Status atualizado: "autorizada"
  → Download DANFE / XML disponível
```

### Fluxo 4: Processamento interno

```
Admin/Operador → Processamento
  → Seleciona material de origem e destino
  → Informa peso
  → Sistema cria atomicamente:
      - Saída do material de origem
      - Entrada no material de destino
  → Ambas vinculadas ao mesmo código PROC#...
```

---

## 10. Decisões Técnicas

### Valores monetários com `Decimal`

Todos os cálculos de `total_value` usam `decimal.Decimal` para evitar erros de ponto flutuante:

```python
total_value = (
    Decimal(str(weight_kg)) * Decimal(str(price_per_kg))
).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

Isso garante que `1000 kg × R$ 0,07/kg = R$ 70,00` (e não `70.00000000000001`).

### Rollback explícito no context manager

```python
@contextmanager
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

Transações nunca ficam abertas em caso de erro.

### Audit log nunca interrompe a aplicação

```python
def log_action(...):
    try:
        execute_insert(...)
    except Exception as e:
        logging.error(f"[AUDIT FAIL] action={action} entity={entity} id={entity_id}: {e}")
        # não relança — falha de log não pode derrubar operação principal
```

### Token OAuth2 com cache em memória

```python
_token_cache: Dict[str, Any] = {}
# Chave: client_id + ambiente
# Valor: {"token": str, "expires_at": float}
```

Evita round-trip de autenticação a cada chamada de API dentro do mesmo processo Streamlit.

### Soft delete

Materiais e parceiros nunca são deletados fisicamente. A coluna `active` permite desativar sem perder histórico de transações.

### PIS/COFINS para sucata

Por padrão, as NF-e emitidas usam CST 07 (operação isenta) para PIS e COFINS — código correto para venda de sucata conforme legislação brasileira.

---

*Documentação gerada em Março 2026*
