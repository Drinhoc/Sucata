# Sistema de Controle de Sucata

Sistema web profissional e completo para gerenciamento de sucatas, desenvolvido com **Streamlit** e **PostgreSQL**.

## Funcionalidades

- **Dashboard**: Visão geral do negócio com métricas mensais e resumos
- **Entradas**: Registro de compras de materiais de fornecedores
- **Saídas**: Registro de vendas com validação de estoque
- **Estoque**: Consulta de estoque atual e valores estimados
- **Cadastros**: Gerenciamento de materiais e parceiros (fornecedores/clientes)
- **Relatórios**: Análises detalhadas com filtros e exportação CSV
- **Operador (Canhotos)**: Geração de recibos e confirmação de pagamentos
- **Login Simples**: Proteção por senha configurável

## Estrutura do Projeto

```
Sucata/
├── app.py                      # Aplicação principal com autenticação
├── db.py                       # Gerenciamento do banco PostgreSQL
├── services.py                 # Lógica de negócio
├── requirements.txt            # Dependências Python
├── railway.toml                # Configuração de deploy no Railway
├── .env.example               # Exemplo de configuração
├── .env                       # Configuração local (criar a partir do .env.example)
└── pages/
    ├── 1_📊_Dashboard.py
    ├── 2_📥_Entradas.py
    ├── 3_📤_Saídas.py
    ├── 4_📦_Estoque.py
    ├── 5_📝_Cadastros.py
    ├── 6_📈_Relatórios.py
    ├── 7_🧾_Operador.py
    └── 8_💳_Pagamentos.py
```

## Instalação e Execução Local

### Pré-requisitos

- Python 3.8 ou superior
- PostgreSQL rodando localmente (ou acesso a uma instância remota)

### Passo a Passo

1. **Clone o repositório**:

```bash
git clone <url-do-repositorio>
cd Sucata
```

2. **Crie um ambiente virtual** (recomendado):

```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

3. **Instale as dependências**:

```bash
pip install -r requirements.txt
```

4. **Configure o arquivo .env**:

```bash
cp .env.example .env
```

Edite o `.env` com suas configurações:

```env
APP_NAME=Sistema de Controle de Sucata
APP_PASSWORD=suasenhaforteaqui
DATABASE_URL=postgresql://usuario:senha@localhost:5432/sucata
```

5. **Execute a aplicação**:

```bash
streamlit run app.py
```

6. **Acesse no navegador**: `http://localhost:8501`

## Deploy no Railway

### Passo a Passo

1. **Crie o projeto no Railway**:
   - Faça login em [railway.app](https://railway.app)
   - Clique em "New Project" → "Deploy from GitHub repo"
   - Escolha o repositório do projeto

2. **Adicione o plugin PostgreSQL**:
   - No painel do projeto, clique em "+ New" → "Database" → "PostgreSQL"
   - A variável `DATABASE_URL` será injetada automaticamente

3. **Configure as variáveis de ambiente** (em "Variables"):
   ```
   APP_NAME=Sistema de Controle de Sucata
   APP_PASSWORD=suasenhaforteaqui
   ```
   > `DATABASE_URL` é configurada automaticamente pelo plugin PostgreSQL — não é necessário adicionar manualmente.

4. **O `railway.toml` já está configurado** com o comando de start correto:
   ```toml
   [deploy]
   startCommand = "streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true"
   ```

5. **Aguarde o deploy** — o Railway detecta o `requirements.txt` e instala as dependências automaticamente.

6. **Primeiro acesso**: O banco de dados (tabelas) é criado automaticamente na primeira inicialização.

## Banco de Dados

O sistema usa **PostgreSQL**. A conexão é feita via variável de ambiente `DATABASE_URL`.

### Tabelas

- **materials**: Materiais (alumínio, cobre, ferro, etc.)
- **partners**: Parceiros (fornecedores e clientes)
- **transactions**: Transações (entradas e saídas)
- **prices**: Preços vigentes por material
- **canhotos**: Recibos de atendimento
- **canhoto_items**: Itens de cada canhoto

### Backup

Use o plugin nativo do Railway ou ferramentas padrão PostgreSQL:

```bash
# Exportar
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restaurar
psql $DATABASE_URL < backup_20260101.sql
```

## Segurança

- **Autenticação**: Sistema protegido por senha via variável de ambiente
- **Validações**: Validação de estoque antes de permitir saídas
- **Soft Delete**: Materiais e parceiros são desativados, não excluídos permanentemente
- **Parameterização SQL**: Todas as queries usam `%s` parametrizado (proteção contra SQL injection)

## Tecnologias Utilizadas

- **Python 3.8+**
- **Streamlit 1.32.0**: Framework web para aplicações de dados
- **PostgreSQL**: Banco de dados relacional
- **psycopg2-binary 2.9.9**: Driver PostgreSQL para Python
- **Pandas 2.2.0**: Manipulação e análise de dados
- **Python-dotenv 1.0.1**: Gerenciamento de variáveis de ambiente

## Problemas Comuns

**Erro: "APP_PASSWORD não configurado"**
- Solução: Defina a variável `APP_PASSWORD` nas variáveis de ambiente (Railway ou `.env` local)

**Erro de conexão com o banco**
- Verifique se `DATABASE_URL` está corretamente configurada
- No Railway: confirme que o plugin PostgreSQL está adicionado ao projeto

**Página não carrega**
- Verifique se todas as dependências estão instaladas: `pip install -r requirements.txt`

## Atualizações

```bash
git pull
pip install -r requirements.txt --upgrade
streamlit run app.py
```

---

**Versão**: 2.0.0 (PostgreSQL)
**Data**: Fevereiro 2026
