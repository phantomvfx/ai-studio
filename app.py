import streamlit as st
import os
import re
from datetime import datetime
from dotenv import load_dotenv
import json
import pipeline

# Attempt to catch specific 429 exceptions gracefully
try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:
    ResourceExhausted = Exception

load_dotenv()

st.set_page_config(page_title="AI Studio", layout="wide")

if os.path.exists("logo.png"):
    try:
        st.logo("logo.png", size="large")
    except Exception:
        pass # In case it's an invalid image type or corrupted

st.title("🎬 Multi-Agent AI Studio")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Configuration")

workflow_mode = st.sidebar.radio(
    "Workflow Mode:",
    ["30-Second Storytelling", "Product Shot"],
    help="Storytelling takes you through a 3-phase creative process. Product Shot delivers a 1-shot API JSON output."
)

# Detect if running on Streamlit Community Cloud
# Streamlit injects `HOSTNAME` or `STREAMLIT_SERVER_PORT` for its cloud containers typically
# A safer way to check Streamlit Cloud specifically is `st.secrets` or checking standard cloud envs
is_streamlit_cloud = os.environ.get('STREAMLIT_SHARING_MODE') is not None or os.environ.get('HOSTNAME', '').startswith('localhost') == False and os.environ.get('USER') == 'appuser'

if is_streamlit_cloud:
    st.sidebar.info("☁️ **Running in Cloud Mode** (Local GPU routing is disabled on this server).")
    engine_mode = "Cloud"
else:
    engine_mode = st.sidebar.radio(
        "Engine Mode:",
        ["Cloud", "Local"],
        help="Cloud uses Google Gemini. Local uses Ollama."
    )

# API Key handling for Cloud
api_key = None
if engine_mode == "Cloud":
    intelligence_selector = st.sidebar.selectbox(
        "Intelligence Engine (Cloud):",
        [
            "Gemini 3.1 Flash Preview (Fast/High Quota)", 
            "Gemini 3.1 Pro Preview (High Reasoning/Lower Quota)",
            "Gemini 2.5 Flash",
            "Gemini 2.5 Pro"
        ]
    )
    if "3.1 Flash" in intelligence_selector:
        model_name = "gemini-3-flash-preview"
    elif "3.1 Pro" in intelligence_selector:
        model_name = "gemini-3.1-pro-preview"
    elif "2.5 Flash" in intelligence_selector:
        model_name = "gemini-2.5-flash"
    elif "2.5 Pro" in intelligence_selector:
        model_name = "gemini-2.5-pro"
        
    # Local .env vs BYO key logic depends on environment. We can just provide a field.
    env_key = os.getenv("GOOGLE_API_KEY")
    key_input = st.sidebar.text_input("Google API Key (Leave blank to use .env):", type="password")
    api_key = key_input if key_input else env_key
    
    if not api_key:
        st.sidebar.warning("Cloud mode requires a Google API Key.")
else:
    local_model_selector = st.sidebar.selectbox(
        "Intelligence Engine (Local):",
        ["qwen3-vl:8b", "qwen3.5:9b", "qwen3.5:cloud", "kimi-k2.5:cloud", "gemma3:12b", "gpt-oss:20b"],
        index=0  # Sets the first item as the default selection
    )
    if "qwen3-vl" in local_model_selector:
        model_name = "qwen3-vl:8b"
    elif "qwen3.5" in local_model_selector:
        if "cloud" in local_model_selector:
            model_name = "qwen3.5:cloud"
        else:
            model_name = "qwen3.5:9b"
    elif "kimi" in local_model_selector:
        model_name = "kimi-k2.5:cloud"
    elif "12b" in local_model_selector:
        model_name = "gemma3:12b"
    else:
        model_name = "gpt-oss:20b"

