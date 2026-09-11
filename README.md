# Agente de Matrículas com IA

Serviço em Python que atende candidatos a cursos por chat: consulta a oferta,
verifica vagas em tempo real e registra pré-inscrições.

---

## Nota para o time técnico da UniScale

Este repositório não é um projeto de portfólio maduro, e a transparência sobre
como ele foi feito importa mais que o código em si.

### O código foi escrito por IA

Não por mim. Usei o Claude como ferramenta de desenvolvimento, e o que está
aqui saiu dele. Eu não teria escrito este código sozinho, nem nesta velocidade.

Digo isso logo no início porque a alternativa — deixar parecer que escrevi —
seria desonesto e não resistiria a cinco minutos de conversa.

### O que foi meu

**Definição do problema e do domínio.** Escolher o que construir, e por que um
agente de matrículas fazia mais sentido aqui do que outra coisa.

**Parte das decisões de arquitetura.** O padrão central deste projeto — regras
de negócio como funções SQL, com o modelo interpretando intenção mas nunca
calculando — vem de um sistema anterior que construí em n8n, um agente de
reservas hoteleiras. O mesmo vale para o tratamento de concorrência com trava
de linha e para a disciplina de medir custo por requisição contra o que a API
efetivamente reporta. Trouxe esses padrões; a IA os implementou em Python.

Outras decisões partiram da IA e eu avaliei e aceitei — escrever o laço do
agente à mão em vez de usar o executor automático do SDK, por exemplo.

**Execução, depuração e validação.** Rodar, quebrar, ler o erro, decidir o que
fazer. Levou dois dias e travou várias vezes: conflito de dependências, formato
errado da string de conexão do pooler, um campo de exemplo do Swagger
derrubando a normalização do histórico, indisponibilidade temporária da API do
modelo. Esse trabalho foi meu, com a IA ajudando no diagnóstico.

**Entendimento.** Estudei o que foi gerado. Não entrou linha que eu não
conseguisse acompanhar.

### O que eu não afirmo

Não domino Python. Não conheço em profundidade as bibliotecas usadas aqui.
Não escreveria este código do zero sem apoio.

### O que eu afirmo

Entendo o que cada parte faz e por que está assim. Consigo explicar as decisões
de arquitetura, defender as que tomei e apontar as que faria diferente.

Se a leitura do código sugerir mais domínio do que descrevi acima, a descrição
acima é a que vale.

### Por que mostro isso mesmo assim

A vaga pede Python e orquestração de agentes em código, e pede também uso
crítico de ferramentas de desenvolvimento assistido por IA. Achei mais útil
mostrar um resultado real com a autoria declarada do que dizer que aprenderia
depois. O que está em jogo aqui não é minha capacidade de digitar Python — é
se eu sei decidir o que construir, dirigir a construção e entender o que saiu
dela.

---

## O que o sistema faz

Um candidato conversa por uma API. O agente entende a intenção, consulta o
banco da instituição e age:

- busca cursos por área ou palavra-chave
- verifica turmas, prazo de inscrição e vagas disponíveis
- registra a pré-inscrição, validando as regras antes de gravar

## Arquitetura

```
candidato → API (FastAPI) → laço do agente → ferramentas → PostgreSQL
```

| Camada | Responsabilidade |
|---|---|
| FastAPI | Contrato de entrada e saída, validação, autenticação |
| Agente | Laço de chamada de função, escrito explicitamente |
| Ferramentas | Ponte entre o modelo e o banco |
| PostgreSQL | Regras de negócio como funções SQL |

## Decisões de arquitetura

### 1. A regra de negócio vive no banco, não no prompt

Disponibilidade de vaga, prazo de inscrição e atomicidade da gravação são
funções SQL versionadas. O modelo interpreta a intenção do candidato e escolhe
a ferramenta certa, mas **nunca decide se há vaga** — ele consulta e obedece à
resposta.

A consequência prática é que o sistema é auditável: dá para explicar por que
uma inscrição foi aceita ou recusada sem depender do texto que o modelo gerou.

Este é o padrão que trouxe do sistema anterior, e é a decisão de que tenho mais
convicção neste projeto.

