# Sistema de Controle de Sucata

Sistema web para gerenciamento de sucatas, desenvolvido com **Streamlit** e **PostgreSQL**.

---

## Funcionalidades

| Módulo | Acesso | Descrição |
|---|---|---|
| **Dashboard** | Todos | Métricas mensais, resumo financeiro e movimentações recentes |
| **Entradas** | Todos | Registro de compras de materiais por fornecedor |
| **Saídas** | Admin | Registro de vendas com validação de estoque |
| **Estoque** | Todos | Posição atual de estoque com valor estimado |
| **Cadastros** | Todos¹ | Materiais (com SKU), parceiros, preços e usuários |
| **Relatórios** | Todos | Análises com filtros, gráficos e exportação CSV |
| **Operador** | Todos | Emissão de canhotos (recibos de atendimento) |
| **Pagamentos** | Todos | Confirmação e cancelamento de canhotos pendentes |
| **Processamento** | Todos | Conversão interna entre materiais (ex: latinha → alumínio) |
| **Logs de Auditoria** | Admin | Histórico completo de todas as ações no sistema |

> ¹ Alterar preços e gerenciar usuários é restrito ao perfil Admin.

---

## Stack

- **Python 3.8+**
- **Streamlit ≥ 1.32** — framework web
- **PostgreSQL** — banco de dados
- **psycopg2-binary** — driver PostgreSQL
- **bcrypt** — hash de senhas
- **itsdangerous** — assinatura de tokens de sessão
- **streamlit-cookies-controller** — sessão persistente via cookie
- **Pandas** — relatórios e exportação CSV

---

## Estrutura do Projeto

```
Sucata/
├── app.py                      # Entrada principal + login
├── auth.py                     # Sessão persistente (cookie assinado)
├── db.py                       # Schema do banco + context manager
├── services.py                 # Lógica de negócio
├── requirements.txt
├── railway.toml                # Config de deploy (Railway)
├── .env.example                # Template de variáveis de ambiente
└── pages/
    ├── 1_📊_Dashboard.py
    ├── 2_📥_Entradas.py
    ├── 3_📤_Saídas.py
    ├── 4_📦_Estoque.py
    ├── 5_📝_Cadastros.py
    ├── 6_📈_Relatórios.py
    ├── 7_🧾_Operador.py
    ├── 8_💳_Pagamentos.py
    ├── 9_🔐_Logs.py
    └── 10_🔄_Processamento.py
```

---

## Banco de Dados

O schema é criado automaticamente na primeira inicialização. As migrations também rodam automaticamente ao iniciar, sem precisar de comando manual.

| Tabela | Descrição |
|---|---|
| `users` | Contas de acesso com hash bcrypt e perfil (admin/operador) |
| `audit_logs` | Registro imutável de todas as ações realizadas no sistema |
| `materials` | Materiais cadastrados, com SKU e unidade |
| `partners` | Parceiros: fornecedores, clientes ou ambos |
| `transactions` | Entradas e saídas de materiais |
| `prices` | Preço vigente por material (usado pelo operador) |
| `canhotos` | Recibos de atendimento emitidos pelo operador |
| `canhoto_items` | Itens de cada canhoto |

> Todos os valores monetários são armazenados como `NUMERIC(12,2)` (precisão exata).

---

## Instalação Local

### Pré-requisitos

- Python 3.8+
- PostgreSQL rodando localmente

### Passo a Passo

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd Sucata

# 2. Crie e ative o ambiente virtual
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais (veja seção abaixo)

# 5. Inicie a aplicação
streamlit run app.py
```

Acesse em: `http://localhost:8501`

**Primeiro acesso:** usuário `admin`, senha `admin`. Troque a senha após o primeiro login.

---

## Variáveis de Ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DATABASE_URL` | **Sim** | URL de conexão PostgreSQL (`postgresql://user:pass@host:5432/db`) |
| `AUTH_COOKIE_SECRET` | **Sim** | Segredo para assinar tokens de sessão — use uma string longa e aleatória |
| `APP_NAME` | Não | Nome exibido no cabeçalho (padrão: `Sistema de Controle de Sucata`) |
| `AUTH_DAYS` | Não | Duração da sessão em dias (padrão: `7`) |

Para gerar um `AUTH_COOKIE_SECRET` seguro:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Deploy no Railway

1. **Crie o projeto**: Railway → "New Project" → "Deploy from GitHub repo"

2. **Adicione o PostgreSQL**: no painel do projeto → "+ New" → "Database" → "PostgreSQL"
   A variável `DATABASE_URL` é injetada automaticamente.

3. **Configure as variáveis** (em "Variables"):
   ```
   AUTH_COOKIE_SECRET=<string gerada acima>
   APP_NAME=Sistema de Controle de Sucata
   ```

4. **Deploy automático**: o Railway detecta o `requirements.txt` e o `railway.toml`, sem configuração adicional.

5. **Primeiro acesso**: tabelas criadas automaticamente. Login com `admin` / `admin`.

---

## Backup

```bash
# Exportar
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restaurar
psql $DATABASE_URL < backup_20260101.sql
```

---

## Problemas Comuns

**Erro de conexão com o banco**
- Verifique se `DATABASE_URL` está correta
- No Railway: confirme que o plugin PostgreSQL está adicionado

**Sessão não persiste após F5**
- Verifique se `AUTH_COOKIE_SECRET` está definido
- Evite usar o valor padrão do `.env.example` em produção

**Página em branco ou erro 500**
- Confirme que todas as dependências estão instaladas: `pip install -r requirements.txt`
- Verifique os logs do Railway para detalhes

---

**Versão:** 3.0.0
**Atualizado:** Março 2026
