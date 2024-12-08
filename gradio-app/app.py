import spaces
import os
import gradio as gr
import torch
from transformers import AutoTokenizer, TextStreamer, pipeline, AutoModelForCausalLM
from langchain_community.embeddings import HuggingFaceInstructEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_community.llms import HuggingFacePipeline

# System prompts
DEFAULT_SYSTEM_PROMPT = """
You are a ROS2 expert assistant. Based on the context provided, give direct and concise answers.
If the information is not in the context, respond with "I don't find that information in the available documentation."
Keep responses to 1-2 lines maximum.
""".strip()

def generate_prompt(context: str, question: str, system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> str:
    return f"""
[INST] <<SYS>>
{system_prompt}
<</SYS>>
Context: {context}
Question: {question}
Answer: [/INST]
""".strip()

# Initialize embeddings and database
embeddings = HuggingFaceInstructEmbeddings(
    model_name="hkunlp/instructor-base",
    model_kwargs={"device": "cpu"}
)

db = Chroma(
    persist_directory="db",
    embedding_function=embeddings
)

def initialize_model():
    model_id = "meta-llama/Llama-3.2-3B-Instruct"
    token = os.environ.get("HF_TOKEN")
    
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        token=token,
        device_map="cuda" if torch.cuda.is_available() else "cpu"
    )
    
    return model, tokenizer

class CustomTextStreamer(TextStreamer):
    def __init__(self, tokenizer, skip_prompt=True, skip_special_tokens=True):
        super().__init__(tokenizer, skip_prompt=skip_prompt, skip_special_tokens=skip_special_tokens)
        self.output_text = ""

    def put(self, value):
        self.output_text += value
        super().put(value)

@spaces.GPU
def respond(message, history, system_message, max_tokens, temperature, top_p):
    try:
        model, tokenizer = initialize_model()
        
        # Get context from database
        retriever = db.as_retriever(search_kwargs={"k": 2})
        docs = retriever.get_relevant_documents(message)
        context = "\n".join([doc.page_content for doc in docs])
        
        # Generate prompt
        prompt = generate_prompt(context=context, question=message, system_prompt=system_message)
        
        # Set up the pipeline
        text_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            repetition_penalty=1.15
        )
        
        # Generate response
        output = text_pipeline(
            prompt,
            return_full_text=False,
            max_new_tokens=max_tokens
        )[0]['generated_text']
        
        yield output.strip()
        
    except Exception as e:
        yield f"An error occurred: {str(e)}"
# def respond(message, history, system_message, max_tokens, temperature, top_p):
#     try:
#         model, tokenizer = initialize_model()
        
#         # Get relevant context from the database
#         retriever = db.as_retriever(search_kwargs={"k": 2})
#         docs = retriever.get_relevant_documents(message)
#         context = "\n".join([doc.page_content for doc in docs])
        
#         # Generate the complete prompt
#         prompt = generate_prompt(context=context, question=message, system_prompt=system_message)
        
#         # Set up the streamer
#         streamer = CustomTextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
        
#         # Set up the pipeline
#         text_pipeline = pipeline(
#             "text-generation",
#             model=model,
#             tokenizer=tokenizer,
#             max_new_tokens=max_tokens,
#             temperature=temperature,
#             top_p=top_p,
#             repetition_penalty=1.15,
#             streamer=streamer,
#         )
        
#         # Generate response
#         _ = text_pipeline(prompt, max_new_tokens=max_tokens)
        
#         # Return only the generated response
#         yield streamer.output_text.strip()
        
#     except Exception as e:
#         yield f"An error occurred: {str(e)}"

# Create Gradio interface
demo = gr.ChatInterface(
    respond,
    additional_inputs=[
        gr.Textbox(
            value=DEFAULT_SYSTEM_PROMPT,
            label="System Message",
            lines=3,
            visible=False
        ),
        gr.Slider(
            minimum=1,
            maximum=2048,
            value=500,
            step=1,
            label="Max new tokens"
        ),
        gr.Slider(
            minimum=0.1,
            maximum=4.0,
            value=0.1,
            step=0.1,
            label="Temperature"
        ),
        gr.Slider(
            minimum=0.1,
            maximum=1.0,
            value=0.95,
            step=0.05,
            label="Top-p"
        ),
    ],
    title="ROS2 Expert Assistant",
    description="Ask questions about ROS2, navigation, and robotics. I'll provide concise answers based on the available documentation.",
)

if __name__ == "__main__":
    demo.launch(share=True)