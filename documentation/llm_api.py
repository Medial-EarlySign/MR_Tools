#python 3.10
from transformers import AutoTokenizer, AutoModelForCausalLM
from chat_utils import format_tokens
import json, torch

def apply_model(model, tokenizer, dialog,max_new_tokens=1024, temperature=1.0, top_p=1.0, top_k=50, cuda=False):
    dialogs=[dialog]
    chats = format_tokens(dialogs, tokenizer)
    chat=chats[0]
    
    do_sample=True
    use_cache=True
    repetition_penalty=1
    length_penalty=1
    tokens= torch.tensor(chat).long()
    tokens= tokens.unsqueeze(0)
    if cuda:
        tokens=tokens.to(torch.device('cuda'))
    print('Apply model')
    with torch.no_grad():
        outputs = model.generate(input_ids=tokens,max_new_tokens=max_new_tokens,do_sample=do_sample,top_p=top_p,temperature=temperature,use_cache=use_cache,top_k=top_k,repetition_penalty=repetition_penalty,length_penalty=length_penalty)
    print('Decode text')
    output_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return output_text

def fetch_tokenizer_and_model():
    #MODEL_PATH = "/nas1/Work/python-resources/common/llama/13B"
    MODEL_PATH = "/nas1/Work/python-resources/common/llama/7B"
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    tokenizer.add_special_tokens({"pad_token": "<PAD>"})
    #, torch_dtype=torch.float16
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH)
    # using CUDA for an optimal experience
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    return tokenizer, model, device

def simple_predict(tokenizer, model, device, message,max_new_tokens=512,top_p=1.0,top_k=50,temperature=1.0,num_beams=None):
    SYSTEM_INS_PROMPT="You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information."

    sys_inst={'role':'system', 'content': SYSTEM_INS_PROMPT}
    user_inst={'role': 'user', 'content': message}

    dialog=[sys_inst, user_inst]
    seed=42
    torch.cuda.manual_seed(seed)
    output_text= apply_model(model, tokenizer, dialog, max_new_tokens, temperature,top_p ,top_k)
    clean_answer=get_just_answer(output_text)
    return clean_answer, output_text

def get_just_answer(output_text):
    return output_text[output_text.find('[/INST]')+7:].strip()

if __name__=='__main__':
    MODEL_PATH="/nas1/Work/python-resources/common/llama/13B/"

    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    tokenizer.add_special_tokens({"pad_token": "<PAD>"})
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, torch_dtype=torch.float16)
    #model.to(torch.device('cuda'))

    SYSTEM_INS_PROMPT="You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information."
    USER_PROMPT='Write a brief birthday message to John'

    sys_inst={'role':'system', 'content': SYSTEM_INS_PROMPT}
    user_inst={'role': 'user', 'content': USER_PROMPT}

    dialog=[sys_inst, user_inst]
    seed=42
    torch.cuda.manual_seed(seed)

    print('Model loaded!')
    #convert data

    #Test zero shoot:
    output_text= apply_model(model, tokenizer, dialog)
    clean_answer=get_just_answer(output_text)

    print(output_text)

    #now fine tune => to save after pretune
