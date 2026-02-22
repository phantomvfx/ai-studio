import os
from griptape.structures import Pipeline
from griptape.tasks import PromptTask
from griptape.drivers import GooglePromptDriver, OllamaPromptDriver
from griptape.rules import Rule, Ruleset

def get_drivers(engine_mode="Cloud", model_name="gemini-1.5-pro"):
    """
    Returns (CREATIVE_DRIVER, TECHNICAL_DRIVER) based on mode and model name.
    """
    if engine_mode == "Cloud":
        creative = GooglePromptDriver(
            model=model_name,
            temperature=0.8
        )
        technical = GooglePromptDriver(
            model=model_name,
            temperature=0.1
        )
    else:
        # Local mode using Ollama
        creative = OllamaPromptDriver(
            model="gemma3:12b",
            temperature=0.8,
            host="http://127.0.0.1:11434"
        )
        technical = OllamaPromptDriver(
            model="qwen2.5-coder:14b",
            temperature=0.1,
            host="http://127.0.0.1:11434"
        )
        
    return creative, technical

def load_prompt(filename):
    path = os.path.join(os.path.dirname(__file__), "knowledge", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def run_phase_1(concept, engine_mode="Cloud", model_name="gemini-1.5-pro"):
    """
    Phase 1: Pre-production (Story Writer -> Screenwriter -> Creative Consultant)
    Returns:
        story_arc (str): The structured story
        screenplay (str): The structured scenes
        consultant_suggestions (str): Art/Camera suggestions
    """
    creative_driver, _ = get_drivers(engine_mode, model_name)
    
    # Task 1: Story Writer
    story_task = PromptTask(
        "Analyze this user concept: {{ args[0] }}\n\n"
        "If the concept is vague or minimalist (e.g., just a few words), act as a 'Creative Engine' and invent a high-concept narrative, emotional arc, and setting.\n"
        "If the concept is specific (e.g., provides explicit colors, models, locations), act as a 'Refiner' and strictly preserve those details while structuring them into the 30-second Hook-Build-Payoff framework.",
        rulesets=[Ruleset(name="StoryFramework", rules=[Rule(load_prompt("story_frameworks.md"))])],
        prompt_driver=creative_driver,
        id="StoryTask"
    )
    story_task.run(concept)
    story_arc = story_task.output.value

    # Task 2: Screenwriter
    screenplay_task = PromptTask(
        "Convert the following story arc into a screenplay:\n{{ args[0] }}",
        rulesets=[Ruleset(name="ScreenplayStandards", rules=[Rule(load_prompt("screenplay_standards.md"))])],
        prompt_driver=creative_driver,
        id="ScreenplayTask"
    )
    screenplay_task.run(story_arc)
    screenplay = screenplay_task.output.value
    
    # Task 3: Art Consultant
    art_consultant_task = PromptTask(
        "Review this screenplay:\n{{ args[0] }}\n\n"
        "Provide Art Direction suggestions. "
        "CRITICAL INSTRUCTION: If the screenplay explicitly features a specific model, object, or location (e.g., 'Porsche 911 996'), your suggestions "
        "must provide 3 DIFFERENT visual worlds/atmospheres for that specific element, NOT swap it for different elements. Keep the core specific subject consistent across options.",
        rulesets=[Ruleset(name="ArtConsultant", rules=[Rule(load_prompt("art_consultant.md"))])],
        prompt_driver=creative_driver,
        id="ArtConsultantTask"
    )
    art_consultant_task.run(screenplay)
    art_suggestions = art_consultant_task.output.value
    
    return story_arc, screenplay, art_suggestions

def run_phase_1_5(screenplay, art_prefs, engine_mode="Cloud", model_name="gemini-1.5-pro"):
    """
    Phase 1.5: Camera Consultant
    Generates camera concepts based on the chosen art direction.
    """
    creative_driver, _ = get_drivers(engine_mode, model_name)
    
    art_instructions = f"Chosen Art Direction: {art_prefs}" if art_prefs else "Chosen Art Direction: None provided. Invent the most cinematic look."
    
    camera_consultant_task = PromptTask(
        f"Review this screenplay:\n{{{{ args[0] }}}}\n\n{art_instructions}\n"
        "Provide Cinematography suggestions specifically tailored to capture the requested art direction.",
        rulesets=[Ruleset(name="CameraConsultant", rules=[Rule(load_prompt("camera_consultant.md"))])],
        prompt_driver=creative_driver,
        id="CameraConsultantTask"
    )
    camera_consultant_task.run(screenplay)
    return camera_consultant_task.output.value

def run_phase_2(screenplay, art_prefs, camera_prefs, engine_mode="Cloud", model_name="gemini-1.5-pro"):
    """
    Phase 2: Production (Art Director -> Cinematographer -> Render Artist)
    Returns:
        final_prompts (str): Strict Nano Banana Pro formatted prompts
    """
    creative_driver, technical_driver = get_drivers(engine_mode, model_name)
    
    # Let's ensure if preferences are empty we handle it gracefully in exactly what we pass to the tasks.
    fallback_instruction = "Choose the most cinematic and professional path from the previous suggestions."
    art_instructions = f"User Art Preferences: {art_prefs}" if art_prefs else f"User Art Preferences: {fallback_instruction}"
    camera_instructions = f"User Camera Preferences: {camera_prefs}" if camera_prefs else f"User Camera Preferences: {fallback_instruction}"

    # Task 4: Art Director
    art_task = PromptTask(
        f"Base Screenplay:\n{{{{ args[0] }}}}\n\n{art_instructions}",
        rulesets=[Ruleset(name="ArtDirection", rules=[Rule(load_prompt("art_direction.md"))])],
        prompt_driver=creative_driver,
        id="ArtTask"
    )
    art_task.run(screenplay)
    art_directed = art_task.output.value
    
    # Task 5: Cinematographer
    camera_task = PromptTask(
        f"Art Directed Screenplay:\n{{{{ args[0] }}}}\n\n{camera_instructions}",
        rulesets=[Ruleset(name="CameraMotion", rules=[Rule(load_prompt("camera_motion.md"))])],
        prompt_driver=creative_driver,
        id="CameraTask"
    )
    camera_task.run(art_directed)
    camera_directed = camera_task.output.value
    
    # Task 6: Render Artist (Strict formatting, Technical Driver)
    render_task = PromptTask(
        "Enriched Screenplay with Camera Motion:\n{{ args[0] }}\n\n"
        "CRITICAL INSTRUCTION: Provide exhaustive detail regardless of the input length. Write these prompts as if they are overriding or enhancing a reference Image-to-Image (I2I) workflow, focusing intensely on technical camera gear, precise lighting physics, and micro-textures that a reference image might lack.",
        rulesets=[Ruleset(name="RenderArtistStyle", rules=[Rule(load_prompt("render_artist_style.md"))])],
        prompt_driver=technical_driver,
        id="RenderTask"
    )
    render_task.run(camera_directed)
    render_prompts = render_task.output.value
    
    # Task 7: Storyboard Consolidation
    storyboard_task = PromptTask(
        "Core Visual Descriptions (6 Scenes):\n{{ args[0] }}\n\n"
        "Task Goal: Take the core visual descriptions of all 6 scenes above and synthesize them into ONE single concise Text-to-Image (T2I) prompt.\n"
        "Formatting Rule: The prompt must explicitly instruct the AI to create a '3x2 grid storyboard panels image'.\n"
        "Instruction: 'A professional 6-panel storyboard grid (3 columns, 2 rows). Each panel depicts a sequential scene from the story: [Briefly list the 6 scene actions derived from the inputs]. Maintain absolute character and environment continuity across all panels. High-contrast sketch and cinematic lighting style.'",
        prompt_driver=technical_driver,
        id="StoryboardTask"
    )
    storyboard_task.run(render_prompts)
    storyboard_prompt = storyboard_task.output.value
    
    return render_prompts, storyboard_prompt
