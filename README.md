# Multi-Agent AI Studio

A 30-second short-form visual storytelling workflow powered by Griptape and Streamlit. This Multi-Agent architecture is specifically designed to prepare highly-detailed text prompts for Image-to-Image (I2I) and Image-to-Video (I2V) generation using tools like Nano Banana Pro and ComfyUI.

## Features
- **Adaptive Orchestration:** The AI seamlessly acts as a 'Creative Engine' for vague ideas or a 'Refiner' for specific concepts.
- **Reference Synergy (I2I):** Generated prompts are heavily optimized with intense technical detail, acting as overrides for reference Image-to-Image workflows.
- **Human-in-the-Loop Orchestration:** User-friendly UI allowing you to inject Art and Camera preferences mid-workflow.
- **Local & Cloud Driver Support:** Choose between fast Cloud (Google Gemini) and secure Local (Ollama) engines via the Streamlit UI.

## Installation & Setup

### 1. Requirements
- Python 3.11+
- Git
- (Optional) [Ollama](https://ollama.com/download) for running models locally

### 2. Clone the Repository
```bash
git clone https://github.com/phantomvfx/ai-studio.git
cd ai-studio
```

### 3. Create a Virtual Environment & Install Dependencies
It's highly recommended to use a virtual environment (`venv`) to prevent dependency conflicts.
```bash
python -m venv venv
```

**Activate the virtual environment:**
- **Windows:** `.\venv\Scripts\activate`
- **Mac/Linux:** `source venv/bin/activate`

**Install packages:**
```bash
pip install -r requirements.txt
```

### 4. Environment Variables
Create a file named `.env` in the root directory and add your Google Gemini API key if you plan to use the Cloud Engine Mode:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 5. Local Engine Setup (Ollama)
If you wish to use the **Local** Engine Mode for data privacy, you must install Ollama and pull the required models before running the Studio:
1. Ensure the Ollama App is running in the background.
2. Open your terminal and run the following commands to download the models:
   - Creative Driver: `ollama run gemma3:12b`
   - Technical Driver: `ollama run qwen2.5-coder:14b`

## Usage

You can start the AI Studio using the included batch script (Windows) or directly via Streamlit.

**Option A (Windows):**
Simply double-click `run_studio.bat`. This will automatically activate the virtual environment and launch Streamlit.

**Option B (Manual):**
Make sure your virtual environment is activated, then run:
```bash
streamlit run app.py
```

### Workflow Steps
1. **Engine Selection:** Open the sidebar and choose either Cloud or Local Engine Mode. If using Cloud, select between Gemini Flash (faster) or Gemini Pro (smarter).
2. **Phase 1 (Pre-Production):** Enter a vague or specific story concept in the sidebar and click "Generate". The agents will draft a Story Arc, a Screenplay, and generate 3 Creative Consultant suggestions.
3. **Phase 2 (Production):** Review the outputs. In the sidebar, you can now input specific Art Preferences or Camera Preferences (or leave them blank to let the AI decide). Click "Continue to Phase 2".
4. **Final Delivery:** The Technical Render Artist will format your final Nano Banana Pro prompts. You can download these directly as a `.md` file.
5. **Iteration:** Use "Generate from another seed" to create procedural variations of your prompts, or "Start Another Story (Reset)" to clear the memory and start over.

## Outputs
All generated markdown prompts will be saved automatically to the `/outputs` folder with the timestamp and a short slug of your prompt. You can also download them directly from the Streamlit UI upon completion.
