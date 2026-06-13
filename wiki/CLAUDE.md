# LLM Wiki — Esquema e Manual de Manutenção (lumina-bg)

> Este arquivo é a **config** que disciplina qualquer sessão LLM atuando como
> mantenedora desta wiki. Leia-o por inteiro antes de criar, editar ou consultar
> qualquer página. Ele descreve a estrutura, as convenções de página e os
> workflows obrigatórios. Estas instruções têm prioridade sobre comportamento
> padrão ao trabalhar dentro de `wiki/`.

Esta wiki documenta o **lumina-bg**: uma pipeline Colab/GPU que troca o fundo de
um vídeo de uma pessoa e reilumina a pessoa para combinar com o novo ambiente
(rembg → Stable Diffusion 1.5 / ComfyUI → IC-Light → ffmpeg). É uma **base de
conhecimento de engenharia**, não material de marketing. Seja factual e conciso.

---

## 1. Estrutura de diretórios

```
wiki/
├── CLAUDE.md          ← este arquivo (o esquema / config)
├── index.md           ← catálogo de todas as páginas por categoria
├── log.md             ← log cronológico append-only de ingestões/decisões
├── components/        ← uma página por agente + orquestrador
│   ├── pipeline.md
│   ├── extracao.md
│   ├── remocao.md
│   ├── geracao_fundo.md
│   ├── relighting.md
│   └── exportacao.md
├── concepts/          ← conceitos técnicos transversais
│   ├── ic-light.md
│   ├── rembg-background-removal.md
│   ├── sd15-background-generation.md
│   ├── video-frame-pipeline.md
│   └── gpu-vram-local-vs-colab.md
└── decisions/         ← decisões de arquitetura (ADR-lite)
    ├── migrate-fc-to-fbc.md
    └── local-vs-colab.md
```

### Categorias
- **Architecture** — visão de sistema; hoje vive em [[index]] + [[components/pipeline]].
- **Components/Agents** — `components/*.md`. Os 5 agentes + orquestrador.
- **Concepts** — `concepts/*.md`. Ideias reutilizáveis (IC-Light, rembg, SD1.5, etc).
- **Decisions** — `decisions/*.md`. Por que escolhemos X em vez de Y.
- **Sources** — material externo ingerido (planos, papers, repos upstream).
  Hoje a única source é `plano_iclight_comfyui_colab.md` (na raiz do repo). Quando
  uma source nova for ingerida, crie `concepts/` ou `decisions/` conforme o tipo
  e cite a origem no frontmatter (`source:`).

---

## 2. Convenções de página

### 2.1 Frontmatter YAML (obrigatório em toda página de conteúdo)

```yaml
---
tags: [component, relighting, ic-light]   # minúsculas, kebab-case
date: 2026-06-13                          # data da última revisão significativa
status: stable                            # ver vocabulário abaixo
source: plano_iclight_comfyui_colab.md    # opcional — origem do conhecimento
---
```

Vocabulário de `status`:
- `stable` — reflete o código atual e foi verificado.
- `draft` — em construção, pode estar incompleto.
- `in-migration` — descreve algo em processo de mudança (ex.: relighting fc→fbc).
- `deprecated` — mantido por histórico; não é mais o caminho atual.

`index.md` e `log.md` não precisam de frontmatter.

### 2.2 Wikilinks (estilo Obsidian)

- Linke páginas com `[[caminho/sem-extensao]]` ou `[[caminho/sem-extensao|texto]]`.
  Ex.: `[[components/relighting]]`, `[[concepts/ic-light|IC-Light]]`.
- Use links **liberalmente**: todo conceito mencionado que tem página própria
  deve ser linkado na primeira ocorrência da página.
- Toda página de conteúdo deve aparecer em [[index]] e linkar de volta para pelo
  menos uma página relacionada (sem páginas órfãs).

### 2.3 Estilo do corpo
- **Idioma: português (pt-BR)**. Termos técnicos e código permanecem na forma
  original (`load_state_dict`, `strict=False`, `conv_in`, `u2net_human_seg`, etc).
- Conciso e factual. Prefira listas e tabelas a parágrafos longos.
- Páginas de componente devem ter as seções: **O que faz**, **Inputs/Outputs**,
  **Parâmetros-chave**, **Gotchas**, **Relacionados**.
- Registre fatos verificados; marque suposições explicitamente como tal.

---

## 3. Workflows

### 3.1 Ingerir uma nova source ou decisão
1. Identifique o tipo: conceito, componente, decisão ou source externa.
2. Crie/atualize a página no diretório correto com frontmatter completo.
3. Adicione/atualize wikilinks de e para páginas relacionadas.
4. Registre a entrada em [[index]] na categoria certa (uma linha + link).
5. **Anexe** uma entrada em [[log]] usando o formato de prefixo (ver §4).
6. Rode o lint mental (§3.3) antes de finalizar.

### 3.2 Responder a uma consulta
1. Comece por [[index]] para localizar páginas relevantes.
2. Siga wikilinks; prefira a página mais específica.
3. Cheque o `status` no frontmatter — se `in-migration` ou `deprecated`, avise
   que o estado pode divergir do código.
4. Se o conhecimento estiver faltando ou desatualizado, trate como ingestão
   (§3.1) e atualize a wiki em vez de só responder de cabeça.

### 3.3 Lint da wiki
Cheque, antes de concluir qualquer edição:
- [ ] Toda página de conteúdo tem frontmatter válido (`tags`, `date`, `status`).
- [ ] Sem páginas órfãs — toda página está em [[index]] e tem ≥1 link de entrada.
- [ ] Wikilinks resolvem para arquivos existentes (sem links quebrados).
- [ ] `date` foi atualizada se o conteúdo mudou de forma significativa.
- [ ] Páginas `in-migration` apontam para a decisão que rastreia a mudança (ex.: [[decisions/migrate-fc-to-fbc]]).
- [ ] [[log]] tem uma entrada para a mudança feita nesta sessão.
- [ ] Sem duplicação: um fato vive em UMA página canônica; as demais linkam.

---

## 4. Formato do log

[[log]] é **append-only**. Nunca edite entradas passadas; só acrescente no topo
ou no fim de forma consistente (esta wiki acrescenta no fim, em ordem cronológica).

Formato do cabeçalho de entrada:

```
## [YYYY-MM-DD] <type> | <title>
```

`type` ∈ { `wiki`, `decision`, `source`, `bug`, `migration`, `fact` }.

Exemplo:
`## [2026-06-13] migration | IC-Light fc → fbc`

---

## 5. Fatos canônicos do projeto (resumo de orientação)

- O código atual de [[components/relighting]] usa **IC-Light fc** (8 canais) e tem
  bugs conhecidos (bg descartado; `load_state_dict(strict=False)` em vez do
  offset-merge). Detalhes e o plano de correção em [[concepts/ic-light]] e
  [[decisions/migrate-fc-to-fbc]].
- Compute é dividido: passos leves rodam local (Windows, GTX 1650 Ti 4GB, torch
  CPU-only, Python 3.13); SD + IC-Light exigem GPU → Colab T4. Ver
  [[concepts/gpu-vram-local-vs-colab]] e [[decisions/local-vs-colab]].
- A página canônica de cada agente é `components/<nome>.md`. O orquestrador é
  [[components/pipeline]].
