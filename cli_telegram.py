# cli_telegram.py
# A skeletal entry point for CLI and future Telegram bot workflow integrations.

import sys
import pipeline
from dotenv import load_dotenv

load_dotenv()

def main():
    print("Welcome to AI Studio CLI")
    engine_mode = input("Enter engine mode (Cloud/Local) [default: Cloud]: ").strip() or "Cloud"
    
    print("\n--- PHASE 1: PRE-PRODUCTION ---")
    concept = input("Enter your story concept: ")
    if not concept:
        print("Concept required. Exiting.")
        sys.exit(1)
        
    print("\nWorking...")
    arc, script, suggestions = pipeline.run_phase_1(concept, engine_mode=engine_mode)
    
    print("\n--- CREATIVE CONSULTANT SUGGESTIONS ---")
    print(suggestions)
    
    print("\n--- HUMAN IN THE LOOP ---")
    art_prefs = input("Enter Art Preferences (or leave blank to auto-decide): ")
    camera_prefs = input("Enter Camera Preferences (or leave blank to auto-decide): ")
    
    print("\n--- PHASE 2: PRODUCTION ---")
    print("Agents are working to generate Nano Banana Pro rendering prompts...")
    final_prompts = pipeline.run_phase_2(script, art_prefs, camera_prefs, engine_mode=engine_mode)
    
    print("\n--- FINAL PROMPTS ---")
    print(final_prompts)

if __name__ == "__main__":
    main()
