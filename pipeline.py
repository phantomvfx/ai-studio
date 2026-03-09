import os
import json
import urllib.request
import urllib.error
from google import genai
from google.genai import types
import ollama

def get_google_client(api_key=None):
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client()

def call_llm(system_prompt, user_prompt, engine_mode="Cloud", model_name="gemini-3.1-pro-preview", temperature=0.7, json_output=False, api_key=None):
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


def run_phase_1(concept, engine_mode="Cloud", model_name="gemini-3.1-pro-preview", api_key=None):
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

def run_phase_1_5(screenplay, art_prefs, engine_mode="Cloud", model_name="gemini-3.1-pro-preview", api_key=None):
    cam_rules = load_prompt("camera_consultant.md")
    art_instructions = f"Chosen Art Direction: {art_prefs}" if art_prefs else "Chosen Art Direction: None provided."
    cam_prompt = f"Review this screenplay:\n{screenplay}\n\n{art_instructions}\nProvide Cinematography suggestions."
    return call_llm(cam_rules, cam_prompt, engine_mode, model_name, 0.8, api_key=api_key)

def run_phase_2(screenplay, art_prefs, camera_prefs, engine_mode="Cloud", model_name="gemini-3.1-pro-preview", api_key=None):
    fallback_instruction = "Choose the most cinematic and professional path."
    art_instructions = f"User Art Preferences: {art_prefs}" if art_prefs else f"User Art Preferences: {fallback_instruction}"
    camera_instructions = f"User Camera Preferences: {camera_prefs}" if camera_prefs else f"User Camera Preferences: {fallback_instruction}"

    art_directed = call_llm(load_prompt("art_direction.md"), f"Screenplay:\n{screenplay}\n\n{art_instructions}", engine_mode, model_name, 0.8, api_key=api_key)
    camera_directed = call_llm(load_prompt("camera_motion.md"), f"Art Directed Screenplay:\n{art_directed}\n\n{camera_instructions}", engine_mode, model_name, 0.8, api_key=api_key)
    
    schema_rules = load_prompt("nano_banana_schema.json")
    
    render_rules = load_prompt("render_artist_style.md")
    render_prompt = (
        f"You have received the enriched screenplay data below.\n"
        f"DATA LOAD:\n{camera_directed}\n\n"
        f"CRITICAL INSTRUCTION: Do NOT respond with conversational text or acknowledge this message. Immediately process the DATA LOAD above.\n"
        f"Your entire output MUST be a valid JSON Object containing a single root key called `scenes`. The value of `scenes` MUST be an Array containing exactly 6 JSON objects. Each of those 6 objects must validate against this schema:\n{schema_rules}\n\n"
        "Include an extra string key `scene_label` (e.g., 'sh 01') at the root of each of the 6 JSON objects to signify which scene it is.\n"
        "Example structural output (OUTPUT RAW JSON ONLY):\n"
        "{\n"
        "  \"scenes\": [\n"
        "    {\n"
        "      \"scene_label\": \"sh 01\",\n"
        "      \"user_intent\": \"string\",\n"
        "      \"meta\": {},\n"
        "      \"subject\": [],\n"
        "      \"scene\": {}\n"
        "    },\n"
        "    {\n"
        "      \"scene_label\": \"sh 02\",\n"
        "      \"user_intent\": \"string\",\n"
        "      \"meta\": {},\n"
        "      \"subject\": [],\n"
        "      \"scene\": {}\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "CRITICAL: YOU MUST OUTPUT EXACTLY 6 FULL SCENE OBJECTS IN THE SCENES ARRAY. DO NOT TRUNCATE."
    )
    # Give the model full JSON output privileges for Phase 2
    render_prompts_json_str = call_llm(render_rules, render_prompt, engine_mode, model_name, 0.1, json_output=True, api_key=api_key)
    
    # Storyboard condensation
    storyboard_prompt = call_llm(
        "You are a technical prompt synthesizer. OUTPUT ONLY THE FINAL PROMPT TEXT. NO INTRODUCTIONS, NO EXPLANATIONS, NO NOTES.", 
        f"Condense these 6 JSON schema scenes into ONE Text-to-Image text prompt (NOT JSON) for a 3 columns 2 rows grid storyboard in a 16:9 image format.\n"
        f"CRITICAL: The prompt MUST explicitly describe exactly 6 distinct panels/shots to match the 6 scenes.\n\n"
        f"SCENES:\n{render_prompts_json_str}\n\n"
        f"CRITICAL INSTRUCTION: Output ONLY the raw generation prompt. Do not say 'Here is the prompt', 'Prompt:', or provide notes.", 
        engine_mode, model_name, 0.1, api_key=api_key
    )
    
    return render_prompts_json_str, storyboard_prompt

def run_product_shot_mode(concept, engine_mode="Cloud", model_name="gemini-3.1-pro-preview", api_key=None):
    """
    4-Stage ComfyUI Product Shot API Workflow in one shot.
    Output is strictly JSON format.
    """
    system_rules = load_prompt("product_shot_rules.md")
    schema_rules = load_prompt("nano_banana_schema.json")
    
    prompt = (
        f"Process this product shot concept: {concept}\n\n"
        f"Apply the 4-stage pipeline from your system instructions. Your final output MUST be a valid JSON instance strictly matching this JSON Schema:\n"
        f"SCHEMA REQUIREMENTS:\n{schema_rules}\n\n"
        f"Do NOT output the raw schema definition. You must fill in the properties with your creative synthesis of the user's concept."
    )
    
    response_text = call_llm(system_rules, prompt, engine_mode, model_name, temperature=0.5, json_output=True, api_key=api_key)
    
    # Strip markdown codeblocks if LLM incorrectly wraps it
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    return response_text

def generate_image(prompt, api_key=None):
    """
    Calls Google GenAI Image generation using Gemini 2.5 Flash Image.
    """
    client = get_google_client(api_key)
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash-image',
            contents=prompt
        )
        for candidate in response.candidates:
            if not candidate.content or not candidate.content.parts:
                continue
            for part in candidate.content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    # Return the bytes of the generated image
                    return part.inline_data.data
    except Exception as e:
        print(f"Image Gen Error: {e}")
        raise e
    return None

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

