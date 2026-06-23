---
title: extracao — Agente 1 (Extração de Frames)
type: entity
created: 2026-06-14
updated: 2026-06-22
sources: ["agentes/extracao.py", "config.py", "pipeline.py", "app.py"]
tags: [component, agent, ffmpeg, extraction, fps, frames]
status: stable
migrated-from: wiki/components/extracao.md
original-date: 2026-06-13
---
# extracao — Agente 1 (Extração de Frames)

`agentes/extracao.py` expõe uma única função pública — `extrair_frames(video_path, output_dir)` — que converte o vídeo de entrada em frames PNG numerados e devolve metadados usados por todos os agentes subsequentes da pipeline.

## Assinatura e contrato público

```python
def extrair_frames(video_path: str, output_dir: str) -> dict:
    ...
    return {
        "fps": float,          # FPS real, arredondado a 3 casas
        "total_frames": int,   # contagem real dos PNGs gerados
        "width": int,          # largura em pixels
        "height": int,         # altura em pixels
        "tempo_s": float,      # elapsed total da função
    }
```

O dict retornado é consumido diretamente pelo orquestrador (`pipeline.py`) e pela UI (`app.py`). Nenhum estado é mantido em disco além dos próprios PNGs — não há arquivo de manifesto ou lock.

## Sequência interna (passo a passo)

### 1. Criar diretório de saída

```python
os.makedirs(output_dir, exist_ok=True)
```

Cria `output_dir` recursivamente se não existir. Idempotente — não falha se já existir.

### 2. Probing via ffprobe

```python
probe_cmd = [
    "ffprobe", "-v", "error",
    "-select_streams", "v:0",
    "-show_entries", "stream=r_frame_rate,width,height,nb_frames",
    "-of", "json", video_path
]
result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
meta = json.loads(result.stdout)["streams"][0]
```

- `-v error` suprime os logs de diagnóstico do ffprobe, deixando apenas o JSON na stdout.
- `-select_streams v:0` — apenas o primeiro stream de vídeo; áudio e legendas são ignorados.
- `-show_entries stream=r_frame_rate,width,height,nb_frames` — os quatro campos necessários.
- `-of json` — saída em JSON parseável.
- `check=True` — qualquer código de saída != 0 lança `subprocess.CalledProcessError` imediatamente (fail-fast).

> ⚠️ `nb_frames` pode retornar `None` ou estar ausente em containers que não pré-calculam o número de frames (e.g. alguns MKV). O agente **não usa** `nb_frames` para nada — é coletado mas ignorado. O `total_frames` real é contado por listagem de arquivos após a extração (ver passo 4).

### 3. Resolução de FPS

Ver [[concepts/agent-frame-extraction-fps-detection]] para a explicação completa. Em resumo:

```python
fps_raw = meta["r_frame_rate"]   # ex: "30000/1001"  ou  "25/1"
num, den = map(int, fps_raw.split("/"))
fps = round(num / den, 3)        # 29.97  ou  25.0
```

O valor `fps` retornado é usado pela exportação para reconstituir o timing original do vídeo.

### 4. Extração de frames via ffmpeg

```python
extract_cmd = [
    "ffmpeg", "-y", "-i", video_path,
    "-q:v", "1",
    "-pix_fmt", "rgb24",
    f"{output_dir}/frame_%05d.png"
]
subprocess.run(extract_cmd, check=True, capture_output=True)
```

| Flag | Efeito |
|---|---|
| `-y` | Sobrescreve arquivos existentes sem perguntar — **sem resume granular** |
| `-i video_path` | Arquivo de entrada |
| `-q:v 1` | Qualidade máxima para codec de imagem (menor = melhor em ffmpeg MJPEG-like scale; para PNG é lossless de qualquer forma, mas controla o nível de compressão interna) |
| `-pix_fmt rgb24` | Força RGB de 8 bits por canal — remove qualquer alpha ou espaço YUV; consumível diretamente por Pillow e OpenCV sem conversão |
| `frame_%05d.png` | Nome com 5 dígitos zero-padded: `frame_00001.png` … `frame_99999.png` |

`capture_output=True` silencia a saída do ffmpeg no terminal. `check=True` falha imediatamente se o ffmpeg retornar erro.

### 5. Contagem real de frames

```python
total_frames = len([f for f in os.listdir(output_dir) if f.endswith(".png")])
```

Lista todos os `.png` no `output_dir` após a extração. Essa contagem é a fonte de verdade para `total_frames` — **não** o campo `nb_frames` do ffprobe.

### 6. Retorno

Retorna o dict com os metadados coletados e o `tempo_s` elapsed. O chamador (pipeline ou UI) armazena esses valores em memória.

## Output dir conventions

O `output_dir` passado à função é sempre o caminho `frames_raw` resolvido pelo [[sources/agent-frame-extraction-config-py]]:

```
<base>/frames/raw/frame_00001.png
               …
               frame_NNNNN.png
```

A base padrão é `./workspace` (local) ou `/content/drive/MyDrive/iclight_pipeline` (Colab). Ver [[concepts/agent-frame-extraction-output-dir-conventions]] para o layout completo.

## Comportamento de resume (ausência de)

O agente **não tem resume granular**. O flag `-y` no ffmpeg sobrescreve qualquer frame existente. Reexecutar a extração recomeça do zero. Isso é aceitável porque a extração é barata (~1ms/frame) comparada ao relighting (~1.5s/frame). Ver [[decisions/agent-frame-extraction-no-resume]].

## Callers

| Arquivo | Contexto |
|---|---|
| `pipeline.py` linha 76 | CLI offline — Etapa 1/5 |
| `app.py` → `cb_preparar()` linha 106 | Gradio UI — botão "Preparar vídeo" |

No `pipeline.py` o retorno alimenta diretamente o `pipeline_log` e o `meta["fps"]` passado à exportação. No `app.py` o retorno alimenta o `ESTADO["meta"]` global (single-user) e configura o slider de frames.

## Dependências de runtime

- `ffmpeg` e `ffprobe` acessíveis no `PATH` do processo Python.
- No Colab: instalados via `apt-get install -y ffmpeg` na célula de setup.
- No Windows local: requer instalação manual e adição ao PATH.
- Sem GPU — roda 100% em CPU.

## Gotchas

- `nb_frames` do ffprobe pode estar ausente; o código não o usa para cálculo, só para coleta.
- Se o `output_dir` já contiver PNGs de uma execução anterior, a contagem final os inclui todos — incluindo eventuais frames não sobrescritos de um vídeo diferente, se o diretório não for limpo entre execuções.
- O `capture_output=True` no ffmpeg esconde erros de codificação na stderr. Em modo de debug pode ser necessário remover essa flag.

## Relacionados

[[entities/pipeline]] · [[entities/remocao]] · [[entities/exportacao]] ·
[[concepts/video-frame-pipeline]] · [[concepts/agent-frame-extraction-fps-detection]] ·
[[concepts/agent-frame-extraction-output-dir-conventions]] ·
[[decisions/agent-frame-extraction-no-resume]] ·
[[sources/agent-frame-extraction-config-py]] · [[index]]
