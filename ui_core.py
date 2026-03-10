"""
ui_core.py — Shared workflow UI for AI Studio.
Called by app.py (cloud) and applocal.py (local) with pre-configured engine settings.
"""
import streamlit as st
import re
from datetime import datetime
import pipeline

# Attempt to catch specific 429 exceptions gracefully
try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:
    ResourceExhausted = Exception


def _parse_t2i_i2v(block: str):
    """
    Extract T2I and I2V text from a single scene block.
    Returns (t2i_text, i2v_text) — either may be empty string.
    """
    t2i_match = re.search(
        r'\*\*T2I Prompt:\*\*\s*\n(.*?)(?=\n\*\*I2V Animation Prompt:|$)',
        block, re.DOTALL | re.IGNORECASE
    )
    i2v_match = re.search(
        r'\*\*I2V Animation Prompt:\*\*\s*\n(.*?)$',
        block, re.DOTALL | re.IGNORECASE
    )

    def clean(text):
        # Strip blockquote markers and excess whitespace
        lines = [l.lstrip('> ').rstrip() for l in text.strip().splitlines()]
        return '\n'.join(lines).strip()

    t2i = clean(t2i_match.group(1)) if t2i_match else ""
    i2v = clean(i2v_match.group(1)) if i2v_match else ""
    return t2i, i2v


def render_prompt_blocks(output_text: str):
    """
    Parse render artist output and display T2I and I2V in separate
    st.code() boxes (with built-in copy button).
    Handles both single-scene (Product Shot) and multi-scene (Storytelling) output.
    """
    # Try to detect multi-scene output by looking for ### Scene headers
    scene_pattern = re.compile(r'(###\s+Scene\s+\d+[^\n]*)', re.IGNORECASE)
    parts = scene_pattern.split(output_text.strip())

    if len(parts) > 1:
        # Multi-scene: parts alternate as [preamble, header, content, header, content ...]
        for i in range(1, len(parts), 2):
            header = parts[i].strip().lstrip('#').strip()
            content = parts[i + 1].strip() if i + 1 < len(parts) else ""
            st.markdown(f"#### 🎬 {header}")
            t2i, i2v = _parse_t2i_i2v(content)
            if t2i:
                st.caption("🖼 T2I Prompt — copy and paste into your image model")
                st.code(t2i, language="markdown")
            if i2v:
                st.caption("🎞 I2V Animation Prompt — copy and paste into your video model")
                st.code(i2v, language="markdown")
            if not t2i and not i2v:
                st.code(content, language="markdown")
            st.divider()
    else:
        # Single scene (Product Shot)
        t2i, i2v = _parse_t2i_i2v(output_text)
        if t2i:
            st.caption("🖼 T2I Prompt — copy and paste into your image model")
            st.code(t2i, language="markdown")
        if i2v:
            st.caption("🎞 I2V Animation Prompt — copy and paste into your video model")
            st.code(i2v, language="markdown")
        if not t2i and not i2v:
            # Fallback — show raw output
            st.code(output_text, language="markdown")


def init_session_state():
    session_vars = [
        "phase", "story_arc", "screenplay", "art_suggestions", "camera_suggestions",
        "generation_seed", "concept_input", "art_input", "camera_input",
        "final_art_pref", "final_cam_pref", "final_prompts", "storyboard_prompt",
        "last_seed", "product_shot_output", "preview_image_bytes", "last_uploaded_image"
    ]
    for var in session_vars:
        if var not in st.session_state:
            st.session_state[var] = (
                0 if var in ["phase", "last_seed"]
                else (1 if var == "generation_seed"
                      else ("" if var not in ["preview_image_bytes", "last_uploaded_image"]
                            else None))
            )
    return session_vars


def reset_state(session_vars):
    for key in session_vars:
        if key in st.session_state:
            st.session_state[key] = (
                0 if key in ["phase", "last_seed"]
                else (1 if key == "generation_seed"
                      else ("" if key not in ["preview_image_bytes", "last_uploaded_image"]
                            else None))
            )


def render_concept_sidebar(engine_mode, api_key):
    """Image upload + concept text area."""
    st.sidebar.divider()
    st.sidebar.subheader("Concept Initialization")

    uploaded_image = st.sidebar.file_uploader(
        "Upload an Image Concept (Optional):", type=["jpg", "jpeg", "png"]
    )
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

    st.sidebar.text_area(
        "Enter your concept:",
        key="concept_input",
        placeholder="A cyberpunk detective chases a rogue android through neon-lit streets..."
    )


def render_product_shot(engine_mode, model_name, api_key):
    """Product Shot workflow UI."""
    st.markdown("### 📸 Product Shot")
    st.info("Generates a single, hyper-detailed product shot — T2I prompt + I2V animation instruction.")
    st.info("👈 Enter your concept in the sidebar to begin.")

    if st.sidebar.button("Generate Product Shot"):
        if not st.session_state.concept_input:
            st.sidebar.warning("Please enter a concept first.")
        else:
            with st.spinner(f"Agents are synthesizing product shot using {model_name}..."):
                try:
                    out = pipeline.run_product_shot_mode(
                        st.session_state.concept_input,
                        engine_mode=engine_mode,
                        model_name=model_name,
                        api_key=api_key
                    )
                    st.session_state.product_shot_output = out
                    st.session_state.preview_image_bytes = None
                except Exception as e:
                    st.error(f"Error during execution: {e}")

    if st.session_state.product_shot_output:
        st.success("Product Shot synthesis complete.")
        st.markdown("### 🍌 Nano Banana Pro Rendering Prompt")
        render_prompt_blocks(st.session_state.product_shot_output)

        extracted_prompt = st.session_state.product_shot_output

        col_img1, col_img2 = st.columns(2)
        with col_img1:
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
        md_content = f"# Product Shot Prompt\n\n{st.session_state.product_shot_output}"
        st.download_button(
            label="📥 Download Output (.md)",
            data=md_content,
            file_name=f"{date_str}_{slug}.md",
            mime="text/markdown"
        )


