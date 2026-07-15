# DeepSeek V4-Flash Native Vision — Reference

## Source

Discovered 2026-07-12 during Prometheus architecture work. DeepSeek rolled out multimodal for V4-Pro and V4-Flash on June 18, 2026. Confirmed working in Gopher's session — the model saw Evan's face, described shirt text "CAN'T", identified room details (guitar, plush toy, red walls) with no hallucinations, no privacy blocks.

## Specs

| Metric | Value |
|---|---|
| KV entries per 800x800 image | ~90 (vs ~870 Claude, ~1100 Gemini) |
| Input pricing | $0.14/M tokens (direct DeepSeek), $0.077/M (OpenRouter) |
| Cost per image | ~$0.000013 |
| Three images per handoff | ~$0.000039 |
| Context window | 1M tokens total (incl visual tokens) |
| API format | OpenAI-compatible (URL or base64) |
| OpenRouter model ID | `deepseek/deepseek-v4-flash` |

## Strong capabilities

- OCR and document text extraction
- Chart and graph understanding
- Screenshot analysis and UI description
- General image description and visual Q&A
- Multi-image comparison
- Table extraction from images
- Handwriting recognition
- **Photo description with people** (NO privacy gating — unlike GPT-4o/Gemini auxiliary fallbacks)

## Weaker areas

- Complex multi-step visual reasoning
- Very fine-grained image detail (tiny text, subtle differences)
- Video frame analysis (not supported)

## How to pass images natively

### Direct DeepSeek API (OpenAI SDK, works with Hermes deepseek-provider)

```python
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
            {"type": "text", "text": "What does this show?"}
        ]
    }]
)
```

### With base64-encoded local image

```python
import base64
with open("/tmp/canvas.png", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
            {"type": "text", "text": "Describe this canvas before and after the edit."}
        ]
    }]
)
```

## Hermes config for auxiliary vision

In agent's `config.yaml`:

```yaml
auxiliary:
  vision:
    provider: openrouter     # or 'deepseek' for direct API
    model: deepseek/deepseek-v4-flash
    download_timeout: 30
```

## MEDIA: path behavior in Hermes

- **Telegram/Discord gateway:** When a message contains `MEDIA:/absolute/path/to/img.png`, the gateway reads the file, sends it as a native image attachment. The model receives the image inline as a multimodal content block. Native vision processes it.
- **CLI mode:** MEDIA: is NOT handled. Use `hermes chat --image /path/to/img.png "prompt"` instead.
- **TUI mode:** Not verified yet.

## Auxiliary pipeline vs native vision

| Aspect | Auxiliary vision_analyze tool | Native vision (MEDIA: inline) |
|---|---|---|
| Model | Fallback model (varies, often Gemini/GPT-4o-mini) | deepseek-v4-flash (same as main) |
| Cost per image | ~$0.002 (GPT-4o) | ~$0.000013 |
| Privacy blocks | YES — refuses to describe people | NO — describes everything |
| Hallucination rate | Higher (worse model) | Lower |
| Latency | Extra API round-trip | Zero (image in context) |
| Tool call needed | Yes | No |
