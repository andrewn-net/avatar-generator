from gradio_client import Client

# Initialize the client with the AI model's endpoint
client = Client("Alpha-VLLM/Lumina-Image-2.0")

# Function to interact with the API
def generate_image(caption, negative_caption="", system_type="You are an assistant designed to generate superior images with the superior degree of image-text alignment based on textual prompts or user prompts.", resolution="512x1792", sampling_steps=1, cfg_scale=4, cfg_truncation=0, cfg_renorm=2.0, solver="euler", time_shift=6, seed=0, rope_scaling="Time-aware", linear_ntk_watershed=0.3, proportional_attention=True):
    # Call the AI API endpoint with the provided parameters
    result = client.predict(
        param_0=caption,
        param_1=negative_caption,
        param_2=system_type,
        param_3=resolution,
        param_4=sampling_steps,
        param_5=cfg_scale,
        param_6=cfg_truncation,
        param_7=cfg_renorm,  # Set to 2.0 as per the expected options
        param_8=solver,
        param_9=time_shift,
        param_10=seed,
        param_11=rope_scaling,
        param_12=linear_ntk_watershed,
        param_13=proportional_attention,
        api_name="/on_submit"
    )
    return result

# Test the function
caption = "Sunset."
result = generate_image(caption)
print(result)
