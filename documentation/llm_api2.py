import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers import StoppingCriteria, StoppingCriteriaList, TextIteratorStreamer
from threading import Thread
import gradio as gr

from ctransformers import AutoModelForCausalLM

# Set gpu_layers to the number of layers to offload to GPU. Set to 0 if no GPU acceleration is available on your system.


# Defining a custom stopping criteria class for the model's text generation.
class StopOnTokens(StoppingCriteria):
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        stop_ids = [2]  # IDs of tokens where the generation should stop.
        for stop_id in stop_ids:
            if input_ids[0][-1] == stop_id:  # Checking if the last generated token is a stop token.
                return True
        return False

# Function to generate model predictions.
def predict(tokenizer, model, device, message):
    history_transformer_format = [[message, ""]]
    stop = StopOnTokens()

    # Formatting the input for the model.
    messages = "</s>".join(["</s>".join(["\n<|user|>:" + item[0], "\n<|assistant|>:" + item[1]])
                        for item in history_transformer_format])
    model_inputs = tokenizer([messages], return_tensors="pt").to(device)
    streamer = TextIteratorStreamer(tokenizer, timeout=100., skip_prompt=True, skip_special_tokens=True)
    generate_kwargs = dict(
        model_inputs,
        streamer=streamer,
        max_new_tokens=512,
        do_sample=True,
        top_p=0.95,
        top_k=50,
        temperature=0.7,
        num_beams=1,
        stopping_criteria=StoppingCriteriaList([stop])
    )
    t = Thread(target=model.generate, kwargs=generate_kwargs)
    t.start()  # Starting the generation in a separate thread.
    partial_message = ""
    for new_token in streamer:
        partial_message += new_token
        if '</s>' in partial_message:  # Breaking the loop if the stop token is generated.
            break
        yield partial_message

def simple_predict2(tokenizer, model, device, message):
    history_transformer_format = [[message, ""]]
    stop = StopOnTokens()

    # Formatting the input for the model.
    messages = "</s>".join(["</s>".join(["\n<|user|>:" + item[0], "\n<|assistant|>:" + item[1]])
                        for item in history_transformer_format])
    model_inputs = tokenizer([messages], return_tensors="pt").to(device)
    streamer = TextIteratorStreamer(tokenizer, timeout=100., skip_prompt=True, skip_special_tokens=True)
    with torch.no_grad():
        model.generate(
            model_inputs,
            streamer=streamer,
            max_new_tokens=512,
            do_sample=True,
            top_p=0.95,
            top_k=50,
            temperature=0.7,
            num_beams=1,
            stopping_criteria=StoppingCriteriaList([stop])
        )
    partial_message = ""
    for new_token in streamer:
        partial_message += new_token
        if '</s>' in partial_message:  # Breaking the loop if the stop token is generated.
            break
        yield partial_message

def fetch_tokenizer_and_model():
    mdl_path = '/nas1/Work/LLM/mistral_chat'
    tokenizer = AutoTokenizer.from_pretrained(mdl_path)
    #tokenizer.add_special_tokens({"pad_token": "<PAD>"})
    #, torch_dtype=torch.float16
    model = AutoModelForCausalLM.from_pretrained(mdl_path, ignore_mismatched_sizes=True)
    # using CUDA for an optimal experience
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    return tokenizer, model, device

def simple_predict(tokenizer, model, device, message,max_new_tokens=512,top_p=0.95,top_k=50,temperature=0.05,num_beams=1):
    #SYS_PROMPT="You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information."
    #history_transformer_format = [[SYS_PROMPT, "OK"], [message, ""]]
    history_transformer_format = [[message, ""]]
    stop = StopOnTokens()

    # Formatting the input for the model.
    #messages = "</s>".join(["</s>".join(["\n<|user|>:" + item[0], "\n<|assistant|>:" + item[1]])
    #                   for item in history_transformer_format])
    messages = f"A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions. USER: {message} ASSISTANT:"

    model_inputs = tokenizer([messages], return_tensors="pt").to(device)
    with torch.no_grad():
        generated_ids = model.generate(**model_inputs,max_new_tokens=max_new_tokens,do_sample=True,top_p=top_p,top_k=top_k,temperature=temperature,num_beams=num_beams,stopping_criteria=StoppingCriteriaList([stop])    )
    result = tokenizer.batch_decode(generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    result = result[0]
    full_res = result
    
    if result.find('ASSISTANT:') > -1:
        result = result[result.find('ASSISTANT:'):]
    return result, full_res

if __name__=='__main__':
    # Loading the tokenizer and model from Hugging Face's model hub.
    llm = AutoModelForCausalLM.from_pretrained("/nas1/Work/LLM/mistral_chat", model_file="mistral-7b-claude-chat.Q5_K_S.gguf", model_type="mistral", gpu_layers=0)
    #tokenizer, model, device = fetch_tokenizer_and_model()
    print('Starting')
    
    gen=llm('How to train a model in python using tensorflow?', max_new_tokens=400, stream=True)
    for token in gen:
        print(token, end='', flush=True)
    #USER_PROMPT='can you show me how to train a model using sklearn in python'
    #result, full_res = simple_predict(tokenizer,model, device, USER_PROMPT)
    #print(result)

    # Setting up the Gradio chat interface.
    #gr.ChatInterface(predict,
    #             title="Tinyllama_chatBot",
    #             description="Ask Tiny llama any questions",
    #             examples=['How to cook a fish?', 'Who is the president of US now?']
    #             ).launch()  # Launching the web interface.