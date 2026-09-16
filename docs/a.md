This architectural design is called a Prompt Microservices Architecture (or Task-Specific Model Microservices). When applied in the context of multi-agent workflows, it is also referred to as a Specialized Agent Architecture or Multi-Model Endpoint Architecture.

Here is how this pattern breaks down across software engineering and AI design paradigms:

1. Prompt Microservices Architecture
In traditional software development, microservices break down a monolithic application into small, single-responsibility services that communicate over APIs.

By extracting system prompts and configurations into separate Modelfile configurations (e.g., Modelfile.chat, Modelfile.readiness) and running distinct Ollama container/service instances for each:

Decoupled Governance: You isolate prompt engineering, context windows, temperature settings, and base model selections per specific domain task.

Independent Scaling & Updates: You can update system instructions for Modelfile.readiness without disturbing the Modelfile.chat service or risking prompt regression across other capabilities.

2. Specialized Agent (or Multi-Agent) Pattern
From an AI/LLM system design perspective, creating distinct endpoints for specialized behaviors forms the foundation of a Multi-Agent System.

Each Ollama instance acts as a dedicated specialized agent (e.g., a triage agent, a readiness evaluator, or a conversational agent).

An upstream router or API gateway receives user requests and routes them to the appropriate specialized Ollama endpoint based on intent or workflow stage.

3. Model-as-a-Service (MaaS) / Task-Specific Endpoints
When hosting multiple tailored instances on local infrastructure or private cloud, this pattern represents an on-premise Model-as-a-Service (MaaS) design. Rather than making calls to a single base LLM endpoint with heavy dynamic prompt injections, your application layer consumes static, specialized endpoints optimized for specific functions.

Core Advantages of This Approach
Predictable Token Usage: Specialized prompts keep system context concise, avoiding token waste from large, monolithic prompts that try to cover every instruction at once.

Configuration Fine-Tuning: You can assign lower temperatures (e.g., 0.0 or 0.2) to Modelfile.readiness for deterministic validation, while using higher temperatures (0.7) for Modelfile.chat.

Version Control as Code: Treating Modelfile definitions as code artifacts allows you to track system prompt evolution alongside your application's deployment code.