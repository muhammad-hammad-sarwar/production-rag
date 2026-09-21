## Gateways

Instead of calling an LLM provider directly, applications communicate
through an **LLM Gateway**.

```
PortKey, LightLLM, Bifrost, Cloudflare
```

The Gateway provides:

- **Model Routing** — choose the appropriate model/provider for a request.
- **Fallbacks** — automatically switch to another provider when the primary
  model fails or becomes unavailable.
- **Guardrails** — validate inputs before they reach the model and validate
  outputs before they reach the application.
- **Provider Abstraction** — the application does not need to know which
  provider is being used.
- **Model Routing For Selecting Model Based on Task** - If task is processing intense, we will use a large model,
  and if it is a simple task like writing email we will use small model.

This makes LLM applications more **fault-tolerant, secure, and easier to
operate**.

### Example

```text
Application
     │
     ▼
┌───────────────────────┐
│      LLM Gateway      │
│                       │
│  ┌─────────────────┐  │
│  │    Guardrails   │  │
│  └────────┬────────┘  │
│           ▼           │
│  ┌─────────────────┐  │
│  │  Model Router   │  │
│  └────────┬────────┘  │
└───────────┼───────────┘
            │
      ┌─────┼─────┬─────────┐
      ▼     ▼     ▼         ▼
   OpenAI  Claude Gemini   Llama
      │
      │ failure
      ▼
   Claude
      │
      │ failure
      ▼
   Gemini
```

### Virtial Keys

- **Multiple Model Provider APIs** - We have let's say 10 provider APIs,
  we dont want to add all 10 apis for each provider which is a pain,
  adding in prod and dev environments, what we do is to add apis in gateway and
  it gives us an alias called **Slug**. We can use that slug in our project.
