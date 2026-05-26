
# 🌱 SCALE — Software for CALculating Emergy based on Life Cycle Inventories

O **SCALE** é uma aplicação web robusta desenvolvida em Django, inspirada na metodologia científica proposta por Marvuglia et al. (2013) no artigo *"SCALE: Software for CALculating Emergy based on life cycle inventories"*. Este projeto foi concebido e refinado como parte prática das Atividades Práticas Supervisionadas (APS) para a disciplina de Engenharia de Software do curso de Ciência da Computação da UNIP (Campus Marquês).

O objetivo principal do sistema é processar matrizes complexas de Inventários do Ciclo de Vida (LCI) planos, modelá-las utilizando conceitos avançados de Teoria dos Grafos e realizar cálculos emergéticos rigorosos em Solar Emjoules (sej) de forma automatizada, replicável e escalável.

---

## 🚀 Funcionalidades Principais

* **Módulo de Importação LCI Inteligente**: Área de upload moderna e intuitiva com suporte a *Drag and Drop* (arrastar e soltar arquivos) e seletor tradicional. Aceita planilhas Excel (`.xlsx`, `.xls`) de aba única e arquivos `.csv` estruturados.
* **Persistência de Dados Estruturada (SQLite)**: Arquitetura modificada para suportar múltiplos carregamentos históricos. Cada planilha importada gera um registro exclusivo de `Inventory`, permitindo alternar entre diferentes ecossistemas analíticos sem perda de dados antigos.
* **Motor de Cálculo Recursivo Otimizado (Pandas)**: Algoritmo de busca em grafos (*graph search*) implementado em memória RAM via DataFrames do Pandas. Possui mecanismos de proteção contra loops infinitos (`visited sets`) causados por retroalimentações (*feedbacks*) nas cadeias produtivas upstream e elimina o gargalo de consultas repetitivas ao banco de dados (N+1 queries).
* **Dashboard Analítico de Alta Resolução**: Painel interativo integrado às views do Django que consome a biblioteca `Matplotlib` em modo *headless* (`Agg`). Gera dinamicamente gráficos de Barras (Top Processos Upstream) e Linhas (Curva de Transformidades UEV) renderizados diretamente em strings Base64 de alta densidade de pixels (DPI 200).
* **Modo de Visualização em Tela Cheia (Zoom)**: Interface front-end enriquecida com modais fluidos em Tailwind CSS. Permite que o usuário clique em qualquer gráfico para ampliá-lo em tela cheia sobre um fundo com efeito de desfoque (*backdrop-blur*). Os gráficos possuem fundo branco sólido garantindo contraste absoluto e legibilidade perfeita das fontes durante o zoom.
* **UI/UX Dinâmica e Minimalista**: Menu lateral totalmente retrátil (*sidebar toggle*) controlado via JavaScript vanilla para otimizar o espaço útil da tela de trabalho, além de sistema assíncrono de alternância de abas sem recarregamento de página.

---

## 🛠️ Tecnologias e Dependências

As principais bibliotecas e frameworks mapeados no ecossistema do projeto são:

* **Django==5.2.14**: Framework web principal responsável pelo roteamento, views e ORM relacional.
* **Pandas==3.0.2** e **Numpy==2.4.4**: Motores matemáticos utilizados na estruturação, filtragem rápida e cálculo matricial recursivo das propriedades das fontes e fluxos.
* **Matplotlib==3.10.9**: Geração assíncrona de gráficos estatísticos customizados.
* **Openpyxl==3.1.5** e **Xlrd==2.0.2**: Leitores e interpretadores de arquivos de planilhas eletrônicas.

---

## 💻 Configuração do Ambiente Local e Execução

Siga os passos abaixo para configurar o ambiente virtual, instalar as dependências e rodar o projeto localmente no seu computador através do terminal (CMD, PowerShell ou Bash).

### 1. Clonar o Repositório e Navegar
Abra o seu terminal, clone o repositório da sua branch de desenvolvimento e acesse o diretório do projeto:

```bash
git clone https://github.com/Jhonydev72/software_scale.git
cd software_scale

```

### 2. Criar o Ambiente Virtual (venv)

Crie um ambiente virtual isolado para garantir que as dependências do SCALE não entrem em conflito com outros pacotes do seu sistema operacional:

```bash
python -m venv venv

```

### 3. Ativar o Ambiente Virtual

Ative o ambiente virtual criado de acordo com o seu sistema operacional:

* **Windows (PowerShell):**

```powershell
.\venv\Scripts\Activate.ps1

```

* **Windows (CMD):**

```cmd
.\venv\Scripts\activate.bat

```

* **Linux / macOS:**

```bash
source venv/bin/activate

```

*Nota: Você saberá que o ambiente está ativo quando o prefixo `(venv)` aparecer antes do caminho da linha de comando.*

### 4. Instalar as Dependências

Com a venv ativa, instale todos os pacotes necessários mapeados no arquivo de requerimentos:

```bash
pip install -r requirements.txt

```

### 5. Executar as Migrações do Banco de Dados

Gere a estrutura das tabelas relacionais (`Inventory`, `Process`, `Flow`, `EmergySource`) no banco SQLite local:

```bash
python manage.py makemigrations
python manage.py migrate

```

### 6. Inicializar o Servidor de Desenvolvimento

Inicie o servidor local do Django:

```bash
python manage.py runserver

```

Abra o seu navegador de preferência e acesse o endereço gerado: `http://127.0.0.1:8000/`

---

## 📖 Fluxo de Utilização do Sistema

1. **Baixar a Planilha Modelo**: Acesse a aba "Planilha Exemplo" ou use o link direto na tela de upload para descarregar o arquivo de template `Planilha_Calculos_Emergeticos.xlsx`. Ela contém as colunas normalizadas e exatas que o leitor de dados do Pandas espera receber.
2. **Importar o Inventário (LCI)**: Na aba inicial, arraste o arquivo preenchido para dentro da área pontilhada ou clique para selecionar. Clique em **Importar**. O sistema exibirá uma mensagem de sucesso indicando a quantidade de processos cadastrados no banco.
3. **Calcular a Emergia de um Processo**: No card inferior esquerdo, insira o ID de um processo cadastrado na planilha (por exemplo, `200` para o cenário de Etanol ou `900` para o Milho) e clique em **Calcular Emergia**. O motor do `emergy_calculator.py` executará o cálculo e trará o valor exato formatado em notação científica (ex: 2.45 x 10^11 sej).
4. **Análise Gráfica no Dashboard**: Navegue até a aba **Dashboard** no menu lateral. O componente de seleção (`<select>`) listará automaticamente o inventário que você acabou de carregar. Selecione-o e clique em **Gerar Gráficos**. Os gráficos de Barras e Linhas serão renderizados instantaneamente em alta qualidade. Clique sobre qualquer um deles para expandir e analisar os dados detalhadamente em tela cheia.

---

## 👥 Desenvolvimento e Colaboração

O projeto adota boas práticas de Engenharia de Software baseadas em branches de desenvolvimento específicas e Pull Requests para a ramificação principal (`main`), garantindo a estabilidade contínua do código estável utilizado para a validação acadêmica.

```

```
