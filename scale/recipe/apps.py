"""Defines the application configuration for the recipe application"""


from django.apps import AppConfig


class RecipeConfig(AppConfig):
    """Configuration for the recipe app
    """
    name = 'recipe'
    label = 'recipe'
    verbose_name = 'Recipe'

    def ready(self):
        """Registers components related to recipes"""

        # Register recipe message types
        from messaging.messages.factory import add_message_type
        from recipe.messages.process_recipe_input import ProcessRecipeInput
        from recipe.messages.reprocess_recipes import ReprocessRecipes
        from recipe.messages.update_recipe_metrics import UpdateRecipeMetrics
        from recipe.messages.update_recipes import UpdateRecipes

        add_message_type(ProcessRecipeInput)
        add_message_type(ReprocessRecipes)
        add_message_type(UpdateRecipeMetrics)
        add_message_type(UpdateRecipes)
