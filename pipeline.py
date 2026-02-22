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
    
    # Task 3: Creative Consultant
    consultant_task = PromptTask(
        "Review this screenplay:\n{{ args[0] }}\n\n"
        "Provide Art Direction and Cinematography suggestions. "
        "CRITICAL INSTRUCTION: If the screenplay explicitly features a specific model, object, or location (e.g., 'Porsche 911 996'), your suggestions "
        "must provide 3 DIFFERENT visual worlds/atmospheres for that specific element, NOT swap it for different elements. Keep the core specific subject consistent across options.",
        rulesets=[Ruleset(name="CreativeConsultant", rules=[Rule(load_prompt("creative_consultant.md"))])],
        prompt_driver=creative_driver,
        id="ConsultantTask"
    )
    consultant_task.run(screenplay)
    suggestions = consultant_task.output.value
    
    return story_arc, screenplay, suggestions

def run_phase_2(screenplay, art_prefs, camera_prefs, engine_mode="Cloud", model_name="gemini-1.5-pro"):
    """
    Phase 2: Production (Art Director -> Cinematographer -> Render Artist)
    Returns:
        final_prompts (str): Strict Nano Banana Pro formatted prompts
    """
    creative_driver, technical_driver = get_drivers(engine_mode, model_name)
    
    # Let's ensure if preferences are empty we handle it gracefully in exactly what we pass to the tasks.
    art_instructions = f"User Art Preferences: {art_prefs}" if art_prefs else "User Art Preferences: None. Invent one from consultant options."
    camera_instructions = f"User Camera Preferences: {camera_prefs}" if camera_prefs else "User Camera Preferences: None. Invent one from consultant options."

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
    
    return render_task.output.value