### 2. Vagas são calculadas, nunca guardadas

Não existe coluna `vagas_ocupadas`. O número sai da contagem real de
inscrições, toda vez. Contador guardado é fonte clássica de dessincronia.

### 3. Concorrência tratada no banco

`criar_pre_inscricao()` usa `for update` para travar a linha da turma durante a
transação. Duas inscrições simultâneas na última vaga são serializadas: a
segunda recebe `sem_vagas`, não uma vaga inexistente.

Há ainda uma restrição de unicidade por turma e e-mail, que impede inscrição
duplicada mesmo que a aplicação tenha bug.

### 4. O laço do agente é explícito

O SDK do Gemini executa funções automaticamente. Essa opção foi desligada
(`automatic_function_calling=disable=True`) para manter o laço no código, com
limite de turnos, contagem de tokens por volta e tratamento de erro visíveis.

Foi sugestão da IA, e aceitei pelo motivo apontado: entender o mecanismo vale
mais, aqui, do que usar a abstração pronta em cima dele.

### 5. Erro de ferramenta não derruba a requisição

O executor de ferramentas captura exceções e devolve o erro como resultado.
O modelo lê aquilo e se recupera. Durante a implementação o banco ficou
indisponível por alguns minutos, e o agente respondeu ao candidato que estava
com instabilidade técnica em vez de estourar um erro 500 — o comportamento
pretendido, confirmado por acidente.

### 6. Custo medido, mesmo sendo gratuito

Cada resposta retorna tokens consumidos e o custo equivalente em dólares,
calculado a partir do `usage_metadata` reportado pela API. No nível gratuito do
Gemini o valor cobrado é zero; o número responde "quanto isso custaria fora do
gratuito", que é a pergunta antes de escalar.

O campo se chama `custo_equivalente_usd` justamente para não sugerir cobrança
que não existe.

## Stack

Python 3.12+ · FastAPI · Pydantic · psycopg 3 · PostgreSQL (Supabase) ·
Google Gemini (flash-lite) · Docker · GitHub Actions

## Rodando localmente

```bash
python -m venv .venv
# Windows:    .venv\Scripts\Activate.ps1
# Mac/Linux:  source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env    # preencher as variáveis
uvicorn app.main:app --reload
```

Esquema do banco em `sql/schema.sql`, dados de exemplo em `sql/seed.sql`.
Documentação interativa em `/docs`.

Há também um `diagnostico.py` que testa cada camada isoladamente — variáveis,
banco, ferramentas, API do modelo e laço completo. Ele existe porque, durante a
implementação, um erro 500 genérico não dizia qual peça havia falhado.

## Testes

```bash
pytest -v
```

Cobrem o que é determinístico: contrato da API, autenticação, validação de
entrada, cálculo de custo e consistência entre ferramentas declaradas e
implementadas.

A qualidade das respostas do modelo **não** é testada por asserção. Para isso
seria necessário um conjunto de referência com respostas revisadas e medição de
taxa de concordância a cada mudança de prompt.

## Limitações conhecidas

- Não há persistência de conversa: o histórico trafega na requisição
- A busca de cursos é textual, não semântica — sem RAG
- Autenticação é uma chave estática única, sem escopo nem expiração
- Sem limite de requisições por cliente
- Uma falha da API do modelo resulta em erro 500, sem retentativa própria
- O nível gratuito do Gemini limita a 15 requisições por minuto
- A pré-inscrição não dispara notificação nem integra com CRM
- Sem observabilidade além de log estruturado em texto
- Dependências com versão mínima, não travada

## O que eu faria diferente com mais tempo

- Retentativa com espera crescente para erros 5xx e 429 do provedor
- Resposta de fallback quando o modelo está indisponível, em vez de 500
- Persistência da conversa, com identificador de sessão
- Conjunto de casos de referência para medir qualidade das respostas
- Versões travadas das dependências, geradas a partir do que foi instalado

---

## Contexto

Construído em 9 e 10 de setembro de 2026, para a conversa com o time técnico da
UniScale. Os dados são fictícios e a instituição é hipotética — o domínio foi
escolhido por proximidade com o que a UniScale faz.

Rodrigo Teixeira Ferreira
