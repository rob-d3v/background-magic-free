# lumina-bg

> Troque o fundo do seu video e ajuste a iluminacao automaticamente — sem tela verde, sem estudio.
> Roda de graca no Google Colab com GPU.

---

## O que faz?

Voce grava um video qualquer (pode ser no celular, webcam, tanto faz) e essa ferramenta:

1. **Recorta voce do video** — remove o fundo frame por frame usando IA
2. **Coloca um fundo novo** — voce escolhe:
   - **Opcao A:** digita o que quer (ex: "estudio moderno com luz azul") e a IA gera
   - **Opcao B:** faz upload da sua propria imagem de fundo (foto, print, etc)
3. **Ajusta a iluminacao** — a IA faz parecer que voce realmente esta naquele ambiente
4. **Exporta o video final** — com o audio original, pronto pra usar

**Antes / Depois:**
```
[Voce no quarto]  ───>  [Voce num estudio profissional com iluminacao cinematica]
```

---

## O que eu preciso?

- Uma conta Google (pra usar o Google Colab + Google Drive)
- Um video `.mp4` (curto, 10-60 segundos eh o ideal pra comecar)
- So. Nao precisa instalar nada no seu computador.

---

## Passo a passo (do zero)

### Passo 1 — Abrir o notebook no Google Colab

Clique no botao abaixo. Ele abre o notebook direto no Colab:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/rob-d3v/background-magic-free/blob/main/lumina_bg.ipynb)

