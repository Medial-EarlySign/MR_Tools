from llama_cpp import Llama
from llama_cpp.llama_types import (
    CreateChatCompletionResponse,
    ChatCompletionRequestMessage,
    ChatCompletionTool,
    ChatCompletionRequestToolMessage,
    ChatCompletionRequestAssistantMessage,
)


class LLM_Model:
    # 1. Initialize the Model
    def __init__(
        self, sys_prompt: str, temperature: float = 0.3, max_tokens: int = 1024
    ):
        self.llm = Llama(
            model_path="./models/Qwen3.5-9B-UD-Q6_K_XL.gguf",  # Path to your downloaded model
            n_gpu_layers=-1,  # -1 offloads ALL layers
            n_ctx=128000,  # Request a 128k context window
            # --- The 8-Bit KV Cache Magic ---
            flash_attn=True,  # Flash Attention MUST be True to use quantized cache
            type_k=8,  # 8-bit precision for the Key cache (GGML_TYPE_Q8_0)
            type_v=8,  # 8-bit precision for the Value cache (GGML_TYPE_Q8_0)
            verbose=False,  # Keep this True initially to verify memory allocation
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.sys_prompt = sys_prompt

    def create_chat_completion(
        self,
        new_user_request: str,
        messages_history: list[ChatCompletionRequestMessage] | None = None
    ) -> CreateChatCompletionResponse:

        if messages_history is None:
            messages_history = []
        if len(messages_history) == 0 or messages_history[0]["role"] != "system":
            messages_history.insert(0, {"role": "system", "content": self.sys_prompt})
        if new_user_request != "":
            messages_history.append({"role": "user", "content": new_user_request})
        
        # print("Using LLM...")
        res: CreateChatCompletionResponse = self.llm.create_chat_completion(  # type: ignore
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=messages_history,
            stream=False,
        )
        return res

def simple_predict(
    llm: LLM_Model,
    query: str,
    messages: list[ChatCompletionRequestMessage] | None = None,
) -> tuple[str, list[ChatCompletionRequestMessage]]:
    if messages is None:
        messages = []
    response = llm.create_chat_completion(query, messages)
    agent_reply = response["choices"][0]
    content_str: str = agent_reply["message"]["content"]  # type: ignore
    if agent_reply["finish_reason"] == "stop" or agent_reply["finish_reason"] is None:
        return content_str, messages
    stop_reason: str = agent_reply["finish_reason"]
    return "agent was stopped due to " + stop_reason + "\n\n" + content_str, messages