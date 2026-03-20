# Sistema de Controle de Sucata

Sistema web para gerenciamento de sucatas, desenvolvido com **Streamlit** e **PostgreSQL**.

---

## Funcionalidades

| Módulo | Acesso | Descrição |
|---|---|---|
| **Dashboard** | Todos | Métricas mensais, resumo financeiro e movimentações recentes |
| **Operador** | Todos | Emissão de canhotos (recibos de atendimento) |
| **Entradas** | Todos | Registro de compras de materiais por fornecedor |
| **Saídas** | Admin | Registro de vendas com emissão de NF-e integrada |
| **Estoque** | Todos | Posição atual de estoque com valor estimado |
| **Cadastros** | Todos¹ | Materiais (com dados fiscais), parceiros, preços, usuários e Config. Fiscal |
| **Relatórios** | Todos | Análises com filtros, gráficos e exportação CSV |
| **Pagamentos** | Todos | Confirmação e cancelamento de canhotos pendentes |
| **Logs de Auditoria** | Admin | Histórico completo de todas as ações no sistema |
| **Processamento** | Todos | Conversão interna entre materiais (ex: latinha → alumínio) |

> ¹ Alterar preços, gerenciar usuários e configurar NF-e é restrito ao perfil Admin.

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
- **requests** — integração com API Nuvem Fiscal (NF-e)

---

## Estrutura do Projeto

```
Sucata/
├── app.py                      # Entrada principal + login
├── auth.py                     # Sessão persistente (cookie assinado)
├── db.py                       # Schema do banco + context manager
├── services.py                 # Lógica de negócio
├── nfe_service.py              # Integração NF-e (Nuvem Fiscal API)
├── requirements.txt
├── railway.toml                # Config de deploy (Railway)
├── .env.example                # Template de variáveis de ambiente
├── DOCUMENTACAO.md             # Documentação técnica completa
└── pages/
    ├── 1_📊_Dashboard.py
    ├── 2_🧾_Operador.py
    ├── 3_📥_Entradas.py
    ├── 4_📤_Saídas.py
    ├── 5_📦_Estoque.py
    ├── 6_📝_Cadastros.py
    ├── 7_📈_Relatórios.py
    ├── 8_💳_Pagamentos.py
    ├── 9_🔐_Logs.py
    └── 10_🔄_Processamento.py
```

---

## Banco de Dados

O schema é criado automaticamente na primeira inicialização. As migrations também rodam automaticamente ao iniciar.

| Tabela | Descrição |
|---|---|
| `users` | Contas de acesso com hash bcrypt e perfil (admin/operador) |
| `audit_logs` | Registro imutável de todas as ações realizadas no sistema |
| `materials` | Materiais com SKU e dados fiscais (NCM, CFOP, CSOSN) |
| `partners` | Parceiros com dados fiscais e endereço completo |
| `transactions` | Entradas/saídas com colunas NF-e (número, chave, status) |
| `prices` | Preço vigente por material |
| `canhotos` | Recibos de atendimento emitidos pelo operador |
| `canhoto_items` | Itens de cada canhoto |
| `fiscal_config` | Configuração do emitente para NF-e (CNPJ, endereço, CRT) |

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
# Edite o .env com suas credenciais

# 5. Inicie a aplicação
streamlit run app.py
```

Acesse em: `http://localhost:8501`

**Primeiro acesso:** usuário `admin`, senha `admin`. Troque a senha após o primeiro login.

---

## Variáveis de Ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DATABASE_URL` | **Sim** | URL de conexão PostgreSQL |
| `AUTH_COOKIE_SECRET` | **Sim** | Segredo para assinar tokens de sessão |
| `NUVEM_FISCAL_CLIENT_ID` | Para NF-e | Client ID da API Nuvem Fiscal |
| `NUVEM_FISCAL_CLIENT_SECRET` | Para NF-e | Client Secret da API Nuvem Fiscal |
| `APP_NAME` | Não | Nome exibido no cabeçalho |
| `AUTH_DAYS` | Não | Duração da sessão em dias (padrão: 7) |

```bash
# Gerar AUTH_COOKIE_SECRET seguro:
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Deploy no Railway

1. **Crie o projeto**: Railway → "New Project" → "Deploy from GitHub repo"

2. **Adicione o PostgreSQL**: `+ New` → `Database` → `PostgreSQL`
   A variável `DATABASE_URL` é injetada automaticamente.

3. **Configure as variáveis** em "Variables":
   ```
   AUTH_COOKIE_SECRET=<string gerada>
   NUVEM_FISCAL_CLIENT_ID=<seu client id>
   NUVEM_FISCAL_CLIENT_SECRET=<seu client secret>
   ```

4. **Deploy automático**: detecta `requirements.txt` e `railway.toml` automaticamente.

5. **Primeiro acesso**: tabelas criadas automaticamente. Login: `admin` / `admin`.

---

## NF-e (Nota Fiscal Eletrônica)

O sistema integra com a [Nuvem Fiscal API](https://www.nuvemfiscal.com.br) para emissão de NF-e modelo 55.

**Fluxo de configuração:**
1. Obtenha credenciais em nuvemfiscal.com.br → API → Credenciais
2. Configure as variáveis `NUVEM_FISCAL_CLIENT_ID` e `NUVEM_FISCAL_CLIENT_SECRET`
3. No painel Admin → Cadastros → Config. Fiscal: preencha dados do emitente
4. Em Cadastros → Materiais: preencha NCM, CFOP e CSOSN de cada material
5. Em Cadastros → Parceiros: preencha CNPJ/CPF, endereço e IE dos clientes
6. Em Saídas: clique em "Emitir NF-e" em qualquer saída registrada

---

## Backup

```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
psql $DATABASE_URL < backup_20260101.sql
```

---

**Versão:** 4.0.0
**Atualizado:** Março 2026
