import json
import os
from pathlib import Path

class RecipeManager:
    def __init__(self, recipes_dir="recipes"):
        # Use absolute path resolution
        if not Path(recipes_dir).is_absolute():
            script_dir = Path(__file__).parent
            self.recipes_dir = script_dir / recipes_dir
        else:
            self.recipes_dir = Path(recipes_dir)
        self.recipes = {}
        self.load_recipes()
    
    def load_recipes(self):
        """Load all recipe JSON files from the recipes directory."""
        for recipe_file in self.recipes_dir.glob("*.json"):
            with open(recipe_file, "r", encoding="utf-8") as f:
                recipe = json.load(f)
                self.recipes[recipe["id"]] = recipe
        print(f"Loaded {len(self.recipes)} recipes")
    
    def get_recipe(self, recipe_id):
        """Get a recipe by ID."""
        return self.recipes.get(recipe_id)
    
    def get_next_recipe_step(self, recipe_id, current_step):
        """Get the next step in a recipe."""
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            return {"error": f"Recipe {recipe_id} not found"}
        
        next_step = current_step + 1
        if next_step >= len(recipe["steps"]):
            return {
                "status": "completed",
                "message": {
                    "darija": "بصحة! الطبق ولى جاهز.",
                    "english": "Bon appétit! The dish is ready."
                }
            }
        
        step = recipe["steps"][next_step]
        return {
            "step_number": step["step_number"],
            "action": step["action"],
            "instruction": {
                "darija": step["darija_instruction"],
                "english": step["english_instruction"]
            },
            "duration_seconds": step["duration_seconds"],
            "timer_label": step["timer_label"],
            "expected_actions": step["expected_actions"],
            "tips": step["tips"]
        }
    
    def explain_ingredient(self, ingredient_name, language="darija"):
        """Get information about an ingredient from all recipes."""
        ingredient_name_lower = ingredient_name.lower()
        
        for recipe in self.recipes.values():
            for ingredient in recipe["ingredients"]:
                # Check if ingredient name matches in any language
                for lang, name in ingredient["name"].items():
                    if ingredient_name_lower in name.lower():
                        return {
                            "name": ingredient["name"],
                            "quantity": ingredient.get("quantity", "N/A"),
                            "cultural_note": ingredient.get("cultural_note", {})
                        }
        
        return {
            "error": f"Ingredient {ingredient_name} not found",
            "message": {
                "darija": "ما لقيتش هاد المكون.",
                "english": "Ingredient not found."
            }
        }
    
    def get_cultural_context(self, topic):
        """Get cultural context about a dish or ingredient."""
        topic_lower = topic.lower()
        
        for recipe in self.recipes.values():
            # Check if topic matches recipe name
            for lang, name in recipe["name"].items():
                if topic_lower in name.lower():
                    return {
                        "name": recipe["name"],
                        "description": recipe["description"],
                        "cultural_context": recipe["cultural_context"]
                    }
        
        return {
            "error": f"No cultural context found for {topic}",
            "message": {
                "darija": "ما لقيتش معلومات على هاد الموضوع.",
                "english": "No information found on this topic."
            }
        }
    
    def get_recipe_list(self):
        """Get a list of all available recipes."""
        return [
            {
                "id": recipe["id"],
                "name": recipe["name"],
                "description": recipe["description"],
                "total_time_minutes": recipe["total_time_minutes"],
                "difficulty": recipe["difficulty"],
                "servings": recipe["servings"]
            }
            for recipe in self.recipes.values()
        ]


class TimerManager:
    def __init__(self):
        self.timers = []
    
    def start_timer(self, duration, label):
        """Start a cooking timer."""
        timer = {
            "duration": duration,
            "label": label,
            "status": "running"
        }
        self.timers.append(timer)
        return {
            "status": "timer_started",
            "duration": duration,
            "label": label,
            "message": {
                "darija": f"بديت الوقت ديال {label} لمدة {duration} ثانية.",
                "english": f"Started timer for {label} for {duration} seconds."
            }
        }
    
    def get_active_timers(self):
        """Get all active timers."""
        return [t for t in self.timers if t["status"] == "running"]


class ActionDetector:
    def __init__(self):
        self.last_action = None
        self.action_history = []
    
    def detect_kitchen_action(self, action, confidence, object_name=None):
        """Confirm detected kitchen action."""
        self.last_action = {
            "action": action,
            "confidence": confidence,
            "object": object_name
        }
        self.action_history.append(self.last_action)
        
        # Generate Darija response based on action
        action_responses = {
            "cutting": "كتقطع {object}. مزيان.",
            "chopping": "كتقطع {object}. مزيان.",
            "stirring": "كتقلب. واصل.",
            "frying": "كتقلي. ديرها على نار متوسطة.",
            "sauteing": "كتقلي. مزيان.",
            "seasoning": "كتزيد التوابل. بنين.",
            "plating": "كتقدم الطبق. بصحة!",
            "mixing": "كتخلط. مزيان.",
            "kneading": "كتعجن. واصل.",
            "rolling": "كتدور. مزيان.",
            "idle": "مستني. الطيب غادي مزيان."
        }
        
        darija_response = action_responses.get(action, "واصل.")
        if object_name:
            darija_response = darija_response.replace("{object}", object_name)
        else:
            darija_response = darija_response.replace(" {object}", "")
        
        return {
            "status": "action_detected",
            "action": action,
            "confidence": confidence,
            "object": object_name,
            "message": {
                "darija": darija_response,
                "english": f"Detected: {action}" + (f" {object_name}" if object_name else "")
            }
        }
    
    def get_last_action(self):
        """Get the last detected action."""
        return self.last_action
