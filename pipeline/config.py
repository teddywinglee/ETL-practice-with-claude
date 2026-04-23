from openai import OpenAI

# Set MODEL to the model name shown in LM Studio's loaded models list (e.g. "llama3.1:8b" or "meta-llama-3.1-8b-instruct")
MODEL = "gemma-4-26b-a4b-it"

lm_studio = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
