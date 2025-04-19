# Math Tutoring Agent with Singapore Method
This project implements a personalized math tutoring agent that uses the Singapore Method and the CPA (Concrete-Pictorial-Abstract) approach to help students understand mathematical concepts effectively.

## Key Features

- Adaptive Diagnostics: Assesses the current level of understanding and adapts instruction accordingly.
- Singapore Method: Implements the Concrete-Pictorial-Abstract approach for deep understanding.
- Thematic Personalization: Examples and problems are contextualized according to the student's interests.
- Learning Paths: Flexible pathways for various math topics.
- Multimodal Generation: Combines text, images, and audio for a complete experience.
- Intelligent Adaptation: Dynamically adjusts the difficulty level in real time based on performance.

## Project Structure

The project is divided into backend and frontend:

### Backend (FastAPI + LangGraph)

```
    └── backend/
        ├── main.py                     # API entry point
        └── app/
            ├── agent/                  # Agent logic
            │   ├── graph.py            # LangGraph definition
            │   ├── nodes.py            # Graph nodes (functions)
            │   ├── prompts.py          # Prompt templates
            │   ├── roadmap.py          # Learning paths
            │   ├── state.py            # State definitions
            │   └── diagnostic.py       # Diagnostic tools
            ├── api/endpoints/          # API endpoints
            │   └── session.py          # Session management
            ├── schemas/                # Pydantic models
            │   └── session.py          # Session schemas
            └── services/               # External services
                ├── azure_openai.py     # Azure OpenAI client
                ├── azure_speech.py     # Azure TTS client
                └── stability_ai.py     # Stability AI client
```

### Frontend (Next.js + TypeScript)

```
└── frontend/
    ├── public/                        # Static assets
    │   └── images/                    # Thematic images
    └── src/
        ├── api/                       # API client
        │   └── mathTutorClient.ts     # Backend client
        ├── components/                # Reusable components
        │   └── ui/                    # UI components
        ├── pages/                     # Routes/pages
        │   ├── index.tsx              # Home page
        │   ├── diagnostic.tsx         # Diagnostic evaluation
        │   ├── learning-path.tsx      # Learning path selection
        │   ├── theme.tsx              # Theme selection
        │   └── lesson.tsx             # Main lesson interface
        └── types/                     # TypeScript definitions
```

## Learning Paths
The system includes learning paths for the following topics:

- Fractions: From basic concepts to advanced operations
- Addition: From basic addition to multi-digit with carrying
- Subtraction: From basic subtraction to multi-digit with borrowing
- Multiplication: From tables to multi-digit multiplication
- Division: From basic division to complex problems

Each path follows a carefully designed pedagogical sequence with mastery requirements to advance.

## Future Adaptation
The system is designed to be easily extensible:

1. Add new learning paths in app/agent/roadmap.py
2. Create new topic-specific prompts in app/agent/prompts.py
3. Add new personalized themes in the frontend


## Credits
Developed as a demo project integrating Azure OpenAI and LangGraph to create adaptive educational agents.

