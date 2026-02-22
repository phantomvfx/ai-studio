# Multi-Agent AI Studio

A 30-second short-form visual storytelling workflow powered by Griptape and Streamlit.

## Features
- **Adaptive Orchestration:** The AI seamlessly acts as a 'Creative Engine' for vague ideas or a 'Refiner' for specific concepts.
- **Reference Synergy (I2I):** Generated prompts are heavily optimized with intense technical detail, acting as overrides for reference Image-to-Image workflows.
- **Human-in-the-Loop Orchestration:** User-friendly UI allowing you to inject Art and Camera preferences mid-workflow.
- **Local & Cloud Driver Support:** Choose between fast Cloud (Google Gemini) and secure Local (Ollama) engines via the Streamlit UI.

## Getting Started

1. Set your `GOOGLE_API_KEY` in the `.env` file.
2. Install dependencies via `pip install -r requirements.txt`.
3. Run the Studio via `run_studio.bat` or `streamlit run app.py`.

## Output
All generated markdown prompts will be saved to the `/outputs` folder with the timestamp and short slug of your prompt. You can download them directly from the Streamlit UI.
