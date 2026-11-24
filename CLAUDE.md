# Instruções para futuras implementações

## Objetivo

Aplicativo desktop local que extrai entidades e relações de texto usando modelos locais e mostra os resultados como grafo.

## Decisões do projeto

- MVP em Python; interface desktop com PySide6.
- Ollama é o primeiro provedor de inferência. A aplicação deve usar a API local, consultar modelos instalados e não implementar inferência de LLM em C++/Rust.
- Manter o provedor atrás de uma interface pequena para permitir outro runtime, como llama.cpp, no futuro.
- GGUF em pasta precisa ser registrado no Ollama (API `/api/create` ou `Modelfile`/`ollama create`); detectar arquivo não significa que ele pode rodar.
- A importação de GGUF já existe como CLI (`scripts/models.py`): pasta `Models/`, biblioteca `ollama` (`create_blob` + `create`), seleção salva em `.lexgraph/config.json`. A UI deve reutilizar `src/services/models.py` em vez de duplicar a lógica.
- Registrar um modelo no Ollama não garante que ele execute: o `/api/create` aceita GGUF sem pesos válidos. Não apresentar "importado" como "funcionando".
- Não fazer fine-tuning no MVP. Usar prompt, JSON Schema, Pydantic e validação semântica.
- Ler [Planejamento.md](Planejamento.md) antes de alterar arquitetura ou escopo.

## Contrato de extração

- Manter entidades e relações em estruturas tipadas e com `schema_version`.
- Relações são direcionadas por `source`, `label`, `target`; ambas as pontas devem apontar para IDs de entidades existentes.
- Usar vocabulário controlado para tipos e rótulos. Preservar o texto original da sentença e não acrescentar fatos que não estejam sustentados por ela.
- Validar a saída do modelo em Python mesmo quando o runtime receber um JSON Schema.
- Falhas de runtime, timeout, JSON inválido e validação devem aparecer como erros recuperáveis na UI.

## Organização sugerida

- `src/app/`: inicialização da aplicação.
- `src/ui/`: janelas, componentes e visualização do grafo.
- `src/domain/`: modelos Pydantic e regras do grafo.
- `src/services/`: orquestração de extração e prompts.
- `src/providers/`: adaptador Ollama e futuros provedores.
- `scripts/`: ferramentas de linha de comando (ex.: `models.py`); adicionam `src/` ao `sys.path`.
- `tests/`: testes unitários com `unittest` (`python -m unittest discover -s tests`); sem chamadas reais ao Ollama, use clientes falsos.

Adapte a organização ao código já existente quando ele for criado; evite criar camadas sem necessidade.

## Diretrizes de implementação

- Não bloquear a thread principal da UI durante chamadas ao modelo.
- Não colocar chamadas HTTP diretamente em componentes visuais; usar serviços/adaptadores.
- Atualizar seletor de modelos ao iniciar e sob solicitação do usuário, com feedback quando Ollama estiver indisponível.
- Mostrar resultados em forma textual além do grafo.
- Erros para o usuário devem dizer o que aconteceu e como resolver (como em `ModelError`). Operações em lote continuam após falhas e terminam com resumo.
- Manter o código curto: usar bibliotecas prontas (ex.: `ollama` para a API) em vez de reimplementar HTTP ou utilitários. Dependências ficam em `requirements.txt` e o ambiente em `.venv/`.
- Manter prompts e schema versionados no código e explicar mudanças incompatíveis.
- Não baixar modelos ou executar inferência de forma silenciosa. A escolha/instalação do modelo deve ser clara para o usuário.

## Sequência de trabalho

1. Validar Ollama e extração estruturada sem UI.
2. Criar schema Pydantic e validação semântica.
3. Implementar provedor Ollama e erros recuperáveis.
4. Fazer UI mínima e lista de resultados.
5. Renderizar grafo.
6. Levar descoberta/importação de GGUF para a UI (a versão CLI já existe).

Ao implementar, consultar a documentação oficial atual do runtime escolhido, pois API e suporte podem mudar. O planejamento registra as fontes iniciais e o escopo do MVP.