def render_storytelling(engine_mode, model_name, api_key):
    """Storytelling multi-phase workflow UI."""
    st.markdown("### 🎥 Storytelling Workflow")
    st.info("Guides you through a 3-phase creative process from narrative conceptualization to a multi-shot storyboard script.")
    st.info("👈 Enter your concept in the sidebar to begin.")

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

    # Phase 1.5 sidebar
    if st.session_state.phase >= 1:
        st.sidebar.divider()
        st.sidebar.subheader("Phase 1.5: Art Direction")
        art_choice = st.sidebar.radio(
            "Art Selection:",
            ["Option 1", "Option 2", "Option 3", "Custom User Input"],
            disabled=(st.session_state.phase >= 2)
        )
        art_input = ""
        if art_choice == "Custom User Input":
            art_input = st.sidebar.text_area(
                "Custom Art Preferences:", disabled=(st.session_state.phase >= 2)
            )

        if st.session_state.phase == 1:
            if st.sidebar.button("Confirm Art & Generate Camera Options"):
                final_art_pref = (
                    art_input if art_choice == "Custom User Input"
                    else f"{art_choice} from previous suggestions."
                )
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

    # Phase 2 sidebar
    if st.session_state.phase >= 2:
        st.sidebar.divider()
        st.sidebar.subheader("Phase 2: Cinematography")
        cam_choice = st.sidebar.radio(
            "Camera Selection:",
            ["Option A", "Option B", "Option C", "Custom User Input"],
            disabled=(st.session_state.phase >= 3)
        )
        cam_input = ""
        if cam_choice == "Custom User Input":
            cam_input = st.sidebar.text_area(
                "Custom Camera Preferences:", disabled=(st.session_state.phase >= 3)
            )

        if st.session_state.phase == 2:
            if st.sidebar.button("Generate Final Prompts"):
                final_cam_pref = (
                    cam_input if cam_choice == "Custom User Input"
                    else f"{cam_choice} from previous suggestions."
                )
                st.session_state.final_cam_pref = final_cam_pref
                st.session_state.phase = 3

    # --- Main panel ---
    if st.session_state.phase == 1:
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
            with st.expander("View Screenplay"):
                st.write(st.session_state.screenplay)
            with st.expander("🎨 Chosen Art Direction", expanded=True):
                st.write(st.session_state.final_art_pref)
        with col2:
            with st.expander("🎥 Cinematographer Suggestions", expanded=True):
                st.write(st.session_state.camera_suggestions)

    elif st.session_state.phase == 3:
        st.subheader("Phase 2: Production (Finalizing Prompts)")

        with st.spinner(f"Render Artist is working... (Seed: {st.session_state.generation_seed})"):
            try:
                if st.session_state.last_seed != st.session_state.generation_seed:
                    seeded_screenplay = (
                        st.session_state.screenplay
                        + f"\n[Variant {st.session_state.generation_seed}]"
                    )
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
                formatted_prompts = st.session_state.final_prompts
                render_prompt_blocks(formatted_prompts)

                st.markdown("### 🖼️ Storyboard Consolidation Prompt")
                st.code(st.session_state.storyboard_prompt, language="markdown")

                col_img1, col_img2 = st.columns(2)
                with col_img1:
                    if st.button("Generate Local Image (ComfyUI)"):
                        with st.spinner("Dispatching Storyboard to Local ComfyUI..."):
                            try:
                                img_bytes = pipeline.generate_image_comfyui(
                                    st.session_state.storyboard_prompt
                                )
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
                    f"## Full Production Script (Final Prompts)\n\n{formatted_prompts}\n\n"
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


def render_reset_controls(session_vars, workflow_mode):
    """Reset + seed controls at the bottom of the sidebar."""
    st.sidebar.divider()
    reset_disabled = st.session_state.phase == 0 and not st.session_state.product_shot_output
    if st.sidebar.button("Start Another Run (Reset)", disabled=reset_disabled):
        st.session_state.clear()
        import streamlit.components.v1 as components
        components.html("<script>window.parent.location.reload();</script>", height=0)

    if workflow_mode == "Storytelling" and st.session_state.phase == 3:
        if st.sidebar.button("Generate from another seed"):
            st.session_state.generation_seed += 1
            st.rerun()


def run(engine_mode: str, model_name: str, api_key, workflow_mode: str):
    """
    Main entry point called by app.py and applocal.py.
    engine_mode: 'Cloud' or 'Local'
    model_name: resolved model string
    api_key: Google API key (None for local)
    workflow_mode: 'Storytelling' or 'Product Shot'
    """
    session_vars = init_session_state()
    render_concept_sidebar(engine_mode, api_key)

    if workflow_mode == "Product Shot":
        render_product_shot(engine_mode, model_name, api_key)
    else:
        render_storytelling(engine_mode, model_name, api_key)

    render_reset_controls(session_vars, workflow_mode)
