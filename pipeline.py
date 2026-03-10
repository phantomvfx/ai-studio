import os
import json
import urllib.request
import urllib.error
import urllib.parse
from google import genai
from google.genai import types
import ollama

def get_google_client(api_key=None):
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client()

def call_llm(system_prompt, user_prompt, engine_mode="Cloud", model_name="gemini-2.5-flash", temperature=0.7, json_output=False, api_key=None):
    if engine_mode == "Cloud":
        client = get_google_client(api_key)
        config_kwargs = {"temperature": temperature}
        if json_output:
            config_kwargs["response_mime_type"] = "application/json"
        
        # Combine system prompt into the request using Instructions if available, or just prepend
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            **config_kwargs
        )
        
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=config
            )
            return response.text
        except Exception as e:
            # Fallback if system_instruction is not supported in this exact way
            prompt = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER INPUT:\n{user_prompt}"
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs)
            )
            return response.text
    else:
        # Local via Ollama
        client = ollama.Client(host='http://127.0.0.1:11434')
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        kwargs = {"model": model_name, "messages": messages, "options": {"temperature": temperature}}
        if json_output:
            kwargs["format"] = "json"
            
        response = client.chat(**kwargs)
        return response['message']['content']

def load_prompt(filename):
    path = os.path.join(os.path.dirname(__file__), "knowledge", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def describe_image(image_bytes, engine_mode="Local", api_key=None, mime_type="image/jpeg", prompt="Describe this image in detail to use as a creative concept. Output ONLY the raw descriptive caption. Do not include titles, labels, meta-commentary, or notes like 'Ideal for a storyboard'.", model_name="qwen3-vl:8b"):
    if engine_mode == "Cloud":
        from google.genai import types
        client = get_google_client(api_key)
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt
                ]
            )
            return response.text
        except Exception as e:
            print(f"Gemini Image Describing Error: {e}")
            raise e
    else:
        try:
            client = ollama.Client(host='http://127.0.0.1:11434')
            messages = [
                {"role": "user", "content": prompt, "images": [image_bytes]}
            ]
            response = client.chat(model=model_name, messages=messages)
            return response['message']['content']
        except Exception as e:
            print(f"Ollama Image Describing Error: {e}")
            raise e


def run_phase_1(concept, engine_mode="Cloud", model_name="gemini-2.5-flash", api_key=None):
    # Story Writer
    system_rules = load_prompt("story_frameworks.md")
    prompt = (
        f"Analyze this user concept: {concept}\n\n"
        "If the concept is vague or minimalist, act as a 'Creative Engine' and invent a narrative. "
        "If specific, preserving details. Output format: sh 01, sh 02, etc. (NOT panel 01)."
    )
    story_arc = call_llm(system_rules, prompt, engine_mode, model_name, 0.8, api_key=api_key)
    
    # Screenwriter
    screenplay_rules = load_prompt("screenplay_standards.md")
    screenplay = call_llm(screenplay_rules, f"Convert the following story arc into a screenplay, use sh 01, sh 02 sequence formatting:\n{story_arc}", engine_mode, model_name, 0.8, api_key=api_key)
    
    # Art Consultant
    art_rules = load_prompt("art_consultant.md")
    art_prompt = f"Review this screenplay:\n{screenplay}\n\nProvide Art Direction suggestions (3 options)."
    art_suggestions = call_llm(art_rules, art_prompt, engine_mode, model_name, 0.8, api_key=api_key)
    
    return story_arc, screenplay, art_suggestions

def run_phase_1_5(screenplay, art_prefs, engine_mode="Cloud", model_name="gemini-2.5-flash", api_key=None):
    cam_rules = load_prompt("camera_consultant.md")
    art_instructions = f"Chosen Art Direction: {art_prefs}" if art_prefs else "Chosen Art Direction: None provided."
    cam_prompt = f"Review this screenplay:\n{screenplay}\n\n{art_instructions}\nProvide Cinematography suggestions."
    return call_llm(cam_rules, cam_prompt, engine_mode, model_name, 0.8, api_key=api_key)

def run_phase_2(screenplay, art_prefs, camera_prefs, engine_mode="Cloud", model_name="gemini-2.5-flash", api_key=None):
    fallback_instruction = "Choose the most cinematic and professional path."
    art_instructions = f"User Art Preferences: {art_prefs}" if art_prefs else f"User Art Preferences: {fallback_instruction}"
    camera_instructions = f"User Camera Preferences: {camera_prefs}" if camera_prefs else f"User Camera Preferences: {fallback_instruction}"

    art_directed = call_llm(load_prompt("art_direction.md"), f"Screenplay:\n{screenplay}\n\n{art_instructions}", engine_mode, model_name, 0.8, api_key=api_key)
    camera_directed = call_llm(load_prompt("camera_motion.md"), f"Art Directed Screenplay:\n{art_directed}\n\n{camera_instructions}", engine_mode, model_name, 0.8, api_key=api_key)

    render_rules = load_prompt("render_artist_style.md")
    render_prompt = (
        f"You have received the enriched screenplay data below. Act as a Render Artist and produce the final prompts.\n\n"
        f"ENRICHED SCREENPLAY:\n{camera_directed}\n\n"
        f"INSTRUCTIONS: Using your guide, produce one output block per scene (sh 01 through sh 06). "
        f"For each scene output:\n"
        f"### Scene [N] — [scene_label]\n"
        f"**T2I Prompt:**\n> (full narrative prompt)\n\n"
        f"**I2V Animation Prompt:**\n> (camera motion instruction)\n\n"
        f"Output ALL 6 scenes. Do NOT truncate. No conversational filler."
    )
    final_prompts = call_llm(render_rules, render_prompt, engine_mode, model_name, 0.7, api_key=api_key)

    # Storyboard condensation
    storyboard_prompt = call_llm(
        "You are a technical prompt synthesizer. OUTPUT ONLY THE FINAL PROMPT TEXT. NO INTRODUCTIONS, NO EXPLANATIONS, NO NOTES.",
        f"Condense these 6 scene prompts into ONE Text-to-Image prompt for a 3-column x 2-row grid storyboard in 16:9 format.\n"
        f"CRITICAL: Describe exactly 6 distinct panels. Output ONLY the raw prompt text.\n\n"
        f"SCENES:\n{final_prompts}",
        engine_mode, model_name, 0.1, api_key=api_key
    )

    return final_prompts, storyboard_prompt

