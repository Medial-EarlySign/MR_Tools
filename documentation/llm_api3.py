import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from transformers import StoppingCriteria, StoppingCriteriaList, TextIteratorStreamer
from threading import Thread
import gradio as gr

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
    stop = StopOnTokens()

    model_inputs = tokenizer([message], return_tensors="pt").to(device)
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

def simple_predict(tokenizer, model, device, message,max_new_tokens=512,top_p=None,top_k=None,temperature=None,num_beams=None):
    # Formatting the input for the model.
    history_transformer_format = [[message, ""]]
    messages = "</s>".join(["</s>".join(["\n<|user|>:" + item[0], "\n<|assistant|>:" + item[1]])
                        for item in history_transformer_format])
    
    model_inputs = tokenizer([messages], return_tensors="pt").to(device)
    with torch.no_grad():
        generated_ids = model.generate(**model_inputs, max_new_tokens=max_new_tokens, do_sample=True)
    result = tokenizer.batch_decode(generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    result = result[0]
    full_res = result
    if result.find('<|user|>:', 10) > -1:
        result = result[:result.find('<|user|>:', 10)]
        #skip till assitant:
    result = result[result.find('<|assistant|>:')+14:]
    #Break also in next assistant
    if result.find('<|assistant|>:') > -1:
        result = result[:result.find('<|assistant|>:')]
    return result, full_res

def fetch_tokenizer_and_model():
    tokenizer = AutoTokenizer.from_pretrained("/nas1/Work/LLM/chat_gpt2")
    
    #quantization_config = BitsAndBytesConfig(
    #    load_in_4bit=True,
    #    bnb_4bit_quant_type="nf4",
    #    bnb_4bit_compute_dtype="torch.float16",
    #)
    #attn_implementation="flash_attention_2"
    #quantization_config=True
    #, torch_dtype=torch.float16
    model = AutoModelForCausalLM.from_pretrained("/nas1/Work/LLM/chat_gpt2", \
                                                  device_map="auto")
    # using CUDA for an optimal experience
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    return tokenizer, model, device

if __name__=='__main__':
    # Loading the tokenizer and model from Hugging Face's model hub.
    #
    tokenizer, model, device = fetch_tokenizer_and_model()
    USER_PROMPT='can you show me how to train a model using sklearn in python'
    result = simple_predict(tokenizer, model, device, USER_PROMPT)
    result = result[0]
    print(result)

    # Setting up the Gradio chat interface.
    #gr.ChatInterface(predict,
    #             title="Tinyllama_chatBot",
    #             description="Ask Tiny llama any questions",
    #             examples=['How to cook a fish?', 'Who is the president of US now?']
    #             ).launch()  # Launching the web interface.