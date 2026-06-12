# Atividade Prática — Pipeline ETL com a API do Banco Mundial

## Visão geral

### O que o pipeline faz?

O pipeline coleta, trata e armazena dados socioeconômicos em um banco de dados PostgreSQL. Durante o processamento, os dados são limpos, padronizados e organizados para facilitar consultas, análises e a criação de dashboards.

### Qual API usa?

O projeto utiliza a API pública do Banco Mundial (World Bank Data API v2). Por meio dela, são obtidos dados de países e indicadores como PIB per capita, população total, gastos com saúde, gastos com educação e acesso à eletricidade.

### Qual problema resolve?

Dados socioeconômicos geralmente estão espalhados em diferentes formatos e nem sempre estão prontos para análise. Este pipeline automatiza a coleta e o tratamento dessas informações, disponibilizando dados atualizados e organizados para comparar países da América Latina, Europa e Ásia e apoiar análises sobre desenvolvimento econômico e social.


## Modelo de Dados

O pipeline utiliza a abordagem **SQLAlchemy Core** (`Table + MetaData`) para definir e manipular as estruturas do banco de dados.

A escolha pelo SQLAlchemy Core foi feita por oferecer uma implementação mais simples e direta para operações de carga em lote e upsert no PostgreSQL. Como o projeto exige a utilização de `on_conflict_do_update`, o Core permite construir instruções SQL de forma explícita, mantendo boa performance e reduzindo a complexidade da camada de persistência. Além disso, a execução em lote utilizando listas de dicionários torna o processo de carga mais eficiente para grandes volumes de registros.

### Estrutura das Tabelas

#### Tabela: countries

| Campo        | Tipo         | Restrição |
| ------------ | ------------ | --------- |
| iso2_code    | CHAR(2)      | PK        |
| iso3_code    | CHAR(3)      |           |
| name         | VARCHAR(100) | NOT NULL  |
| region       | VARCHAR(80)  |           |
| income_group | VARCHAR(60)  |           |
| capital      | VARCHAR(80)  |           |
| longitude    | NUMERIC(9,4) |           |
| latitude     | NUMERIC(9,4) |           |
| loaded_at    | TIMESTAMP    |           |

**Função:** armazenar os metadados dos países extraídos da API do Banco Mundial.

---

#### Tabela: indicators

| Campo          | Tipo        | Restrição |
| -------------- | ----------- | --------- |
| indicator_code | VARCHAR(40) | PK        |
| indicator_name | TEXT        | NOT NULL  |
| unit           | VARCHAR(30) |           |

**Função:** armazenar os indicadores socioeconômicos utilizados pelo pipeline.

---

#### Tabela: wdi_facts

| Campo          | Tipo          | Restrição |
| -------------- | ------------- | --------- |
| iso2_code      | CHAR(2)       | PK / FK   |
| indicator_code | VARCHAR(40)   | PK / FK   |
| year           | SMALLINT      | PK        |
| value          | NUMERIC(18,4) |           |
| loaded_at      | TIMESTAMP     |           |

**Chave Primária Composta:** `(iso2_code, indicator_code, year)`

**Chaves Estrangeiras:**

* `iso2_code → countries.iso2_code`
* `indicator_code → indicators.indicator_code`

**Função:** armazenar a série histórica dos indicadores para cada país e ano.

### Relacionamento entre as tabelas

countries (1) ──────< wdi_facts >────── (1) indicators

Cada país pode possuir diversos registros históricos na tabela `wdi_facts`, assim como cada indicador pode aparecer em diversos países e anos. A tabela `wdi_facts` atua como tabela fato, conectando as dimensões `countries` e `indicators`.

## Regras de Transformação

Durante a etapa de transformação, foram aplicadas regras para garantir que os dados estivessem limpos, organizados e sem inconsistências antes do carregamento no PostgreSQL.

### T1 — Filtro de Países

Foram removidos registros que não representam países reais. A API do Banco Mundial também retorna agrupamentos como continentes, regiões e blocos econômicos.

**Objetivo:** manter apenas dados de países para permitir comparações corretas entre eles.

### T2 — Limpeza e Padronização de Texto

Os campos de texto tiveram espaços extras removidos. Valores vazios foram convertidos para `None` e os nomes das regiões foram padronizados.

**Objetivo:** evitar diferenças de escrita que possam causar problemas em consultas e análises.

### T3 — Conversão de Tipos

Os dados foram convertidos para os tipos corretos. O campo `year` foi transformado em inteiro e os campos numéricos, como `value`, `latitude` e `longitude`, foram convertidos para decimal.

**Objetivo:** garantir compatibilidade com o PostgreSQL e evitar erros durante a carga dos dados.

### T4 — Filtro por Período

Foram mantidos apenas os registros entre 2010 e o ano atual.

**Objetivo:** reduzir o volume de dados e focar em informações mais recentes e relevantes.

### T5 — Remoção de Duplicidades