# --- SESSION STATE INITIALIZATION ---
session_vars = [
    "phase", "story_arc", "screenplay", "art_suggestions", "camera_suggestions",
    "generation_seed", "concept_input", "art_input", "camera_input",
    "final_art_pref", "final_cam_pref", "final_prompts", "storyboard_prompt",
    "last_seed", "product_shot_json", "preview_image_bytes", "last_uploaded_image"
]
for var in session_vars:
    if var not in st.session_state:
        st.session_state[var] = 0 if var in ["phase", "last_seed"] else (1 if var == "generation_seed" else ("" if var != "preview_image_bytes" and var != "last_uploaded_image" else None))

def reset_state():
    for key in session_vars:
        if key in st.session_state:
            st.session_state[key] = 0 if key in ["phase", "last_seed"] else (1 if key == "generation_seed" else ("" if key != "preview_image_bytes" and key != "last_uploaded_image" else None))

st.sidebar.divider()
st.sidebar.subheader("Concept Initialization")

uploaded_image = st.sidebar.file_uploader("Upload an Image Concept (Optional):", type=["jpg", "jpeg", "png"])
if uploaded_image is not None and st.session_state.get("last_uploaded_image") != uploaded_image.file_id:
    with st.spinner("Agents are analyzing image concept..."):
        try:
            caption = pipeline.describe_image(
                uploaded_image.getvalue(),
                engine_mode=engine_mode,
                api_key=api_key,
                mime_type=uploaded_image.type
            )
            st.session_state.concept_input = caption
            st.session_state.last_uploaded_image = uploaded_image.file_id
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Image analysis failed: {e}")

st.sidebar.text_area("Enter your concept:", key="concept_input", placeholder="A cyberpunk detective chases a rogue android through neon-lit streets...")

# -------------------------------------------------------------
# MODE 1: PRODUCT SHOT
# -------------------------------------------------------------
if workflow_mode == "Product Shot":
    st.markdown("### 📸 Product Shot")
    st.info("Generates a single, hyper-detailed product shot composition outputted as JSON for ComfyUI.")
    
    if st.sidebar.button("Generate Product Shot"):
        if not st.session_state.concept_input:
            st.sidebar.warning("Please enter a concept first.")
        else:
            with st.spinner(f"Agents are synthesizing product shot using {model_name}..."):
                try:
                    out_json = pipeline.run_product_shot_mode(
                        st.session_state.concept_input, 
                        engine_mode=engine_mode, 
                        model_name=model_name,
                        api_key=api_key
                    )
                    st.session_state.product_shot_json = out_json
                    st.session_state.preview_image_bytes = None # clear old preview
                except Exception as e:
                    st.error(f"Error during execution: {e}")
                    
    if st.session_state.product_shot_json:
        st.success("Product Shot synthesis complete.")
        # Parse prompt to send to image generator
        try:
            prompt_data = json.loads(st.session_state.product_shot_json)
            extracted_prompt = prompt_data.get("prompt", st.session_state.product_shot_json)
            i2v_prompt = prompt_data.pop("i2v_prompt", None)
            
            st.markdown("### 🍌 Nano Banana Pro Rendering Prompt")
            if i2v_prompt:
                st.markdown("**I2V Animation Prompt:**")
                st.code(i2v_prompt, language="markdown")
                
            with st.expander("Shot Details (JSON)", expanded=False):
                st.code(json.dumps(prompt_data, indent=2), language="json")
                
        except:
            st.markdown("### 🍌 Nano Banana Pro Rendering Prompt (JSON)")
            with st.expander("Shot Details (JSON)", expanded=False):
                st.code(st.session_state.product_shot_json, language="json")
            extracted_prompt = st.session_state.product_shot_json
            
        col_img1, col_img2 = st.columns(2)
        with col_img1:
            if st.button("Generate Image Preview via Gemini 2.5 Flash"):
                if engine_mode == "Cloud" and api_key:
                    with st.spinner("Generating Image Preview..."):
                        try:
                            img_bytes = pipeline.generate_image(extracted_prompt, api_key=api_key)
                            st.session_state.preview_image_bytes = img_bytes
                        except Exception as e:
                            st.error(f"Image Gen Error: {e}")
                else:
                    st.error("Image generation requires Cloud mode and a valid Google API Key.")
            
            if st.button("Generate Local Image (ComfyUI)"):
                with st.spinner("Dispatching to Local ComfyUI..."):
                    try:
                        img_bytes = pipeline.generate_image_comfyui(extracted_prompt)
                        st.session_state.preview_image_bytes = img_bytes
                        st.success("Successfully generated by ComfyUI!")
                    except Exception as e:
                        st.error(str(e))
                        
        with col_img2:
            if st.session_state.preview_image_bytes:
                st.image(st.session_state.preview_image_bytes, caption="Generated Preview")
                st.download_button(
                    label="📥 Download Preview Image",
                    data=st.session_state.preview_image_bytes,
                    file_name="product_shot_preview.jpg",
                    mime="image/jpeg"
                )

        st.markdown("### 📦 Deliverables")
        slug = re.sub(r'[^a-zA-Z0-9\s]', '', st.session_state.concept_input)
        slug = "_".join(slug.split()[:3]).lower() or "product_shot"
        date_str = datetime.now().strftime("%Y%m%d")
        
        md_content = f"# Product Shot API Output\n\n```json\n{st.session_state.product_shot_json}\n```"
        st.download_button(
            label="📥 Download Output (.md)",
            data=md_content,
            file_name=f"{date_str}_{slug}.md",
            mime="text/markdown"
        )


