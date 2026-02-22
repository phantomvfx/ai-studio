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
if "art_suggestions" not in st.session_state:
    st.session_state.art_suggestions = ""
if "camera_suggestions" not in st.session_state:
    st.session_state.camera_suggestions = ""
if "generation_seed" not in st.session_state:
    st.session_state.generation_seed = 1
if "concept_input" not in st.session_state:
    st.session_state.concept_input = ""
if "art_input" not in st.session_state:
    st.session_state.art_input = ""
if "camera_input" not in st.session_state:
    st.session_state.camera_input = ""
if "final_art_pref" not in st.session_state:
    st.session_state.final_art_pref = ""
if "final_cam_pref" not in st.session_state:
    st.session_state.final_cam_pref = ""
if "final_prompts" not in st.session_state:
    st.session_state.final_prompts = ""
if "storyboard_prompt" not in st.session_state:
    st.session_state.storyboard_prompt = ""
if "last_seed" not in st.session_state:
    st.session_state.last_seed = 0

# --- SIDEBAR: PRE-PRODUCTION ---
st.sidebar.divider()
st.sidebar.subheader("Phase 1: Pre-Production")
st.sidebar.text_area("Enter your story concept:", key="concept_input", placeholder="A cyberpunk detective chases a rogue android through neon-lit streets...")

if st.sidebar.button("Generate Script"):
    if not st.session_state.concept_input:
        st.sidebar.warning("Please enter a story concept first.")
    else:
        with st.spinner(f"Agents are writing using {model_name}..."):
            try:
                arc, script, art_suggs = pipeline.run_phase_1(st.session_state.concept_input, engine_mode=engine_mode, model_name=model_name)
                st.session_state.story_arc = arc
                st.session_state.screenplay = script
                st.session_state.art_suggestions = art_suggs
                st.session_state.phase = 1
                st.rerun()
            except ResourceExhausted:
                st.sidebar.error("Quota exceeded. Please switch to Gemini 1.5 Flash.")
            except Exception as e:
                st.sidebar.error(f"Error during Phase 1: {e}")

# --- SIDEBAR: ART DIRECTION PREFERENCES ---
if st.session_state.phase >= 1:
    st.sidebar.divider()
    st.sidebar.subheader("Phase 1.5: Art Direction")
    st.sidebar.markdown("Choose an Art Direction option from the main panel, or type your own.")
    
    art_choice = st.sidebar.radio("Art Selection:", ["Option 1", "Option 2", "Option 3", "Custom User Input"], disabled=(st.session_state.phase >= 2))
    
    art_input = ""
    if art_choice == "Custom User Input":
        art_input = st.sidebar.text_area("Custom Art Preferences:", placeholder="e.g., Cyberpunk Neon, gritty", disabled=(st.session_state.phase >= 2))
    
    if st.session_state.phase == 1:
        if st.sidebar.button("Confirm Art & Generate Camera Options"):
            if art_choice != "Custom User Input":
                option_num = art_choice.split(" ")[1]
                pattern = rf"(?is)\*\*Option\s+{option_num}.*?(?=\*\*Option\s+{int(option_num)+1}|---|$)"
                match = re.search(pattern, st.session_state.art_suggestions)
                if match:
                    final_art_pref = match.group(0).strip()
                else:
                    final_art_pref = f"{art_choice} from previous suggestions."
            else:
                final_art_pref = art_input
                
            st.session_state.final_art_pref = final_art_pref
            
            with st.spinner(f"Camera Consultant is working using {model_name}..."):
                try:
                    cam_suggs = pipeline.run_phase_1_5(st.session_state.screenplay, st.session_state.final_art_pref, engine_mode=engine_mode, model_name=model_name)
                    st.session_state.camera_suggestions = cam_suggs
                    st.session_state.phase = 2
                    st.rerun()
                except ResourceExhausted:
                    st.sidebar.error("Quota exceeded. Please switch to Gemini 1.5 Flash.")
                except Exception as e:
                    st.sidebar.error(f"Error during Phase 1.5: {e}")

# --- SIDEBAR: CAMERA PREFERENCES ---
if st.session_state.phase >= 2:
    st.sidebar.divider()
    st.sidebar.subheader("Phase 2: Cinematography")
    st.sidebar.markdown("Choose a Camera option from the main panel, or type your own.")
    
    cam_choice = st.sidebar.radio("Camera Selection:", ["Option A", "Option B", "Option C", "Custom User Input"], disabled=(st.session_state.phase >= 3))
    
    cam_input = ""
    if cam_choice == "Custom User Input":
        cam_input = st.sidebar.text_area("Custom Camera Preferences:", placeholder="e.g., Handheld Documentary", disabled=(st.session_state.phase >= 3))
    
    if st.session_state.phase == 2:
        if st.sidebar.button("Generate Final Prompts"):
            if cam_choice != "Custom User Input":
                option_letter = cam_choice.split(" ")[1]
                next_letter = chr(ord(option_letter) + 1)
                pattern = rf"(?is)\*\*Option\s+{option_letter}.*?(?=\*\*Option\s+{next_letter}|---|$)"
                match = re.search(pattern, st.session_state.camera_suggestions)
                if match:
                    final_cam_pref = match.group(0).strip()
                else:
                    final_cam_pref = f"{cam_choice} from previous suggestions."
            else:
                final_cam_pref = cam_input
                
            st.session_state.final_cam_pref = final_cam_pref
            st.session_state.phase = 3
            st.rerun()

