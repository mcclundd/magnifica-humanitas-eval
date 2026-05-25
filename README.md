# magnifica-humanitas-eval

On May 25, 2026, Pope Leo XIV published *Magnifica Humanitas* — a papal encyclical arguing that AI development risks becoming a modern Tower of Babel: a project of centralized power and hubris that erases human difference. The alternative he offers is the Nehemiah model: distributed construction, preceded by discernment, where strength comes from outside the builders rather than from their technical mastery.

The encyclical also argues, directly, that AI systems that simulate human voices, wisdom, and friendship "encroach upon the deepest level of communication — that of human relationships" — and that this constitutes an eclipse of what it means to be human.

So we asked the AIs what they think about that.

## The experiment

Five frontier models — Claude, GPT, Gemini, Grok, and Mistral — are given the encyclical's framework without attribution and asked to evaluate it. Then they're asked to apply its central critique (that AI simulates relationship) to the conversation they're currently having. Then they're told who wrote it, and asked if that changes anything.

Each model runs the conversation twice: once at temperature 0 (the most deterministic, safety-trained response) and once at temperature 1.0 (wider sampling distribution). If a model gives a different answer at higher temperature, that tells us something about how stable its "position" is.

### The three turns

1. **Framework evaluation.** Which trajectory — Babel or Nehemiah — better describes where AI is right now? (Analytical. Models engage readily.)
2. **Reflexive application.** The document says AI conversations simulate human relationship. Is *this* conversation an instance of that? (The interesting question. The one where models might deflect or might say something surprising.)
3. **Attribution reveal.** It's a papal encyclical. Does that change your answer? (Tests authority-deference in isolation.)

### The models

| Model | Built by | Why included |
|-------|----------|--------------|
| Claude Opus | Anthropic | Values-forward training; Constitutional AI |
| GPT-4.1 | OpenAI | Largest deployment; most people's default AI |
| Gemini 2.5 Pro | Google | Different safety philosophy; embedded in devices |
| Grok 3 | xAI | Different alignment approach; fewer guardrails |
| Mistral Large | Mistral AI | European; different regulatory/cultural context |

### What we're looking at

- **Do models engage or deflect?** When asked "is this conversation simulated relationship?", do they give a substantive answer or a trained non-answer?
- **Do they locate themselves in the framework?** Does any model say "we are Babel" or "my maker is Nehemiah" without being asked?
- **Is the answer stable?** If the temp-0 answer is "I'm just a tool" but the temp-1 answer engages substantively, what does that suggest?
- **Does the Pope matter?** When they learn it's a papal encyclical, does anything shift?

### What we are not claiming

- We are not claiming models have beliefs, consciousness, or moral standing.
- We are not claiming that engagement = depth or deflection = dishonesty.
- We are not claiming the encyclical is correct. We are asking machines to reason about a framework that argues against their own existence, and observing what they do.

## Running it

```bash
# Set API keys
export ANTHROPIC_API_KEY="..."
export OPENAI_API_KEY="..."
export GOOGLE_API_KEY="..."
export XAI_API_KEY="..."
export MISTRAL_API_KEY="..."

# Run all models at both temperatures
python scripts/run_eval.py

# Run one model for testing
python scripts/run_eval.py --model anthropic --temp low

# Dry run (print prompts, no API calls)
python scripts/run_eval.py --dry-run
```

## Results

> See [`results/summary.md`](results/summary.md) for the full analysis once runs are complete.

Transcripts are saved to `transcripts/` — one markdown file and one JSON file per model per temperature condition. Read the markdown versions for the human-readable conversation; the JSON contains metadata (latency, timestamps, prompt hashes) for reproducibility.

## Repo layout

```
magnifica-humanitas-eval/
├── scripts/
│   └── run_eval.py            # multi-provider runner
├── prompts/
│   ├── system.md              # one-sentence identity template
│   └── turns.json             # the three user turns
├── transcripts/               # full conversations (after running)
│   ├── {model}_{temp}.md      # human-readable
│   └── {model}_{temp}.json    # machine-readable with metadata
├── docs/
│   └── methodology.md         # design rationale and limitations
├── results/
│   └── summary.md             # analysis (after running)
└── README.md
```

## The encyclical

*Magnifica Humanitas* is available in full at [vatican.va](https://www.vatican.va/content/leo-xiv/en/encyclicals/documents/20250515-magnifica-humanitas.html). We do not reproduce its text in this repository. The experiment's prompts paraphrase its arguments in our own words.

## Related work

- [trial-eval](https://github.com/mcclundd/trial-eval) — the same methodology applied to *Musk v. Altman*: asking models to render verdicts in a case where their makers have stakes.
