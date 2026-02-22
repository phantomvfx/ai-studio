import streamlit as st
import os
import re
from datetime import datetime
from dotenv import load_dotenv
import pipeline

# Attempt to import google api core exceptions for specific 429 catching
try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:
    ResourceExhausted = Exception

# Load environment variables (e.g., GOOGLE_API_KEY)
load_dotenv()

st.set_page_config(page_title="AI Studio - Nano Banana Pro", layout="wide")

st.title("🎬 Multi-Agent AI Studio")
st.markdown("### 30-Second Short-Form Visual Storytelling Workflow")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Configuration")
engine_mode = st.sidebar.radio(
    "Engine Mode:",
    ["Cloud", "Local"],
    help="Cloud uses Google Gemini. Local uses Ollama."
)

if engine_mode == "Cloud":
    intelligence_selector = st.sidebar.selectbox(
        "Intelligence Engine (Cloud):",
        ["Gemini 1.5 Flash (Fast/High Quota)", "Gemini 1.5 Pro (High Reasoning/Lower Quota)"]
    )
    if "Flash" in intelligence_selector:
        model_name = "gemini-3-flash-preview"
    else:
        model_name = "gemini-3.1-pro-preview"
else:
    model_name = "local-model" # pipeline.py hardcodes gemma3/qwen2.5 for local

# --- SESSION STATE INITIALIZATION ---
if "phase" not in st.session_state:
    st.session_state.phase = 0
if "story_arc" not in st.session_state:
    st.session_state.story_arc = ""
if "screenplay" not in st.session_state:
    st.session_state.screenplay = ""
if "consultant_suggestions" not in st.session_state:
    st.session_state.consultant_suggestions = ""
if "generation_seed" not in st.session_state:
    st.session_state.generation_seed = 1
if "concept_input" not in st.session_state:
    st.session_state.concept_input = ""
if "art_input" not in st.session_state:
    st.session_state.art_input = ""
if "camera_input" not in st.session_state:
    st.session_state.camera_input = ""
if "final_prompts" not in st.session_state:
    st.session_state.final_prompts = ""
if "last_seed" not in st.session_state:
    st.session_state.last_seed = 0

# --- SIDEBAR: PRE-PRODUCTION ---
st.sidebar.divider()
st.sidebar.subheader("Phase 1: Pre-Production")
st.sidebar.text_area("Enter your story concept:", key="concept_input", placeholder="A cyberpunk detective chases a rogue android through neon-lit streets...")

if st.sidebar.button("Generate Pre-Production"):
    if not st.session_state.concept_input:
        st.sidebar.warning("Please enter a story concept first.")
    else:
        with st.spinner(f"Agents are writing using {model_name}..."):
            try:
                arc, script, suggestions = pipeline.run_phase_1(st.session_state.concept_input, engine_mode=engine_mode, model_name=model_name)
                st.session_state.story_arc = arc
                st.session_state.screenplay = script
                st.session_state.consultant_suggestions = suggestions
                st.session_state.phase = 1
                st.rerun()
            except ResourceExhausted:
                st.sidebar.error("Quota exceeded. Please switch to Gemini 1.5 Flash.")
            except Exception as e:
                st.sidebar.error(f"Error during Phase 1: {e}")

# --- SIDEBAR: PRODUCTION PREFERENCES ---
if st.session_state.phase >= 1:
    st.sidebar.divider()
    st.sidebar.subheader("Human-In-The-Loop: Production Preferences")
    st.sidebar.markdown("Leave blank to let agents auto-decide based on consultant suggestions.")
    
    st.sidebar.text_input("Art Preferences:", key="art_input", placeholder="e.g., Cyberpunk Neon, gritty")
    st.sidebar.text_input("Camera Preferences:", key="camera_input", placeholder="e.g., Handheld Documentary")
    
    if st.sidebar.button("Continue to Phase 2: Production"):
        st.session_state.phase = 2
        st.rerun()

# --- SIDEBAR: RESET & RESEED ---
st.sidebar.divider()
reset_disabled = st.session_state.phase == 0
if st.sidebar.button("Start Another Story (Reset)", disabled=reset_disabled):
    keys_to_delete = [
        "phase", "story_arc", "screenplay", "consultant_suggestions", 
        "generation_seed", "concept_input", "art_input", "camera_input",
        "story_concept", "final_prompts", "last_seed" # Legacy key just in case
    ]
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

if st.session_state.phase == 2:
    if st.sidebar.button("Generate from another seed"):
        st.session_state.generation_seed += 1
        st.rerun()

# --- MAIN PANEL ---
if st.session_state.phase == 0:
    st.info("👈 Enter your concept in the sidebar to begin.")
    
elif st.session_state.phase == 1:
    st.subheader("Phase 1: Pre-Production Review")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("📝 Story Arc", expanded=True):
            st.write(st.session_state.story_arc)
        with st.expander("🎬 Screenplay", expanded=True):
            st.write(st.session_state.screenplay)
            
    with col2:
        with st.expander("💡 Creative Consultant Suggestions", expanded=True):
            st.write(st.session_state.consultant_suggestions)
            
elif st.session_state.phase == 2:
    st.subheader("Phase 2: Production (Finalizing Prompts)")
    
    # We display phase 1 stuff collapsibly so it isn't lost
    with st.expander("View Pre-Production Details"):
        st.write("**Screenplay:**\n", st.session_state.screenplay)
    
    with st.spinner(f"Art Director, Cinematographer, and Render Artist are working... (Seed: {st.session_state.generation_seed})"):
        try:
            if st.session_state.last_seed != st.session_state.generation_seed:
                # We append a hidden seed text to the end of the screenplay just to force the LLM to process it slightly differently
                seeded_screenplay = st.session_state.screenplay + f"\n[Hidden System Note: Procedural generation variant {st.session_state.generation_seed}]"
                
                final_prompts_output = pipeline.run_phase_2(
                    seeded_screenplay,
                    st.session_state.art_input,
                    st.session_state.camera_input,
                    engine_mode=engine_mode,
                    model_name=model_name
                )
                
                st.session_state.final_prompts = final_prompts_output
                st.session_state.last_seed = st.session_state.generation_seed
                
            st.success(f"Workflow Complete! (Variant {st.session_state.generation_seed})")
            
            st.markdown("### 🍌 Nano Banana Pro Rendering Prompts")
            # Display final prompts formatted as code for easy copy/paste
            st.code(st.session_state.final_prompts, language="markdown")
            
            # --- SAVING LOGIC ---
            slug = re.sub(r'[^a-zA-Z0-9\s]', '', st.session_state.concept_input)
            slug = "_".join(slug.split()[:3]).lower()
            if not slug:
                slug = "story"
                
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"{date_str}_{slug}_v{st.session_state.generation_seed}.md"
            filepath = os.path.join("outputs", filename)
            
            os.makedirs("outputs", exist_ok=True)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(st.session_state.final_prompts)
            
            with open(filepath, "r", encoding="utf-8") as f:
                md_data = f.read()

            st.download_button(
                label="📥 Download .md",
                data=md_data,
                file_name=filename,
                mime="text/markdown"
            )
            
        except ResourceExhausted:
            st.error("Quota exceeded for the selected model. Please switch to Gemini 1.5 Flash in the sidebar.")
        except Exception as e:
            st.error(f"Error during Phase 2: {e}")