# -------------------------------------------------------------
# MODE 2: 30-SECOND STORYTELLING
# -------------------------------------------------------------
else:
    st.markdown("### 🎥 30-Second Short-Form Visual Storytelling Workflow")
    
    if st.sidebar.button("Generate Script"):
        if not st.session_state.concept_input:
            st.sidebar.warning("Please enter a concept first.")
        else:
            with st.spinner(f"Agents are writing using {model_name}..."):
                try:
                    arc, script, art_suggs = pipeline.run_phase_1(
                        st.session_state.concept_input, 
                        engine_mode=engine_mode, 
                        model_name=model_name,
                        api_key=api_key
                    )
                    st.session_state.story_arc = arc
                    st.session_state.screenplay = script
                    st.session_state.art_suggestions = art_suggs
                    st.session_state.phase = 1
                except Exception as e:
                    st.sidebar.error(f"Error during Phase 1: {e}")

    # Sidebars for phases
    if st.session_state.phase >= 1:
        st.sidebar.divider()
        st.sidebar.subheader("Phase 1.5: Art Direction")
        art_choice = st.sidebar.radio("Art Selection:", ["Option 1", "Option 2", "Option 3", "Custom User Input"], disabled=(st.session_state.phase >= 2))
        art_input = ""
        if art_choice == "Custom User Input":
            art_input = st.sidebar.text_area("Custom Art Preferences:", disabled=(st.session_state.phase >= 2))
        
        if st.session_state.phase == 1:
            if st.sidebar.button("Confirm Art & Generate Camera Options"):
                final_art_pref = art_input if art_choice == "Custom User Input" else f"{art_choice} from previous suggestions."
                st.session_state.final_art_pref = final_art_pref
                
                with st.spinner(f"Camera Consultant is working using {model_name}..."):
                    try:
                        cam_suggs = pipeline.run_phase_1_5(
                            st.session_state.screenplay, 
                            st.session_state.final_art_pref, 
                            engine_mode=engine_mode, 
                            model_name=model_name,
                            api_key=api_key
                        )
                        st.session_state.camera_suggestions = cam_suggs
                        st.session_state.phase = 2
                    except Exception as e:
                        st.sidebar.error(f"Error during Phase 1.5: {e}")

    if st.session_state.phase >= 2:
        st.sidebar.divider()
        st.sidebar.subheader("Phase 2: Cinematography")
        cam_choice = st.sidebar.radio("Camera Selection:", ["Option A", "Option B", "Option C", "Custom User Input"], disabled=(st.session_state.phase >= 3))
        cam_input = ""
        if cam_choice == "Custom User Input":
            cam_input = st.sidebar.text_area("Custom Camera Preferences:", disabled=(st.session_state.phase >= 3))
        
        if st.session_state.phase == 2:
            if st.sidebar.button("Generate Final Prompts"):
                final_cam_pref = cam_input if cam_choice == "Custom User Input" else f"{cam_choice} from previous suggestions."
                st.session_state.final_cam_pref = final_cam_pref
                st.session_state.phase = 3

    # Main Panel Rendering
    if st.session_state.phase == 0:
        st.info("👈 Enter your concept in the sidebar to begin.")
        
    elif st.session_state.phase == 1:
        st.subheader("Phase 1: Pre-Production Review")
        col1, col2 = st.columns(2)
        with col1:
            with st.expander("📝 Story Arc", expanded=True): st.write(st.session_state.story_arc)
            with st.expander("🎬 Screenplay", expanded=True): st.write(st.session_state.screenplay)
        with col2:
            with st.expander("💡 Art Director Suggestions", expanded=True): st.write(st.session_state.art_suggestions)
                
    elif st.session_state.phase == 2:
        st.subheader("Phase 1.5: Cinematography Review")
        col1, col2 = st.columns(2)
        with col1:
            with st.expander("View Screenplay"): st.write(st.session_state.screenplay)
            with st.expander("🎨 Chosen Art Direction", expanded=True): st.write(st.session_state.final_art_pref)
        with col2:
            with st.expander("🎥 Cinematographer Suggestions", expanded=True): st.write(st.session_state.camera_suggestions)
                
    elif st.session_state.phase == 3:
        st.subheader("Phase 2: Production (Finalizing Prompts)")
        
        with st.spinner(f"Render Artist is working... (Seed: {st.session_state.generation_seed})"):
            try:
                if st.session_state.last_seed != st.session_state.generation_seed:
                    seeded_screenplay = st.session_state.screenplay + f"\n[Variant {st.session_state.generation_seed}]"
                    r_prompts, s_prompt = pipeline.run_phase_2(
                        seeded_screenplay,
                        st.session_state.final_art_pref,
                        st.session_state.final_cam_pref,
                        engine_mode=engine_mode,
                        model_name=model_name,
                        api_key=api_key
                    )
                    st.session_state.final_prompts = r_prompts
                    st.session_state.storyboard_prompt = s_prompt
                    st.session_state.last_seed = st.session_state.generation_seed
                    st.session_state.preview_image_bytes = None
                
                st.success(f"Workflow Complete! (Variant {st.session_state.generation_seed})")
                
                st.markdown("### 🍌 Nano Banana Pro Rendering Prompts")
                
                # Parse final prompts as JSON (Array of objects)
                formatted_prompts = ""
                try:
                    # Clean potential markdown wrapping from LLM
                    raw_json = st.session_state.final_prompts.replace("```json", "").replace("```", "").strip()
                    prompts_list = json.loads(raw_json)
                    
                    if isinstance(prompts_list, dict) and "scenes" in prompts_list:
                        prompts_list = prompts_list["scenes"]
                        
                    if isinstance(prompts_list, list):
                        for scene_data in prompts_list:
                            scene_label = scene_data.pop("scene_label", "Scene")
                            i2v_prompt = scene_data.pop("i2v_prompt", None)
                            
                            st.markdown(f"### {scene_label}")
                            if i2v_prompt:
                                st.markdown("**I2V Animation Prompt:**")
                                st.code(i2v_prompt, language="markdown")
                                formatted_prompts += f"**{scene_label} I2V Prompt:**\n```markdown\n{i2v_prompt}\n```\n\n"
                                
                            with st.expander("Shot Details (JSON)", expanded=False):
                                scene_json_str = json.dumps(scene_data, indent=2)
                                st.code(scene_json_str, language="json")
                                
                            formatted_prompts += f"**{scene_label} JSON:**\n```json\n{scene_json_str}\n```\n\n"
                    else:
                        with st.expander("Raw Output (JSON)", expanded=False):
                            st.code(raw_json, language="json")
                        formatted_prompts = st.session_state.final_prompts
                except Exception as parse_err:
                    # Fallback if the LLM completely failed to output valid JSON
                    st.warning("Failed to parse output as strict JSON. Displaying raw output.")
                    with st.expander("Raw Output", expanded=False):
                        st.code(st.session_state.final_prompts, language="json")
                    formatted_prompts = st.session_state.final_prompts
                
                st.markdown("### 🖼️ Storyboard Consolidation Prompt")
                st.code(st.session_state.storyboard_prompt, language="markdown")
                
                col_img1, col_img2 = st.columns(2)
                with col_img1:
                    if st.button("Generate Storyboard Preview via Gemini 2.5 Flash"):
                        if engine_mode == "Cloud" and api_key:
                            with st.spinner("Generating Storyboard Image Preview..."):
                                try:
                                    img_bytes = pipeline.generate_image(st.session_state.storyboard_prompt, api_key=api_key)
                                    st.session_state.preview_image_bytes = img_bytes
                                except Exception as e:
                                    st.error(f"Image Gen Error: {e}")
                        else:
                            st.error("Image generation requires Cloud mode and a valid Google API Key.")

                    if st.button("Generate Local Image (ComfyUI)"):
                        with st.spinner("Dispatching Storyboard to Local ComfyUI..."):
                            try:
                                img_bytes = pipeline.generate_image_comfyui(st.session_state.storyboard_prompt)
                                st.session_state.preview_image_bytes = img_bytes
                                st.success("Successfully generated by ComfyUI!")
                            except Exception as e:
                                st.error(str(e))
                                
                with col_img2:
                    if st.session_state.preview_image_bytes:
                        st.image(st.session_state.preview_image_bytes, caption="Generated Storyboard")
                        st.download_button(
                            label="📥 Download Storyboard Image",
                            data=st.session_state.preview_image_bytes,
                            file_name="storyboard_preview.jpg",
                            mime="image/jpeg"
                        )
                
                st.markdown("### 📦 Deliverables")
                slug = re.sub(r'[^a-zA-Z0-9\s]', '', st.session_state.concept_input)
                slug = "_".join(slug.split()[:3]).lower() or "story"
                date_str = datetime.now().strftime("%Y%m%d")
                
                md_content = (
                    f"# Original Concept\n\n{st.session_state.concept_input}\n\n"
                    f"# Phase 1: Pre-Production\n\n"
                    f"## Story Arc\n\n{st.session_state.story_arc}\n\n"
                    f"## Screenplay\n\n{st.session_state.screenplay}\n\n"
                    f"## Art Director Suggestions\n\n{st.session_state.art_suggestions}\n\n"
                    f"## Chosen Art Direction\n\n{st.session_state.final_art_pref}\n\n"
                    f"# Phase 1.5: Cinematography\n\n"
                    f"## Cinematographer Suggestions\n\n{st.session_state.camera_suggestions}\n\n"
                    f"## Chosen Cinematography\n\n{st.session_state.final_cam_pref}\n\n"
                    f"# Phase 2: Production\n\n"
                    f"## Full Production Script (JSON / Final Prompts)\n\n{formatted_prompts}\n\n"
                    f"## Storyboard Prompt\n\n{st.session_state.storyboard_prompt}"
                )
                
                st.download_button(
                    label="📥 Download Full Package (.md)",
                    data=md_content,
                    file_name=f"{date_str}_{slug}_Complete.md",
                    mime="text/markdown"
                )
                
            except Exception as e:
                st.error(f"Error during Phase 2: {e}")

# --- RESET CONTROLS ---
st.sidebar.divider()
reset_disabled = st.session_state.phase == 0 and not st.session_state.product_shot_json
if st.sidebar.button("Start Another Run (Reset)", disabled=reset_disabled):
    reset_state()
    st.rerun()

if workflow_mode == "30-Second Storytelling" and st.session_state.phase == 3:
    if st.sidebar.button("Generate from another seed"):
        st.session_state.generation_seed += 1
        st.rerun()

st.sidebar.divider()
if not is_streamlit_cloud:
    if st.sidebar.button("🚪 Exit / Close Studio"):
        os._exit(0)