def run_product_shot_mode(concept, engine_mode="Cloud", model_name="gemini-2.5-flash", api_key=None):
    """
    1-shot Product Shot pipeline using the Nano Banana Render Artist guide.
    Outputs a narrative T2I + I2V prose prompt.
    """
    system_rules = load_prompt("product_shot_rules.md")
    render_rules = load_prompt("render_artist_style.md")

    prompt = (
        f"Process this product shot concept: {concept}\n\n"
        f"Apply your 4-stage pipeline (Brief Analysis → Composition → Lighting & Camera → Materiality). "
        f"Then, acting as a Render Artist using the following guide, produce the final output:\n\n"
        f"{render_rules}\n\n"
        f"Output format:\n"
        f"**T2I Prompt:**\n> (full narrative prompt following the Nano Banana formula)\n\n"
        f"**I2V Animation Prompt:**\n> (camera motion instruction for video generation)\n\n"
        f"No JSON. No schema. No preamble. Output only the two prompt blocks above."
    )

    return call_llm(system_rules, prompt, engine_mode, model_name, temperature=0.6, api_key=api_key)



def generate_image_comfyui(prompt):
    """
    Submits the prompt directly to local ComfyUI using the ZimageRender.json workflow.
    """
    # 1. Check if ComfyUI is running
    server_address = "127.0.0.1:8188"
    try:
        req = urllib.request.Request(f"http://{server_address}/system_stats")
        with urllib.request.urlopen(req) as response:
            pass # Server is up
    except urllib.error.URLError:
        raise ConnectionError("ComfyUI is not running. Please start ComfyUI manually and try again.")
        
    # 2. Load the workflow
    workflow_path = os.path.join(os.path.dirname(__file__), "comfyui", "ZimageRender.json")
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)
        
    # 3. Inject the Prompt into Node 5 (CLIPTextEncode)
    if "5" in workflow and "inputs" in workflow["5"]:
        workflow["5"]["inputs"]["text"] = prompt
        
    # 4. Randomize the Seed in Node 4 (KSampler)
    if "4" in workflow and "inputs" in workflow["4"]:
        import random
        workflow["4"]["inputs"]["seed"] = random.randint(1, 999999999999999)
        
    # Send the prompt to ComfyUI (Fire and Forget/Immediate return for now, since polling requires websocket logic) 
    # To get the image natively back to Streamlit, we must poll the /history endpoint.
    
    data = json.dumps({"prompt": workflow}).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read())
            prompt_id = result.get('prompt_id')
    except Exception as e:
        raise Exception(f"Failed to queue prompt in ComfyUI: {e}")

    # For this iteration, we will rely on ComfyUI to save it to its output folder, 
    # but we will poll it so we can return the exact image to the Streamlit UI.
    
    import time
    max_retries = 600 # 600 seconds timeout
    image_data = None
    
    for _ in range(max_retries):
        time.sleep(1) # Poll every 1 second
        try:
            hist_req = urllib.request.Request(f"http://{server_address}/history/{prompt_id}")
            with urllib.request.urlopen(hist_req) as hist_resp:
                history = json.loads(hist_resp.read())
                
                if prompt_id in history:
                    # Job Finished! Find the SaveImage node (Node 19 in standard workflow)
                    node_outputs = history[prompt_id].get('outputs', {})
                    
                    # Assuming node 19 is the final output node connected to the VaeDecode (Node 9) 
                    # as Upscaler 18 is disconnected.
                    # Or we dynamically find it by grabbing the first image in outputs
                    for node_id, output in node_outputs.items():
                        if 'images' in output:
                            image_info = output['images'][0]
                            filename = image_info['filename']
                            subfolder = image_info['subfolder']
                            folder_type = image_info['type']
                            
                            # Construct the view URL
                            view_url = f"http://{server_address}/view?filename={urllib.parse.quote(filename)}&subfolder={urllib.parse.quote(subfolder)}&type={folder_type}"
                            
                            # Download the image bytes
                            img_req = urllib.request.Request(view_url)
                            with urllib.request.urlopen(img_req) as img_resp:
                                image_data = img_resp.read()
                            break
                    if image_data:
                        break 
        except Exception:
            pass # Keep polling
            
    if image_data:
        return image_data
    else:
        raise TimeoutError("ComfyUI took too long to generate the image.")

