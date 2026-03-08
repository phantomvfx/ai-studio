# 🎬 Multi-Agent AI Studio (Visual Storytelling)

**Live Demo:** [https://ai-studio-phlabs.streamlit.app/](https://ai-studio-phlabs.streamlit.app/)

**AI Studio** is an advanced, dual-engine (Cloud & Local) AI pipeline designed to generate continuous narrative storyboards and detailed product shots using a combination of LLMs and generative image diffusion models.

## ✨ Features

- **Dual-Engine Flexibility**: 
  - **Cloud Mode**: Harnesses Google GenAI (`gemini-2.5-flash`, `gemini-3.1-pro-preview`) for high-quality, high-speed reasoning and image synthesis.
  - **Local Mode**: Runs entirely offline via Ollama, supporting models like `qwen3.5:9b`, `gemma3:12b`, `kimi-k2.5:cloud`, and `gpt-oss:20b` for complete privacy.
- **Workflow Modes**:
  - **30-Second Storytelling**: A comprehensive multi-phase pipeline that breaks a concept down into a structured story arc, formats it into a screenplay, offers Art & Cinematography suggestions, and finally outputs an array of robust JSON rendering prompts conforming strictly to the `Nano Banana Pro` schema.
  - **Product Shot**: A streamlined, strict zero-shot pipeline that directly parses a concept into the final JSON array layout.
- **Integrated Image Generation**: 
  - **Gemini 2.5 Flash**: Generate high-speed Storyboard previews natively in Cloud Mode.
  - **Local ComfyUI Integration**: Seamlessly dispatches generation jobs to a local ComfyUI instance running the `ZimageRender.json` workflow.
- **Deliverables Export**: Single-click compiled Markdown export containing the entire creative process alongside the final `I2V` (Image-to-Video) prompt blocks.

---

## 🚀 Installation & Setup

### Prerequisites
1. **Python 3.12**
2. **Google Gemini API Key** (for Cloud mode)
3. **Ollama** installed locally (for Local mode)
4. *(Optional)* **ComfyUI** running locally on port `8188` (for Local Image Generation)

### 1. Clone & Install
```bash
git clone https://github.com/phantomvfx/ai-studio.git
cd aistudio

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the root directory and add your Google API key:
```env
GOOGLE_API_KEY=your_genai_api_key_here
```

### 3. Start the Application
You can run the application directly via Streamlit or by using the provided batch file:
```bash
# Using Streamlit directly
streamlit run app.py

# OR using the Windows batch file
run_studio.bat
```

---

## 📱 Telegram Bot Integration (CLI)
AI Studio includes a fully functional, headless Telegram Bot (`cli_telegram.py`) that allows you to generate campaigns directly from your phone.

1. Message `@BotFather` on Telegram to create a new bot and copy the HTTP API Token.
2. Add your token to the `.env` file:
   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   ```
3. Run `run_studio.bat` (which boots the bot automatically) OR run it manually:
   ```bash
   python cli_telegram.py
   ```
4. **Usage**: Message your bot `/generate <concept>` for a full Storyboard campaign, or `/product <concept>` for a Product Shot campaign. The bot will autonomously run the entire pipeline through your local models and reply with the compiled `.md` document and a ComfyUI image preview!

---

## 🔌 Integrating Local ComfyUI (Zimage)
If you wish to render storyboards natively on your GPU without calling Cloud APIs, you can use the built-in ComfyUI integration.

1. Launch your **ComfyUI** instance locally so that it is running at `http://127.0.0.1:8188`.
2. Ensure you have the `comfyui/ZimageRender.json` workflow present in your AI Studio directory.
3. In the AI Studio Web UI, click **"Generate Local Image (ComfyUI)"**. The backend will automatically inject the prompt, randomize the diffusion seed, and poll ComfyUI's `/history` endpoint until the image is returned straight into your Streamlit interface.

---

## 📂 Project Structure

- `app.py`: The Main Streamlit user interface.
- `pipeline.py`: Core logic, schema enforcement, API routing, and ComfyUI websocket polling.
- `cli_telegram.py`: *(Optional)* A CLI/Telegram bot interface for running the core pipeline asynchronously.
- `knowledge/`: Contains the system instructions, schemas, and markdown rulesets enforcing the LLM behaviors (e.g., `nano_banana_schema.json`, `product_shot_rules.md`).
- `comfyui/`: Contains the `ZimageRender.json` workflow used for the seamless local API dispatch.
- `outputs/`: Default save directory for generated `.json` and `.md` assets.

---

## 🛠️ Modifying the Pipeline
- **Adding New Local Models**: To add new Ollama targets, simply update the `local_model_selector` UI dropdown in `app.py`, and it will automatically flow down into `pipeline.py`'s `call_llm` routing.
- **Adjusting the Schema**: Open `knowledge/nano_banana_schema.json`. By altering the required fields here, the Pipeline will rigorously enforce the new ruleset onto the AI engines.
