import os
import re
import io
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import pipeline

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am your AI Studio Creative Director.\n\n"
                                    "Commands:\n"
                                    "/generate <concept> - Create a Storyboard campaign\n"
                                    "/product <concept> - Create a Product Shot campaign")

async def generate_story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    concept = " ".join(context.args)
    if not concept:
        await update.message.reply_text("Please provide a concept. Example: /generate A cyberpunk detective...")
        return
        
    status_message = await update.message.reply_text("⏳ Briefing the AI Agents... This takes about 1-2 minutes.")
    
    try:
        # Defaulting to Local and kimi-k2.5:cloud for the Telegram Bot experience
        engine_mode = "Local"
        model_name = "kimi-k2.5:cloud" 
        api_key = os.getenv("GOOGLE_API_KEY")
        
        arc, script, art_suggs = pipeline.run_phase_1(concept, engine_mode, model_name, api_key)
        cam_suggs = pipeline.run_phase_1_5(script, "Auto-decide best cinematic style", engine_mode, model_name, api_key)
        final_prompts, storyboard_prompt = pipeline.run_phase_2(script, "Auto-decide", "Auto-decide", engine_mode, model_name, api_key)
        
        slug = re.sub(r'[^a-zA-Z0-9\s]', '_', concept)
        slug = "_".join(slug.split('_')[:6]).strip('_') or "storyboard_campaign"
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Ensure the outputs directory exists
        os.makedirs("outputs", exist_ok=True)
        filename = os.path.join("outputs", f"{slug}_{date_str}.md")
        
        md_content = f"# Full Production Script\n\n```json\n{final_prompts}\n```\n\n# Storyboard Prompt\n\n{storyboard_prompt}"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        with open(filename, "rb") as f:
            await update.message.reply_document(document=f)
            
        await status_message.edit_text("🎨 Generating Local Storyboard Image via ComfyUI... (This may take a moment)")
        
        try:
            # We must use asyncio.to_thread because pipeline.generate_image_comfyui 
            # uses a synchronous time.sleep() blocking polling loop under the hood.
            img_bytes = await asyncio.to_thread(pipeline.generate_image_comfyui, storyboard_prompt)
            if img_bytes:
                await update.message.reply_photo(photo=io.BytesIO(img_bytes), caption="🎬 Your Storyboard Preview")
                await status_message.edit_text("✅ Storyboard Campaign and Image Ready! Check the document above.")
        except Exception as img_e:
            await status_message.edit_text(f"✅ Campaign Ready! (Note: ComfyUI Image Generation skipped: {img_e})")
        
    except Exception as e:
        await status_message.edit_text(f"❌ Error during generation: {e}")

async def generate_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    concept = " ".join(context.args)
    if not concept:
        await update.message.reply_text("Please provide a concept. Example: /product VW Polo 1982 on the beach road")
        return
        
    status_message = await update.message.reply_text("⏳ Briefing the AI Agents... This takes about 1 minute.")
    
    try:
        engine_mode = "Local"
        model_name = "kimi-k2.5:cloud"
        api_key = os.getenv("GOOGLE_API_KEY")

        final_json = pipeline.run_product_shot_mode(concept, engine_mode, model_name, api_key)
        
        slug = re.sub(r'[^a-zA-Z0-9\s]', '_', concept)
        slug = "_".join(slug.split('_')[:6]).strip('_') or "product_shot"
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Ensure the outputs directory exists
        os.makedirs("outputs", exist_ok=True)
        filename = os.path.join("outputs", f"{slug}_{date_str}.md")
        
        md_content = f"# Product Shot API Output\n\n```json\n{final_json}\n```"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        with open(filename, "rb") as f:
            await update.message.reply_document(document=f)
            
        await status_message.edit_text("🎨 Generating Local Product Shot Image via ComfyUI... (This may take a moment)")
        
        try:
            # We must use asyncio.to_thread because pipeline.generate_image_comfyui 
            # uses a synchronous time.sleep() blocking polling loop under the hood.
            img_bytes = await asyncio.to_thread(pipeline.generate_image_comfyui, concept)
            if img_bytes:
                await update.message.reply_photo(photo=io.BytesIO(img_bytes), caption="🎬 Your Product Shot Preview")
                await status_message.edit_text("✅ Product Campaign and Image Ready! Check the document above.")
        except Exception as img_e:
            await status_message.edit_text(f"✅ Campaign Ready! (Note: ComfyUI Image Generation skipped: {img_e})")
    except Exception as e:
        await status_message.edit_text(f"❌ Error during generation: {e}")

def main():
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return
        
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("generate", generate_story))
    application.add_handler(CommandHandler("product", generate_product))

    print("Creative Director Telegram Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
