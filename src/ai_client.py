import json

# SDK Imports with safe fallbacks
try:
    from openai import OpenAI as OpenAIClient
except ImportError:
    OpenAIClient = None

try:
    from google import genai as google_genai
except ImportError:
    google_genai = None

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from mistralai.client import MistralClient
except ImportError:
    MistralClient = None

try:
    import cohere
except ImportError:
    cohere = None

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

try:
    import replicate
except ImportError:
    replicate = None

try:
    import together
except ImportError:
    together = None

try:
    import boto3
except ImportError:
    boto3 = None


PROVIDER_CLIENT_FACTORIES = {
    "openai": lambda key: OpenAIClient(api_key=key) if OpenAIClient else None,
    "anthropic": lambda key: anthropic.Anthropic(api_key=key) if anthropic else None,
    "google": lambda key: google_genai.configure(api_key=key) if google_genai else None,
    "mistral": lambda key: MistralClient(api_key=key) if MistralClient else None,
    "cohere": lambda key: cohere.Client(api_key=key) if cohere else None,
    "huggingface": lambda key: InferenceClient(token=key) if InferenceClient else None,
    "replicate": lambda key: replicate.Client(api_token=key) if replicate else None,
    "together": lambda key: together.Client(api_key=key) if together else None,
    "bedrock": lambda key: boto3.client("bedrock-runtime", region_name="us-east-1") if boto3 else None,
}

def get_client(provider: str, api_key: str):
    if provider not in PROVIDER_CLIENT_FACTORIES:
        raise ValueError("Unknown provider: " + provider)

    if provider == "google":
        if google_genai:
            google_genai.configure(api_key=api_key)
            return google_genai
        else:
            raise RuntimeError("SDK for provider 'google' not available in environment")

    factory = PROVIDER_CLIENT_FACTORIES[provider]
    client = factory(api_key)
    if client is None:
        raise RuntimeError(f"SDK for provider '{provider}' not available in environment")
    return client


def generate_content(provider: str, api_key: str, model: str, content: str) -> str:
    client = get_client(provider, api_key)

    if provider == "openai":
        try:
            resp = client.chat.completions.create(model=model, messages=[{"role": "user", "content": content}])
            return resp.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"OpenAI request failed: {e}")

    if provider == "google":
        try:
            gen_model = client.GenerativeModel(model)
            resp = gen_model.generate_content(content)
            return resp.text
        except Exception as e:
            raise RuntimeError(f"Google GenAI request failed: {e}")

    if provider == "anthropic":
        try:
            msg = client.messages.create(model=model, messages=[{"role": "user", "content": content}], max_tokens=2048)
            return msg.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic request failed: {e}")

    if provider == "mistral":
        try:
            r = client.chat(model=model, messages=[{"role": "user", "content": content}])
            return r.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"Mistral request failed: {e}")

    if provider == "cohere":
        try:
            r = client.chat(model=model, message=content)
            return r.text
        except Exception as e:
            raise RuntimeError(f"Cohere request failed: {e}")

    if provider == "huggingface":
        try:
            r = client.text_generation(model=model, inputs=content)
            return str(r)
        except Exception as e:
            raise RuntimeError(f"HuggingFace request failed: {e}")

    if provider == "replicate":
        try:
            output = client.run(model, input={"prompt": content})
            return "".join(output)
        except Exception as e:
            raise RuntimeError(f"Replicate request failed: {e}")

    if provider == "together":
        try:
            r = client.chat.completions.create(model=model, messages=[{"role": "user", "content": content}])
            return r.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"Together.ai request failed: {e}")

    if provider == "bedrock":
        try:
            body = json.dumps({"inputText": content})
            resp = client.invoke_model(
                body=body, modelId=model, contentType="application/json", accept="application/json"
            )
            resp_body = json.loads(resp.get("body").read())
            return resp_body.get("results")[0].get("outputText")
        except Exception as e:
            raise RuntimeError(f"Bedrock request failed: {e}")

    raise NotImplementedError(f"Provider integration not implemented for: {provider}")
