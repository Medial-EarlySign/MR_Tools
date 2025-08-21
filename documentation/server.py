#python 3.10

from fastapi import FastAPI, Request, Response  
import torch, json, sys
from fetch_conf import DB_Access
from llm_api import simple_predict, fetch_tokenizer_and_model
#from llm_api2 import simple_predict, fetch_tokenizer_and_model
#from llm_api3 import simple_predict, fetch_tokenizer_and_model

app = FastAPI()
app.model=None
app.tokenizer=None

app.CONNECTION_STRING='mssql+pyodbc://confuser:2w#E#E2w@confluence'
app.db=None
app.db_data=None
app.SYSTEM_INS_PROMPT=None
app.SYSTEM_INS_PROMPT_MEDIAL=None
app.USE_GPU=True
app.USE_CONFLUENCE=False

@app.on_event("startup")
async def startup_event():
    app.SYSTEM_INS_PROMPT="You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information."
    if app.USE_CONFLUENCE:
        IGNORE_TITLES=['Influenza Complications', 'THIN Signals', 'Signals map', 'Signals', 'Signal', 'NWP', 'Readmission', 'Prostate', 'THIN - 1601']
        app.db=DB_Access(app.CONNECTION_STRING)
        app.db_data=app.db.fetch_data()
        app.db_data['final_text']= 'Title: ' +  app.db_data['TITLE'] + '\nContent: ' + app.db_data['text']
        app.db_data=app.db_data[~app.db_data['TITLE'].isin(IGNORE_TITLES)]
        full_text=app.db_data['final_text'].sum()
        app.SYSTEM_INS_PROMPT_MEDIAL= app.SYSTEM_INS_PROMPT + "\nPlease use this information to answer the question: " + full_text
        print('Finished fetch confluence data')
        
    app.tokenizer, app.model, app.device = fetch_tokenizer_and_model()
    print('Model loaded!')

def get_result(js_data_str, response : Response, SYS_PROMT: str):
    response.headers["Access-Control-Allow-Origin"] = "*"
    try:
        js_data=json.loads(js_data_str)
    except:
        print(js_data_str)
        return {'error': 'please pass valid json'}
    if 'query' not in js_data:
        print(js_data)
        return {'error': 'please pass query element in request'}
    temperature = 0.05
    if 'temperature' in js_data:
        temperature = float(js_data['temperature'])
    max_new_tokens = 512
    if 'max_new_tokens' in js_data:
        max_new_tokens = int(js_data['max_new_tokens'])
    num_beams = 1
    if 'num_beams' in js_data:
        num_beams = int(js_data['num_beams'])
    top_k = 50
    if 'top_k' in js_data:
        top_k = int(js_data['top_k'])
    top_p = 0.95
    if 'top_p' in js_data:
        top_p = float(js_data['top_p'])
    print(js_data)
    USER_PROMPT=js_data['query']
    
    #sys_inst={'role':'system', 'content': SYS_PROMT}
    #user_inst={'role': 'user', 'content': USER_PROMPT}
    #dialog=[sys_inst, user_inst]
    #prompt = SYS_PROMT + '\nHere is user question:\n' + USER_PROMPT
    #return {'response': "Of course! I'd be happy to help you with that.\n\nBefore we begin, could you please clarify what type of model you would like to train using scikit-learn in Python? There are several types of models available in scikit-learn, such as linear regression, logistic regression, decision trees, random forests, and support vector machines, to name a few. Additionally, could you please provide some more details about the data you will be using to train the model? This information will help me provide a more tailored response.\n\nPlease note that scikit-learn is a powerful library, and training a model can be a complex process. It's important to ensure that you have a solid understanding of the underlying concepts and techniques before attempting to train a model. If you're new to machine learning or scikit-learn, I would recommend starting with some online tutorials or courses to gain a better understanding of the basics before moving on to more advanced topics.\n\nOnce you have a clear understanding of the basics, you can use the scikit-learn library to train a model using a variety of techniques, such as cross-validation, feature selection, and hyperparameter tuning.\n\nHere's"}
    
    sys.setrecursionlimit(100000)
    prompt = USER_PROMPT
    result, full_res = simple_predict(app.tokenizer, app.model, app.device, prompt, max_new_tokens,top_p,top_k,temperature,num_beams)
    #final_result= result[0]
    #for text in result:
    #    final_result += text + ' '
    #output_text= apply_model(app.model, app.tokenizer, dialog, app.USE_GPU)
    #clean_answer=get_just_answer(output_text)
    res= {'response': full_res }
    #print (res)
    return res

@app.post("/")
async def index(request: Request, response : Response):
    js_body = await request.body()
    js_body=js_body.decode('utf-8')
    return get_result(js_body, response, app.SYSTEM_INS_PROMPT)

@app.post("/medial")
async def index(request: Request, response : Response):
    if not(app.USE_CONFLUENCE):
        response.headers["Access-Control-Allow-Origin"] = "*"
        return { "error" : "unsupported yet" }
    js_body = await request.body()
    js_body=js_body.decode('utf-8')
    return get_result(js_body, response, app.SYSTEM_INS_PROMPT_MEDIAL)

