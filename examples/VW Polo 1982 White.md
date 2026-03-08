# Product Shot API Output

```json
{
  "user_intent": "A cinematic hero shot of a pristine 1982 white Volkswagen Polo Mk1 showcasing authentic 1980s German automotive design, materials, and patina in golden hour urban environment",
  "meta": {
    "aspect_ratio": "16:9",
    "quality": "ultra_photorealistic",
    "safety_filter": "block_some",
    "steps": 50,
    "guidance_scale": 7.5,
    "seed": 1982
  },
  "subject": [
    {
      "id": "hero_vehicle",
      "type": "vehicle",
      "name": "Volkswagen Polo 1982",
      "description": "1982 Volkswagen Polo Mk1 facelift in factory Alpine White (L90E), boxy 3-door hatchback silhouette with sharp geometric creases and flat panels characteristic of 1980s German utilitarian design, round sealed-beam headlights with amber turn signal indicators showing internal filament details and glass refraction, black textured plastic bumpers with thin chrome trim strips catching specular highlights, black side rubbing strips along the doors showing material density, chrome door handles and side mirrors with authentic micro-pitting and oxidation patina, steel wheels with chrome hubcaps showing realistic brake dust accumulation in the crevices, VW roundel emblem on matte black plastic grille with subtle light diffusion, rubber window seals exhibiting subsurface scattering and slight UV degradation, single-stage Alpine White paint exhibiting authentic orange peel texture and microscopic metallic flake sparkling with anisotropic specular highlights along the body lines, pristine sheet metal with factory-consistent panel gaps and door seals",
      "position": "center"
    }
  ],
  "scene": {
    "location": "European urban cobblestone street with historic architecture",
    "time": "golden_hour",
    "weather": "clear_skies",
    "lighting": {
      "type": "natural_sunlight",
      "direction": "side_lit"
    },
    "background_elements": [
      "blurred historic European buildings with warm stone facades",
      "wet cobblestone street creating mirror-like Fresnel reflections",
      "distant chestnut trees with autumn foliage",
      "soft atmospheric haze and floating dust motes in light rays",
      "vintage street lamp with warm glow"
    ]
  },
  "technical": {
    "camera_model": "Hasselblad X2D",
    "lens": "85mm",
    "aperture": "f/4",
    "shutter_speed": "1/250",
    "iso": "100",
    "film_stock": "Kodak Portra 400"
  },
  "composition": {
    "framing": "wide_shot",
    "angle": "low_angle",
    "focus_point": "whole_scene"
  },
  "style_modifiers": {
    "medium": "photography",
    "aesthetic": [
      "vintage_80s",
      "minimalist"
    ],
    "artist_reference": [
      "automotive photography",
      "medium format film aesthetic"
    ]
  },
  "i2v_prompt": "Slow cinematic dolly shot circling counter-clockwise around the stationary white Volkswagen Polo, golden hour sunlight shifting across the boxy body panels creating moving anisotropic specular highlights on the Alpine White paint, subtle dust particles floating and glowing in the warm 3200K light rays, background bokeh shifting from sharp to soft as the camera moves, maintaining tack-sharp focus on the vehicle's iconic 1980s silhouette and chrome details, reflections in the wet cobblestones subtly rippling",
  "advanced": {
    "negative_prompt": [
      "modern cars",
      "modified",
      "tuning",
      "body kit",
      "rust",
      "damage",
      "dents",
      "scratches",
      "blur",
      "low quality",
      "distortion",
      "watermark",
      "text",
      "signature",
      "worst quality",
      "oversaturated",
      "cartoon",
      "anime"
    ],
    "magic_prompt_enhancer": true,
    "hdr_mode": true
  }
}
```