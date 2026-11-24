# Planejamento do projeto

## 1. Objetivo

Criar um aplicativo local para selecionar um modelo de IA, enviar uma sentença e visualizar as entidades e relações que o modelo extraiu em um grafo.

Exemplo de entrada: `Albert Einstein é um físico alemão.`

O programa deve representar o que foi dito na sentença, sem inventar fatos adicionais. Uma representação possível é:

- Entidades: `Albert Einstein` (pessoa), `físico` (profissão), `alemão` (nacionalidade).
- Relações: `Albert Einstein — tem profissão → físico`; `Albert Einstein — tem nacionalidade → alemão`.

Os nomes dos tipos e das relações devem ser padronizados no aplicativo. “É” pode aparecer como rótulo legível, mas relações explícitas como `tem_profissao` e `tem_nacionalidade` produzem grafos mais claros e consistentes.

## 2. Decisões recomendadas para o MVP

### Interface e aplicação

Começar com **Python** para a aplicação inteira: interface, chamada ao motor de inferência, validação e preparação dos dados do grafo. Para uma interface desktop, **PySide6 (Qt)** é uma opção adequada e permite desenhar o grafo com `QGraphicsView`/`QGraphicsScene`. Uma alternativa é usar uma biblioteca de grafo dedicada, como NetworkX para os dados e uma visualização Qt ou web embutida para a tela.

Não criar inicialmente um backend próprio em C++ ou Rust. O trabalho de inferência pesada já fica com o Ollama, que fornece a API local; Python pode falar com ela por HTTP. Um backend nativo só deve ser considerado se medições mostrarem um gargalo específico ou surgir uma necessidade concreta de distribuição/integração.

### Execução dos modelos

Usar **Ollama como primeiro adaptador de modelos**. A API local permite listar modelos instalados (`GET /api/tags`) e enviar conversas (`POST /api/chat`). O aplicativo pode atualizar o seletor consultando essa API e mostrar uma mensagem útil se o serviço não estiver instalado ou iniciado.

Para o MVP, o fluxo recomendado é instalar o Ollama e baixar modelos por ele. A ideia de “jogar qualquer arquivo em uma pasta e detectar automaticamente” tem limites: arquivos GGUF precisam ser compatíveis com o runtime e o Ollama pede um `Modelfile` e um comando de criação para importar um GGUF. Portanto, planejar a pasta própria do aplicativo como uma melhoria: observar a pasta, reconhecer arquivos `.gguf`, mostrar o que foi encontrado e oferecer **Importar/Registrar**. Só depois de validar o modelo gerar o `Modelfile` e registrá-lo no Ollama. Não tratar um arquivo encontrado como necessariamente utilizável.

Uma alternativa para uma fase posterior é integrar diretamente com **llama.cpp/llama-server**: ele lê GGUF, tem API HTTP compatível com OpenAI e aceita resposta JSON restringida por schema. A aplicação poderia iniciar um servidor por modelo. Isso dá controle maior sobre a pasta de modelos, mas aumenta o trabalho de empacotar binários, configurar CPU/GPU, iniciar/parar processos e lidar com diferenças entre plataformas. Manter um contrato interno de adaptador de inferência permite trocar ou adicionar esse motor sem reescrever a interface.

### Extração confiável

Definir um contrato de dados versionado e usar um schema Pydantic como fonte da verdade. Enviar o JSON Schema à API Ollama (`format`) e validar a resposta novamente em Python. A documentação do Ollama recomenda schemas e validação com Pydantic para saídas estruturadas. Um prompt deve explicar as definições semânticas e instruir o modelo a incluir somente informação afirmada ou implicada diretamente na sentença.

Isso **não exige treinamento ou fine-tuning** no início. Use instrução clara, schema, exemplos pequenos (few-shot, se necessário), temperatura baixa e validação. O schema garante forma, não verdade: modelos ainda podem atribuir tipos errados, omitir itens ou extrair relações incorretas. Exiba os resultados para inspeção e permita corrigir/reprocessar. Se testes com dados representativos mostrarem erros sistemáticos que prompt e validação não resolvem, então estudar fine-tuning ou um extrator especializado.

## 3. Contrato inicial para os dados

Formato conceitual (ajustável antes da implementação):

```json
{
  "schema_version": "1.0",
  "entities": [
    {"id": "e1", "text": "Albert Einstein", "type": "PESSOA"},
    {"id": "e2", "text": "físico", "type": "PROFISSAO"},
    {"id": "e3", "text": "alemão", "type": "NACIONALIDADE"}
  ],
  "relations": [
    {"source": "e1", "label": "TEM_PROFISSAO", "target": "e2"},
    {"source": "e1", "label": "TEM_NACIONALIDADE", "target": "e3"}
  ]
}
```

Regras iniciais:

1. `id` é único na resposta; toda relação aponta para entidades existentes.
2. `text` preserva o trecho reconhecível da sentença; a normalização visual não deve apagar o original.
3. `type` e `label` usam um vocabulário controlado definido pela aplicação, com opção `OUTRO` e rótulo textual quando necessário.
4. Relações são direcionadas: `source — label → target`. A tela pode oferecer layout e orientação diferentes sem alterar os dados.
5. Campos opcionais futuros: offsets de início/fim, evidência textual da relação e confiança. Não usar confiança como garantia de correção.
6. Caso a sentença não contenha entidades/relações relevantes, retornar listas vazias, não completar com conhecimento externo.

## 4. Arquitetura proposta

