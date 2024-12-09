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

# Expanded pre-populated questions
PREDEFINED_QUESTIONS = [
    "Select a question...",
    "Tell me how can I navigate to a specific pose - include replanning aspects in your answer.",
    "Can you provide me with code for this task?",
    "How do I set up obstacle avoidance in ROS2 navigation?",
    "What are the key parameters for tuning the nav2 planner?",
    "How do I integrate custom recovery behaviors?"
]

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

def question_selected(question):
    if question == "Select a question...":
        return ""
    return question

@spaces.GPU
def respond(message, history, system_message, max_tokens, temperature, top_p):
    try:
        # Initialize chat history if None
        history = history or []
        
        if not message.strip():
            history.append((message, "Please enter a question or select one from the dropdown menu."))
            return history
            
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
        
        # Add the new exchange to history
        history.append((message, output.strip()))
        
        return history
        
    except Exception as e:
        history.append((message, f"An error occurred: {str(e)}"))
        return history

def clear_input():
    return gr.Textbox.update(value="")

# Create the Gradio interface
with gr.Blocks(title="ROS2 Expert Assistant") as demo:
    gr.Markdown("# ROS2 Expert Assistant")
    gr.Markdown("Ask questions about ROS2, navigation, and robotics. I'll provide concise answers based on the available documentation.")
    
    with gr.Row():
        with gr.Column(scale=8):
            # Dropdown for predefined questions
            question_dropdown = gr.Dropdown(
                choices=PREDEFINED_QUESTIONS,
                value="Select a question...",
                label="Pre-defined Questions"
            )
        
    with gr.Row():
        # Chat interface
        chatbot = gr.Chatbot()
    
    with gr.Row():
        # Message input
        msg = gr.Textbox(
            label="Your Question",
            placeholder="Type your question here or select one from the dropdown above...",
            lines=2
        )
        
    with gr.Row():
        submit = gr.Button("Submit")
        clear = gr.Button("Clear")
        
    with gr.Accordion("Advanced Settings", open=False):
        system_message = gr.Textbox(
            value=DEFAULT_SYSTEM_PROMPT,
            label="System Message",
            lines=3
        )
        max_tokens = gr.Slider(
            minimum=1,
            maximum=2048,
            value=500,
            step=1,
            label="Max new tokens"
        )
        temperature = gr.Slider(
            minimum=0.1,
            maximum=4.0,
            value=0.1,
            step=0.1,
            label="Temperature"
        )
        top_p = gr.Slider(
            minimum=0.1,
            maximum=1.0,
            value=0.95,
            step=0.05,
            label="Top-p"
        )
    
    # Add custom CSS for tooltip
    gr.Markdown("""
        <style>
        .tooltip {
            cursor: help;
            font-size: 1.2em;
        }
        </style>
    """)
    
    # Event handlers
    question_dropdown.change(
        question_selected,
        inputs=[question_dropdown],
        outputs=[msg]
    )
    
    def submit_and_clear(message, history, system_message, max_tokens, temperature, top_p):
        # First get the response
        new_history = respond(message, history, system_message, max_tokens, temperature, top_p)
        # Then clear the input
        return new_history, gr.Textbox.update(value="")
    
    submit.click(
        submit_and_clear,
        inputs=[
            msg,
            chatbot,
            system_message,
            max_tokens,
            temperature,
            top_p
        ],
        outputs=[chatbot, msg]
    )
    
    clear.click(lambda: (None, ""), None, [chatbot, msg], queue=False)
    msg.submit(
        submit_and_clear,
        inputs=[
            msg,
            chatbot,
            system_message,
            max_tokens,
            temperature,
            top_p
        ],
        outputs=[chatbot, msg]
    )

if __name__ == "__main__":
    demo.launch(share=True)