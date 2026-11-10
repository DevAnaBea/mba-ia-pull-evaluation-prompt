# Pull, otimização e avaliação de prompts com LangChain e LangSmith

Este projeto implementa o desafio de obter um prompt do LangSmith Prompt Hub, otimizá-lo para converter relatos de bugs em User Stories, publicar a nova versão e avaliá-la com um dataset de 15 exemplos.

A avaliação usa cinco métricas: Helpfulness, Correctness, F1-Score, Clarity e Precision. O critério do desafio exige que cada métrica e a média geral sejam iguais ou superiores a 0.8.

## Tecnologias

- Python 3.10 ou superior (ambiente validado com Python 3.12)
- LangChain Core
- LangSmith Prompt Hub, datasets e avaliação
- Google Gemini ou OpenAI como provedor de LLM
- Prompts em YAML
- pytest

## Estrutura

```text
mba-ia-pull-evaluation-prompt/
├── .env.example                       Modelo das variáveis de ambiente
├── .gitignore                         Arquivos ignorados pelo Git
├── README.md                          Documentação do projeto
├── requirements.txt                   Dependências Python
├── datasets/
│   └── bug_to_user_story.jsonl        Dataset de avaliação com 15 exemplos
├── prompts/
│   ├── bug_to_user_story_v1.yml       Prompt semente obtido do Hub
│   └── bug_to_user_story_v2.yml       Prompt otimizado
├── src/
│   ├── evaluate.py                    Execução de experimentos e cálculo das métricas
│   ├── metrics.py                     Avaliadores LLM-as-Judge
│   ├── pull_prompts.py                Pull do prompt semente
│   ├── push_prompts.py                Validação e publicação do v2
│   └── utils.py                       Configuração de modelos e utilitários
└── tests/
    ├── test_prompts.py                Validação dos requisitos do prompt
    └── test_scripts.py                Testes locais de scripts e configuração Gemini
```

## Requisitos

- Python 3.10 ou superior
- Uma conta LangSmith e uma API key para pull, push e avaliação remotos
- Uma API key do Google AI Studio para usar Gemini, ou uma API key OpenAI se optar por esse provedor
- Conexão com a internet para acessar os serviços

Não compartilhe suas chaves. O arquivo `.env` é ignorado pelo Git; nunca o adicione a commits.

## 1. Obter o projeto

Se ainda não tiver o repositório:

```powershell
git clone https://github.com/DevAnaBea/mba-ia-pull-evaluation-prompt.git
Set-Location .\mba-ia-pull-evaluation-prompt
```

Se o projeto já estiver no computador, entre na pasta correspondente.

## 2. Criar e ativar o ambiente virtual

### Windows PowerShell

```powershell
py -3.12 -m venv .\venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

O comando `Set-ExecutionPolicy` vale somente para a sessão atual do PowerShell. Também é possível executar os comandos usando `.\venv\Scripts\python.exe` sem ativar o ambiente.

### Linux ou macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Instalar as dependências

Com o ambiente virtual ativado:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 4. Configurar o ambiente

Crie o `.env` a partir do modelo:

### Windows PowerShell

```powershell
Copy-Item .env.example .env
notepad .env
```

### Linux ou macOS

```bash
cp .env.example .env
```

Preencha no `.env` as variáveis necessárias:

```env
LANGSMITH_API_KEY=sua_chave_langsmith
LANGSMITH_PROJECT=mba-ia-pull-evaluation-prompt
USERNAME_LANGSMITH_HUB=dev-anabea

LLM_PROVIDER=google
GOOGLE_API_KEY=sua_chave_google
LLM_MODEL=gemini-3.8-flash
EVAL_MODEL=gemini-3.8-flash
```

Os modelos são configurados somente no `.env`, não no `.env.example`. `LLM_MODEL` gera as respostas e `EVAL_MODEL` avalia as respostas; ambos podem usar o mesmo modelo. O handle público configurado para este projeto é `dev-anabea`.

Para usar OpenAI, configure `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, `LLM_MODEL` e `EVAL_MODEL` com modelos disponíveis na sua conta.

