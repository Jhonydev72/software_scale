# 🌱 SCALE - Cálculo de Emergia (APS Engenharia de Software)

Sistema inspirado no software SCALE (Marvuglia et al., 2013) para cálculo emergético utilizando inventários de ciclo de vida (LCI). Desenvolvido em Django para a disciplina de Atividades Práticas Supervisionadas do curso de Ciência da Computação.

## 📋 Funcionalidades

- Importação de dados LCI nos formatos **CSV** ou **Excel (XLSX)**
- Cálculo de emergia total (solar emjoules - sej) para produtos e serviços
- Interface web verde/branca (natureza/sustentabilidade)
- Banco de dados SQLite para armazenamento de processos, fluxos e fontes emergéticas
- API RESTful para integração com outros sistemas

## 🛠️ Tecnologias Utilizadas

- **Python 3.11+**
- **Django 5.x** (framework web)
- **SQLite** (banco de dados)
- **pandas** (manipulação de dados)
- **numpy** (cálculos matriciais)
- **HTML/CSS/JavaScript** (frontend)

## 📦 Pré-requisitos

Antes de começar, você precisa ter instalado:

- [Python 3.11 ou superior](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)
- [pip](https://pip.pypa.io/en/stable/installation/) (geralmente já vem com o Python)

## 🚀 Como executar o projeto

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/software_scale.git
cd software_scale

python -m venv venv
venv\Scripts\activate

3. Instale as dependências

bash

pip install -r requirements.txt


Se o arquivo requirements.txt não existir ainda, crie com o comando abaixo ou instale manualmente:

bash
pip install django pandas numpy openpyxl xlrd
pip freeze > requirements.txt



4. Execute as migrações do banco de dados
bash
python manage.py makemigrations
python manage.py migrate



5. Inicie o servidor
bash
python manage.py runserver


6. Acesse o sistema
Abra seu navegador e acesse: http://localhost:8000