```text
Interface PySide6
  ├── seletor de modelo e botão Atualizar
  ├── campo de texto e botão Extrair
  ├── estado de carregamento/erro
  ├── painel de entidades e relações
  └── visualização do grafo
          │
          ▼
Camada de aplicação (Python)
  ├── serviço de extração
  ├── schema Pydantic + validação semântica
  ├── adaptador Ollama (HTTP local)
  └── conversão para nós/arestas da visualização
          │
          ▼
Ollama local → modelo instalado
```

Separar a UI da inferência por interfaces simples, por exemplo `ModelProvider.list_models()` e `ModelProvider.extract(text, model)`. Assim, uma implementação futura com llama.cpp pode substituir o adaptador sem acoplar a tela ao motor.

## 5. Ordem de implementação

### Etapa 1 — validar o ambiente e a extração

- Registrar sistema operacional, RAM, GPU/VRAM e espaço em disco disponíveis.
- Instalar Ollama e baixar um modelo instruct pequeno que caiba no equipamento.
- Fazer uma chamada de teste por HTTP, sem interface.
- Escolher a primeira lista de tipos e relações e fixar o schema `1.0`.
- Montar um conjunto manual de sentenças em português, incluindo sujeito composto, negação, ambiguidade, sentença sem relações e entradas longas.

**Saída:** prova de conceito que recebe texto e retorna JSON validado.

### Etapa 2 — serviço e tratamento de falhas

- Implementar adaptador HTTP para Ollama.
- Buscar modelos disponíveis na inicialização e ao clicar em Atualizar.
- Tratar Ollama indisponível, lista vazia, modelo removido, timeout, resposta malformada e erro de validação.
- Não bloquear a thread da interface durante inferência.

**Saída:** função de extração independente da UI, com erros apresentáveis.

### Etapa 3 — interface mínima

- Janela PySide6 com seletor de modelo, campo de entrada, botão Extrair e botão Atualizar.
- Apresentar carregamento e erros compreensíveis.
- Mostrar primeiro entidades e relações em tabelas/listas para depurar o contrato.

**Saída:** fluxo funcional de ponta a ponta, mesmo antes do grafo.

### Etapa 4 — visualização do grafo

- Converter entidades em nós e relações em arestas direcionadas.
- Exibir rótulo e tipo no nó e predicado na aresta.
- Adicionar zoom, pan e um layout legível; oferecer painel textual acessível como alternativa.
- Testar grafo vazio, uma entidade, várias relações e rótulos longos.

**Saída:** estrutura retornada pela IA renderizada na janela.

### Etapa 5 — importação e descoberta de modelos

- Começar com a listagem de modelos que Ollama já conhece.
- Criar uma pasta de modelos configurável e detectar arquivos GGUF adicionados.
- Mostrar estado “encontrado”, “compatível/importável” ou “erro”; não carregar automaticamente.
- Para importação confirmada, criar `Modelfile`, registrar com Ollama e atualizar a lista.
- Considerar monitoramento automático da pasta depois que o fluxo explícito estiver estável.

**Saída:** caminho compreensível de arquivo GGUF local até modelo selecionável.

### Etapa 6 — qualidade, empacotamento e evolução

- Comparar resultados dos modelos suportados no conjunto manual e documentar limitações.
- Versionar schema, prompts e preferências do usuário.
- Empacotar o aplicativo e decidir se Ollama será dependência instalada à parte ou instalação assistida.
- Considerar adaptador llama.cpp, fine-tuning, histórico ou exportação somente quando houver requisito e evidência.

## 6. Critérios de conclusão do MVP

- O programa lista modelos locais retornados pelo Ollama e permite selecionar um.
- Uma sentença enviada retorna entidades e relações validadas pelo schema.
- Relações sem referência válida e tipos fora do vocabulário são rejeitados ou normalizados de maneira explícita.
- A UI apresenta os resultados em lista e grafo, sem travar durante a geração.
- Erros de serviço, modelo e resposta são visíveis e não encerram o aplicativo.
- Existe um procedimento documentado para instalar modelo via Ollama.

## 7. Principais riscos e decisões em aberto

- **Hardware e desempenho:** tamanho e quantização do modelo determinam memória, velocidade e qualidade. Medir no computador-alvo antes de recomendar modelos específicos.
- **Qualidade semântica:** JSON válido não significa extração correta; medir com sentenças em português e manter evidência textual quando possível.
- **Importação arbitrária:** GGUF não implica compatibilidade garantida. Usar metadados, runtime e validação do próprio modelo.
- **Vocabulário:** decidir se tipos/relacionamentos serão fixos, editáveis ou definidos pelo usuário. Começar controlado e pequeno.
- **Distribuição:** decidir sistema operacional alvo e se o usuário instala Ollama separadamente.

## 8. Referências técnicas consultadas

- [Ollama — List models API](https://docs.ollama.com/api/tags): consulta dos modelos conhecidos pelo serviço local.
- [Ollama — Importing a Model](https://docs.ollama.com/import): importação de GGUF/Safetensors por `Modelfile` e `ollama create`.
- [Ollama — Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs): JSON Schema, Pydantic e validação da saída.
- [Ollama — Chat API](https://docs.ollama.com/api/chat): endpoint local e campo `format`.
- [llama.cpp — HTTP Server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md): servidor local, GGUF, API compatível com OpenAI e JSON com schema.
- [Hugging Face Transformers — Installation/offline](https://huggingface.co/docs/transformers/installation): arquivos/cache locais e modo offline, como referência para alternativas que carregam modelos diretamente em Python.
