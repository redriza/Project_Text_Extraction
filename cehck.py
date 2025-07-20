from huggingface_hub import list_models

models = list(list_models())  # Convert generator to list
print(f"Total available models: {len(models)}")
