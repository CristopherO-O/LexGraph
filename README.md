# LexGraph

Aplicativo desktop local que extrai entidades e relações de texto com modelos de IA locais ([Ollama](https://ollama.com)) e mostra o resultado como grafo. Escopo e decisões: [Planejamento.md](Planejamento.md).

> Estado atual: só existe o script de modelos (`scripts/models.py`). Interface e extração ainda não foram implementadas.

## Instalação

```bash
# Ollama (Arch; use ollama-cuda/ollama-rocm para GPU). Outras distros: curl -fsSL https://ollama.com/install.sh | sh
sudo pacman -S ollama
sudo systemctl enable --now ollama

# Projeto
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Se o Ollama não estiver em `http://127.0.0.1:11434`, defina a variável `OLLAMA_HOST`.

## Adicionar modelos

O Ollama **não** detecta arquivos jogados nas pastas internas dele. Todo modelo precisa ser registrado, de uma destas formas:

1. **Baixar pelo Ollama (recomendado):** `ollama pull qwen2.5:7b-instruct`. Os modelos estão em https://ollama.com/library. Um modelo 7B em Q4 precisa de ~5 GB de RAM/VRAM.
2. **Arquivo `.gguf` com o script:** baixe um GGUF (no Hugging Face, repositórios `*-GGUF`, por exemplo na quantização `Q4_K_M`), coloque em `Models/` e rode o script (veja abaixo).
3. **Manual com `Modelfile`:** para personalizar template ou parâmetros:
   ```bash
   echo 'FROM ./Models/meu-modelo.gguf' > Modelfile
   ollama create meu-modelo -f Modelfile
   ```
   Pesos em Safetensors também podem ser importados assim. Veja https://docs.ollama.com/import.

## Script de modelos

```bash
scripts/models.py                  # lista o Ollama e importa todos os .gguf de Models/
scripts/models.py meu-modelo.gguf  # seleciona; se não estiver no Ollama, importa da pasta
scripts/models.py qwen2.5:7b       # nome do Ollama (com ou sem :tag) ou caminho para .gguf
```

- **Sem parâmetro:** importa os modelos da pasta um por vez. Se um falhar, mostra o erro e segue para o próximo. Os que já estão registrados são pulados.
- **Com parâmetro:** procura no Ollama e depois em `Models/`. O modelo escolhido fica salvo em `.lexgraph/config.json`.
- O nome registrado vem do arquivo: `Qwen2.5-7B.Q4_K_M.gguf` vira `qwen2.5-7b.q4_k_m`.
- Antes de importar, o script recusa arquivo vazio ou que não seja GGUF e modelo dividido (`-00001-of-00003`) com partes faltando. Arquivos `mmproj*` são ignorados.
- Use `--models-dir PASTA` para usar outra pasta.
- Códigos de saída: `0` ok, `1` erro, `3` lote com falhas.

**Importante:** registrar não garante que o modelo rode. O Ollama só valida a arquitetura ao carregar o modelo. Se um modelo importado falhar ao gerar texto, atualize o Ollama ou use outro arquivo. A importação copia o GGUF para o armazenamento do Ollama, então o original em `Models/` pode ser apagado depois.

## Testes

```bash
.venv/bin/python -m unittest discover -s tests
```