Os registros foram verificados para identificar duplicatas com base na combinação de país, indicador e ano. Quando havia repetição, apenas um registro era mantido.

**Objetivo:** evitar dados duplicados e garantir a integridade das informações armazenadas.

## Como Executar

### 1. Clonar o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd etl_worldbank
```

### 2. Configurar as variáveis de ambiente

Crie o arquivo `.env` a partir do modelo:

```bash
cp .env.example .env
```

Depois, preencha as informações de conexão com o PostgreSQL.

### 3. Iniciar o ambiente

Execute o Docker Compose para criar e iniciar os serviços:

```bash
docker compose up --build
```

### 4. Executar o pipeline

Inicie o processo ETL:

```bash
python src/main.py
```

Durante a execução, o pipeline:

* Coleta dados da API do Banco Mundial;
* Aplica as regras de transformação;
* Carrega os dados nas tabelas do PostgreSQL.

### 5. Validar os dados

Após a execução, utilize as consultas de validação para verificar:

* Quantidade de países carregados;
* Registros por indicador;
* Valores nulos;
* Integridade dos dados armazenados.

### 6. Validar a idempotência

Execute novamente o pipeline:

```bash
python src/main.py
```

Em seguida, confira a quantidade de registros:

```sql
SELECT COUNT(*) FROM wdi_facts;
```

Se o total permanecer o mesmo após novas execuções, o pipeline está funcionando de forma idempotente, sem gerar registros duplicados.

## Consultas de Validação

Após a execução do pipeline, foram realizadas consultas para verificar se os dados foram carregados corretamente no PostgreSQL.

### 1. Quantidade de países carregados

```sql
SELECT COUNT(*) FROM countries;
```

**Resultado:**

```text
215
```

**Verificação:** confirma que apenas países válidos foram carregados na tabela `countries`.

---

### 2. Países por grupo de renda

```sql
SELECT income_group, COUNT(*)
FROM countries
GROUP BY income_group
ORDER BY 2 DESC;
```

**Resultado:**

```text
Middle income | 104
High income   | 86
Low income    | 25
```

**Verificação:** confirma que os países foram classificados corretamente por grupo de renda.

---

### 3. Registros e valores nulos por indicador

```sql
SELECT indicator_code,
       COUNT(*) AS obs,
       SUM(CASE WHEN value IS NULL THEN 1 ELSE 0 END) AS nulls
FROM wdi_facts
GROUP BY indicator_code;
```

**Resultado:**

```text
EG.ELC.ACCS.ZS    | 2150 | 20
NY.GDP.PCAP.KD    | 2150 | 105
SE.XPD.TOTL.GD.ZS | 2150 | 843
SH.XPD.CHEX.GD.ZS | 2150 | 413
SP.POP.TOTL       | 2150 | 0
```

**Verificação:** confirma que os cinco indicadores foram carregados e que valores ausentes foram tratados sem interromper o processo.

---

### 4. Consulta da série histórica

```sql
SELECT c.name, f.year, f.value
FROM wdi_facts f
JOIN countries c ON c.iso2_code = f.iso2_code
WHERE f.indicator_code = 'NY.GDP.PCAP.KD'
  AND c.iso2_code IN ('BR','US','CN','DE','NG')
ORDER BY c.name, f.year;
```

**Resultado:** série histórica carregada corretamente para os países selecionados.

**Verificação:** confirma a integridade dos relacionamentos entre as tabelas e a carga correta dos indicadores.

---

### 5. Teste de idempotência

Após executar o pipeline novamente:

```sql
SELECT COUNT(*) FROM wdi_facts;
```

**Resultado:**

```text
10750
```

**Verificação:** a quantidade de registros permaneceu a mesma após a reexecução, comprovando que não houve duplicação de dados.

## Decisões Técnicas

### Uso do SQLAlchemy Core

Foi utilizado o SQLAlchemy Core (`Table` e `MetaData`) em vez do ORM. Essa abordagem simplifica operações em lote e facilita a implementação de upserts com `on_conflict_do_update`.

### Arquitetura Modular

O projeto foi dividido em módulos de extração, transformação, carga e orquestração. Essa separação deixa o código mais organizado, facilita a manutenção e permite evoluir cada etapa de forma independente.

### Retry na Extração

Foi implementado um mecanismo de retry com backoff para lidar com falhas temporárias de rede ou indisponibilidade da API. Isso torna o processo de coleta mais confiável.

### Deduplicação de Dados

Antes da carga, os registros passam por uma etapa de remoção de duplicidades. Essa estratégia evita conflitos no banco de dados e reduz processamento desnecessário.

### Integridade dos Dados

A carga é realizada na ordem `countries → indicators → wdi_facts`, garantindo que os relacionamentos entre as tabelas sejam respeitados.

### Configuração por Variáveis de Ambiente

As configurações da aplicação são armazenadas em variáveis de ambiente. Isso evita informações sensíveis no código-fonte e facilita a configuração em diferentes ambientes.
