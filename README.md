# Sistema de Controle de Sucata

Sistema web profissional e completo para gerenciamento de sucatas, desenvolvido com **Streamlit** e **SQLite**.

## Funcionalidades

- **Dashboard**: Visão geral do negócio com métricas mensais e resumos
- **Entradas**: Registro de compras de materiais de fornecedores
- **Saídas**: Registro de vendas com validação de estoque
- **Estoque**: Consulta de estoque atual e valores estimados
- **Cadastros**: Gerenciamento de materiais e parceiros (fornecedores/clientes)
- **Relatórios**: Análises detalhadas com filtros e exportação CSV
- **Login Simples**: Proteção por senha configurável

## Estrutura do Projeto

```
Sucata/
├── app.py                      # Aplicação principal com autenticação
├── db.py                       # Gerenciamento do banco SQLite
├── services.py                 # Lógica de negócio
├── requirements.txt            # Dependências Python
├── .env.example               # Exemplo de configuração
├── .env                       # Configuração (criar a partir do .env.example)
├── data.db                    # Banco de dados SQLite (criado automaticamente)
├── pages/
│   ├── 1_📊_Dashboard.py
│   ├── 2_📥_Entradas.py
│   ├── 3_📤_Saídas.py
│   ├── 4_📦_Estoque.py
│   ├── 5_📝_Cadastros.py
│   └── 6_📈_Relatórios.py
└── README.md
```

## Instalação e Execução Local

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Passo a Passo

1. **Clone o repositório** (ou baixe os arquivos):

```bash
git clone <url-do-repositorio>
cd Sucata
```

2. **Crie um ambiente virtual** (recomendado):

```bash
# No Windows
python -m venv venv
venv\Scripts\activate

# No Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Instale as dependências**:

```bash
pip install -r requirements.txt
```

4. **Configure o arquivo .env**:

```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite o arquivo .env e defina sua senha
# No Windows, use: copy .env.example .env
```

Edite o arquivo `.env` e configure:

```env
APP_NAME=Sistema de Controle de Sucata
APP_PASSWORD=suasenhaforteaqui
```

5. **Execute a aplicação**:

```bash
streamlit run app.py
```

6. **Acesse no navegador**:

A aplicação abrirá automaticamente em `http://localhost:8501`

## Uso do Sistema

### Primeiro Acesso

1. Faça login com a senha configurada no `.env`
2. Vá para **Cadastros** e adicione:
   - Materiais (ex: Alumínio, Cobre, Ferro)
   - Parceiros (fornecedores e clientes)
3. Comece a registrar **Entradas** (compras) e **Saídas** (vendas)
4. Acompanhe o negócio pelo **Dashboard** e **Relatórios**

### Fluxo de Trabalho Recomendado

1. **Cadastro inicial**: Configure materiais e parceiros
2. **Registro de entradas**: Registre as compras de material
3. **Controle de estoque**: Monitore os níveis de estoque
4. **Registro de saídas**: Registre as vendas (o sistema valida o estoque)
5. **Análise**: Use o Dashboard e Relatórios para tomar decisões

## Deploy no Railway

### Preparação

1. Crie uma conta em [railway.app](https://railway.app)
2. Certifique-se de que todos os arquivos estão commitados no Git

### Deploy via GitHub

1. **Conecte seu repositório**:
   - Faça login no Railway
   - Clique em "New Project"
   - Selecione "Deploy from GitHub repo"
   - Escolha o repositório do projeto

2. **Configure as variáveis de ambiente**:
   - No painel do Railway, vá em "Variables"
   - Adicione:
     ```
     APP_NAME=Sistema de Controle de Sucata
     APP_PASSWORD=suasenhaforteaqui
     ```

3. **Aguarde o deploy**:
   - O Railway detectará automaticamente o `requirements.txt`
   - O build será feito automaticamente

4. **Configure o comando de inicialização**:
   - Em "Settings", adicione o comando:
     ```
     streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
     ```

5. **Acesse sua aplicação**:
   - O Railway fornecerá uma URL pública
   - Acesse e faça login com sua senha

### Deploy via Railway CLI

```bash
# Instale o Railway CLI
npm i -g @railway/cli

# Faça login
railway login

# Inicialize o projeto
railway init

# Configure as variáveis
railway variables set APP_PASSWORD=suasenhaaqui

# Deploy
railway up
```

## Banco de Dados

O sistema usa **SQLite** (arquivo `data.db`) que é criado automaticamente ao iniciar a aplicação.

### Tabelas

- **materials**: Materiais (alumínio, cobre, etc.)
- **partners**: Parceiros (fornecedores e clientes)
- **transactions**: Transações (entradas e saídas)

### Backup

Para fazer backup, basta copiar o arquivo `data.db`:

```bash
# Criar backup
cp data.db backup_data_$(date +%Y%m%d).db

# Restaurar backup
cp backup_data_20240101.db data.db
```

## Segurança

- **Autenticação**: Sistema protegido por senha
- **Validações**: Validação de estoque antes de permitir saídas
- **Soft Delete**: Materiais e parceiros são desativados, não excluídos
- **Dados locais**: Banco SQLite mantido localmente (ou no servidor de deploy)

## Tecnologias Utilizadas

- **Python 3.8+**
- **Streamlit 1.32.0**: Framework web para aplicações de dados
- **SQLite**: Banco de dados embutido
- **Pandas 2.2.0**: Manipulação e análise de dados
- **Python-dotenv 1.0.1**: Gerenciamento de variáveis de ambiente

## Suporte e Manutenção

### Problemas Comuns

**Erro ao iniciar: "APP_PASSWORD não configurado"**
- Solução: Copie `.env.example` para `.env` e defina uma senha

**Banco de dados não encontrado**
- Solução: O banco é criado automaticamente ao iniciar. Verifique permissões de escrita

**Página não carrega**
- Solução: Verifique se todas as dependências estão instaladas com `pip install -r requirements.txt`

### Atualizações

Para atualizar o sistema:

```bash
# Atualize o código
git pull

# Atualize as dependências
pip install -r requirements.txt --upgrade

# Reinicie a aplicação
streamlit run app.py
```

## Licença

Este projeto foi desenvolvido para uso pessoal/comercial.

## Autor

Sistema desenvolvido para controle de sucata.

---

**Versão**: 1.0.0
**Data**: Janeiro 2026