> **Se o botao nao funcionar:** va em [colab.research.google.com](https://colab.research.google.com), clique em `File > Open notebook > GitHub`, e cole o link deste repositorio.

---

### Passo 2 — Ativar a GPU (IMPORTANTE!)

Sem isso nada funciona.

1. No Colab, va no menu: **Runtime > Change runtime type**
2. Em "Hardware accelerator", selecione **GPU** (T4)
3. Clique em **Save**

```
Se aparecer "T4" no canto superior direito, ta certo.
Se aparecer "None" ou "CPU", repita o passo acima.
```

---

### Passo 3 — Rodar celula por celula

O notebook tem 9 celulas. Rode uma de cada vez clicando no botao de play (triangulo) do lado esquerdo de cada celula.

**Celula 1 — Montar Google Drive**
- Vai pedir permissao pra acessar seu Google Drive. Clique em "Allow".
- Isso cria uma pasta `iclight_pipeline` no seu Drive pra guardar tudo.

**Celula 2 — Instalar dependencias**
- Instala tudo que precisa. Demora uns 2-3 minutos.
- Vai aparecer um monte de texto. Espere ate aparecer `Dependencias instaladas!`

**Celula 3 — Clonar repositorios**
- Baixa o ComfyUI e o IC-Light. Demora uns 1-2 minutos.

**Celula 4 — Baixar modelos de IA**
- Baixa os modelos Stable Diffusion e IC-Light (~4GB no total).
- Primeira vez demora uns 5-10 minutos. Depois pula automatico.

**Celula 5 — Upload do video + fundo (opcional)**
- Primeiro faz upload do seu video `.mp4`
  - Ou coloque manualmente em `Google Drive > iclight_pipeline > input > video.mp4`
- Depois pergunta se voce quer enviar um **fundo proprio** (imagem/foto)
  - **Se voce TEM uma imagem de fundo:** faz upload dela. A IA pula a geracao e usa a sua imagem direto. Mais rapido!
  - **Se voce NAO tem:** clica Cancel ou nao envia nada. A IA gera um fundo pra voce na proxima celula.
- No final mostra as informacoes do video e o tempo estimado.

**Celula 6 — Configurar prompt e parametros**
- O prompt serve pra duas coisas:
  - Se voce **nao enviou fundo**: a IA gera o fundo a partir desse texto
  - Se voce **enviou fundo proprio**: o prompt ainda eh usado pro IC-Light ajustar a iluminacao (descreva a luz da cena)
- Exemplos de prompts (em ingles funciona melhor):
  ```
  modern studio with soft blue ambient lighting, cinematic
  tropical beach at sunset, warm golden light
  cozy living room with fireplace, warm lighting
  futuristic neon city at night, cyberpunk
  professional office, clean white background
  ```
- Tambem da pra ajustar os parametros (steps, seed, qualidade), mas os padroes ja funcionam bem. Pode deixar como esta.

**Celula 7 — Rodar a pipeline**
- **ESSA EH A CELULA PRINCIPAL.** Ela faz todo o trabalho.
- Mostra o progresso etapa por etapa com barra de progresso.
- Tempo estimado:
  - Video de 10 segundos: ~10 min
  - Video de 30 segundos: ~28 min
  - Video de 1 minuto: ~55 min
- **Se o Colab desconectar no meio:** sem problema! Rode essa celula de novo. Ela continua de onde parou (nao reprocessa frames ja feitos).

**Celula 8 — Ver preview**
- Mostra 4 imagens lado a lado: original, sem fundo, fundo gerado, resultado final.
- Assim voce ve se ficou bom antes de baixar.

**Celula 9 — Baixar o video**
- Baixa o video final pro seu computador.
- O video tambem fica salvo em `Google Drive > iclight_pipeline > output > video_final.mp4`

---

## Dicas

- **Video curto primeiro** — teste com 5-10 segundos antes de processar videos longos
- **Prompt em ingles** — os modelos de IA entendem melhor. Use termos como "cinematic", "soft lighting", "studio"
- **Boa iluminacao no video original** — a IA funciona melhor se voce estiver bem iluminado no video
- **Fundo simples** — quanto mais uniforme o fundo original, melhor o recorte
- **Se der erro** — verifique se a GPU esta ativada (Passo 2) e se o video esta no formato `.mp4`

---

## Se o Colab desconectar

Isso eh normal no plano gratuito. Pode acontecer depois de uns 30-90 minutos.

**O que fazer:**
1. Reconecte (clique em "Reconnect" no canto superior direito)
2. Rode as celulas 2, 3 e 4 de novo (reinstala tudo, mas eh rapido)
3. Rode a celula 7 — ela continua de onde parou, nao recomeca do zero

---

## Estrutura do projeto

```
Google Drive/
  iclight_pipeline/
    input/video.mp4           <-- seu video original
    frames/raw/               <-- frames extraidos
    frames/nobg/              <-- frames sem fundo
    background/bg.png         <-- fundo gerado pela IA
    relit/                    <-- frames com iluminacao nova
    output/video_final.mp4    <-- VIDEO FINAL (resultado)
    pipeline_log.json         <-- log de execucao
```

---

## Tempo estimado (GPU T4 gratuita)

| Duracao do video | Tempo de processamento |
|---|---|
| 5 segundos | ~5 min |
| 10 segundos | ~10 min |
| 30 segundos | ~28 min |
| 1 minuto | ~55 min |
| 3 minutos | ~2.5 horas |

> A etapa mais demorada eh o relighting (IC-Light) — ~1.5s por frame.

---

## Problemas comuns

| Problema | Solucao |
|---|---|
| "GPU nao encontrada" | Runtime > Change runtime type > GPU (T4) |
| "Video nao encontrado" | Verifique se o video esta em `Drive > iclight_pipeline > input > video.mp4` |
| Colab desconectou | Reconecte e rode celulas 2-4 de novo, depois celula 7 |
| Resultado ficou estranho | Tente outro prompt ou mude o seed na celula 6 |
| Demora demais | Use video mais curto ou reduza Steps pra 15 na celula 6 |

---

## Tecnologias usadas

- [rembg](https://github.com/danielgatis/rembg) — remocao de fundo por IA
- [IC-Light](https://github.com/lllyasviel/IC-Light) — relighting (ajuste de iluminacao)
- [Stable Diffusion 1.5](https://huggingface.co/runwayml/stable-diffusion-v1-5) — geracao do fundo
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — backend para Stable Diffusion
- [ffmpeg](https://ffmpeg.org) — manipulacao de video

---

## Licenca

MIT — use como quiser.

---

Made by [@rob-d3v](https://github.com/rob-d3v)