Este código omite `temperature` nos modelos Gemini 3.6 e posteriores, pois as versões atuais da API não devem receber os parâmetros de amostragem `temperature`, `top_p` e `top_k`. Consulte a documentação oficial antes de trocar o modelo:

- [Modelos Gemini](https://ai.google.dev/gemini-api/docs/models)
- [Preços e limites do Gemini](https://ai.google.dev/gemini-api/docs/pricing)
- [Modelos OpenAI](https://platform.openai.com/docs/models)

As cotas gratuitas variam por modelo, projeto e período. Confira o uso atual em [ai.dev/rate-limit](https://ai.dev/rate-limit). Um erro `429 RESOURCE_EXHAUSTED` significa que a cota aplicável foi atingida; aguarde a renovação indicada pela API ou consulte as opções de plano.

No PowerShell, caso o terminal não aceite os caracteres Unicode dos scripts, habilite UTF-8 antes de executá-los:

```powershell
$env:PYTHONUTF8 = "1"
```

## 5. Fazer pull do prompt semente

O prompt de origem do desafio é `leonanluppi/bug_to_user_story_v1`. Para baixá-lo para `prompts/bug_to_user_story_v1.yml`, execute:

```powershell
python .\src\pull_prompts.py
```

O pull usa `dangerously_pull_public_prompt=True`, conforme exigido pelo LangSmith para identificadores públicos com o formato `owner/nome`.

## 6. Otimizar o prompt

O prompt otimizado está em `prompts/bug_to_user_story_v2.yml`. Ele recebe `{bug_report}` na mensagem User e mantém as instruções fixas na mensagem System.

Técnicas aplicadas:

- **Role Prompting:** define a persona de Product Manager e o público da User Story (desenvolvedores e QAs).
- **Few-shot Learning:** apresenta três pares de relato/resposta com diferentes níveis de detalhe.
- **Skeleton of Thought:** orienta uma estrutura com User Story e critérios de aceitação, usando seções adicionais somente quando justificadas pelo relato.

As instruções também pedem para preservar os fatos, evitar inventar detalhes e marcar lacunas importantes em vez de presumir informações.

## 7. Executar os testes

No ambiente virtual:

```powershell
python -m pytest tests/test_prompts.py tests/test_scripts.py -q
```

Os testes validam a estrutura do YAML, a persona, o formato, os exemplos Few-shot, os metadados, a variável `{bug_report}`, a conversão do prompt obtido no pull e a compatibilidade dos parâmetros Gemini. Eles não fazem chamadas de geração ao Gemini ou ao LangSmith.

## 8. Publicar o prompt otimizado

O push valida o prompt e publica uma versão pública no Hub:

```powershell
python .\src\push_prompts.py
```

O identificador publicado é `{USERNAME_LANGSMITH_HUB}/bug_to_user_story_v2`. A publicação deste projeto pode ser consultada em:

[dev-anabea/bug_to_user_story_v2 no LangSmith](https://smith.langchain.com/prompts/bug_to_user_story_v2/5d74d49e?organizationId=4807bd3b-eed8-4f56-ae2c-d538f2d9e915)

## 9. Executar a avaliação

Depois de publicar o prompt e confirmar que há cota disponível:

```powershell
python .\src\evaluate.py
```

O script cria ou reutiliza o dataset LangSmith `<LANGSMITH_PROJECT>-eval`, executa o prompt nos 15 exemplos, grava os feedbacks e apresenta as médias de Helpfulness, Correctness, F1-Score, Clarity e Precision. Helpfulness é calculada como a média de Clarity e Precision; Correctness, como a média de F1-Score e Precision.

Cada exemplo requer uma chamada do modelo para gerar a resposta e chamadas adicionais dos avaliadores. Como F1-Score, Clarity e Precision usam avaliadores LLM, uma avaliação completa pode consumir aproximadamente 60 chamadas de geração no provedor: 15 respostas e 45 avaliações. Retentativas ou erros de serviço podem alterar esse total. Verifique a cota antes de executar.

## Autoria

Ana Beatriz Thomaz  
MBA em Engenharia de Software com IA — Full Cycle  
[DevAnaBea](https://github.com/DevAnaBea)