# --- SIDEBAR: RESET & RESEED ---
st.sidebar.divider()
reset_disabled = st.session_state.phase == 0
if st.sidebar.button("Start Another Story (Reset)", disabled=reset_disabled):
    keys_to_delete = [
        "phase", "story_arc", "screenplay", "art_suggestions", "camera_suggestions", 
        "generation_seed", "concept_input", "art_input", "camera_input", "final_art_pref", "final_cam_pref",
        "story_concept", "final_prompts", "storyboard_prompt", "last_seed" # Legacy key just in case
    ]
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

if st.session_state.phase == 3:
    if st.sidebar.button("Generate from another seed"):
        st.session_state.generation_seed += 1
        st.rerun()

st.sidebar.divider()
if st.sidebar.button("🚪 Exit / Close Studio"):
    os._exit(0)

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
        with st.expander("💡 Art Director Suggestions", expanded=True):
            st.write(st.session_state.art_suggestions)
            
elif st.session_state.phase == 2:
    st.subheader("Phase 1.5: Cinematography Review")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("View Pre-Production Details"):
            st.write("**Screenplay:**\n", st.session_state.screenplay)
        with st.expander("🎨 Chosen Art Direction", expanded=True):
            st.write(st.session_state.final_art_pref)
            
    with col2:
        with st.expander("🎥 Cinematographer Suggestions", expanded=True):
            st.write(st.session_state.camera_suggestions)
            
elif st.session_state.phase == 3:
    st.subheader("Phase 2: Production (Finalizing Prompts)")
    
    # We display phase 1 stuff collapsibly so it isn't lost
    with st.expander("View Pre-Production & Choices Details"):
        st.write("**Screenplay:**\n", st.session_state.screenplay)
        st.write("**Chosen Art Direction:**\n", st.session_state.final_art_pref)
        st.write("**Chosen Cinematography:**\n", st.session_state.final_cam_pref)
    
    with st.spinner(f"Art Director, Cinematographer, and Render Artist are working... (Seed: {st.session_state.generation_seed})"):
        try:
            if st.session_state.last_seed != st.session_state.generation_seed:
                # We append a hidden seed text to the end of the screenplay just to force the LLM to process it slightly differently
                seeded_screenplay = st.session_state.screenplay + f"\n[Hidden System Note: Procedural generation variant {st.session_state.generation_seed}]"
                
                render_prompts_output, storyboard_prompt_output = pipeline.run_phase_2(
                    seeded_screenplay,
                    st.session_state.final_art_pref,
                    st.session_state.final_cam_pref,
                    engine_mode=engine_mode,
                    model_name=model_name
                )
                
                st.session_state.final_prompts = render_prompts_output
                st.session_state.storyboard_prompt = storyboard_prompt_output
                st.session_state.last_seed = st.session_state.generation_seed
                
            st.success(f"Workflow Complete! (Variant {st.session_state.generation_seed})")
            
            st.markdown("### 🍌 Nano Banana Pro Rendering Prompts")
            # Display final prompts formatted as code for easy copy/paste
            st.code(st.session_state.final_prompts, language="markdown")
            
            st.markdown("### 🖼️ Storyboard Consolidation Prompt")
            st.code(st.session_state.storyboard_prompt, language="markdown")
            
            # --- SAVING LOGIC & FINAL DELIVERABLES ---
            st.markdown("### 📦 Final Deliverables")
            
            slug = re.sub(r'[^a-zA-Z0-9\s]', '', st.session_state.concept_input)
            slug = "_".join(slug.split()[:3]).lower()
            if not slug:
                slug = "story"
                
            date_str = datetime.now().strftime("%Y%m%d")
            script_filename = f"{date_str}_{slug}_Script.md"
            storyboard_filename = f"{date_str}_{slug}_Storyboard.md"
            
            script_filepath = os.path.join("outputs", script_filename)
            storyboard_filepath = os.path.join("outputs", storyboard_filename)
            
            os.makedirs("outputs", exist_ok=True)
            
            with open(script_filepath, "w", encoding="utf-8") as f:
                f.write(st.session_state.final_prompts)
                
            with open(storyboard_filepath, "w", encoding="utf-8") as f:
                f.write(st.session_state.storyboard_prompt)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.download_button(
                    label="📥 Download Full Production Script (.md)",
                    data=st.session_state.final_prompts,
                    file_name=script_filename,
                    mime="text/markdown"
                )
            with col_b:
                st.download_button(
                    label="📥 Download Storyboard Prompt (.md)",
                    data=st.session_state.storyboard_prompt,
                    file_name=storyboard_filename,
                    mime="text/markdown"
                )
            
        except ResourceExhausted:
            st.error("Quota exceeded for the selected model. Please switch to Gemini 1.5 Flash in the sidebar.")
        except Exception as e:
            st.error(f"Error during Phase 2: {e}")
