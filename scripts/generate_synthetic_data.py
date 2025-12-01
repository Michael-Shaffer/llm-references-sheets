import os
import json
import glob
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain.schema import SystemMessage, HumanMessage

# Configuration
RAW_DOCS_DIR = "data/raw_docs"
OUTPUT_FILE = "data/dataset.jsonl"
VLLM_API_BASE = "http://localhost:8000/v1"
MODEL_NAME = "/models/Meta-Llama-3.1-8B-Instruct"  # Use the model name the server knows

# Initialize LLM
llm = ChatOpenAI(
    openai_api_key="EMPTY",
    openai_api_base=VLLM_API_BASE,
    model_name=MODEL_NAME,
    temperature=0.7,
    max_tokens=1024
)

def load_json_docs(directory: str) -> List[Dict[str, Any]]:
    """Load all JSON files from the directory and return list of doc objects."""
    docs = []
    for file_path in glob.glob(os.path.join(directory, "*.json")):
        print(f"Loading {file_path}...")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                # Support both list of docs and single doc
                if isinstance(content, list):
                    docs.extend(content)
                else:
                    docs.append(content)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    return docs

def generate_qa_pairs(doc: Dict[str, Any]) -> List[dict]:
    """Ask the LLM to generate Q&A pairs from a document object."""
    
    doc_title = doc.get('doc_title', 'Unknown Document')
    section = doc.get('section', 'General')
    page = doc.get('page', 'N/A')
    text = doc.get('text', '')

    if not text.strip():
        return []
        
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=(
            "You are an expert dataset creator. Your task is to create high-quality "
            "instruction-response pairs for fine-tuning a Large Language Model."
        )),
        HumanMessage(content=f"""
        Read the following text from the document "{doc_title}", Section "{section}":
        
        <context>
        {text}
        </context>
        
        Generate 3 to 5 distinct Question and Answer pairs based *only* on this context.
        
        Guidelines:
        1. Include the context of the document or section in the question if relevant (e.g., "According to [Title]...").
        2. Questions should be specific and technical.
        3. Answers should be detailed and directly supported by the text.
        
        Format the output as a JSON list of objects:
        [
            {{"instruction": "Question text", "output": "Answer text"}}
        ]
        
        Return ONLY the JSON list.
        """)
    ])
    
    try:
        response = llm.invoke(prompt.format_messages())
        content = response.content.strip()
        
        # Basic cleanup to ensure we get just the JSON list
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
             content = content.split("```")[1].split("```")[0].strip()
             
        data = json.loads(content)
        
        # Add metadata to the training example if useful, or just standard instruction format
        for item in data:
            if 'input' not in item:
                item['input'] = "" 
                # Optional: You could put "Context: {doc_title}, Section {section}" into 'input'
                
        return data
    except json.JSONDecodeError:
        print("Failed to parse JSON from LLM response.")
        print("Raw response:", response.content)
        return []
    except Exception as e:
        print(f"Error generating Q&A: {e}")
        return []

def main():
    print(f"Scanning {RAW_DOCS_DIR} for JSON documents...")
    
    # 1. Load Documents
    docs = load_json_docs(RAW_DOCS_DIR)
    
    if not docs:
        print("No JSON documents found. Add .json files to data/raw_docs/")
        # Create a sample JSON for testing
        sample_doc = {
            "doc_title": "STARS Quick Reference Guide",
            "section": "1.2 System Overview",
            "page": 5,
            "text": "The Standard Terminal Automation Replacement System (STARS) is a joint FAA and DoD program..."
        }
        with open(os.path.join(RAW_DOCS_DIR, "stars_sample.json"), "w") as f:
            json.dump([sample_doc], f, indent=2)
        print("Created dummy file. Rerun to use it.")
        return

    print(f"Loaded {len(docs)} document sections.")

    # 2. Generate Q&A
    new_examples = []
    for i, doc in enumerate(docs):
        print(f"Processing document {i+1}/{len(docs)}: {doc.get('doc_title', '')} - {doc.get('section', '')}...")
        
        # If text is too long, split it (simple splitter for now)
        text = doc.get('text', '')
        if len(text) > 4000:
            splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
            chunks = splitter.split_text(text)
            for chunk in chunks:
                sub_doc = doc.copy()
                sub_doc['text'] = chunk
                pairs = generate_qa_pairs(sub_doc)
                new_examples.extend(pairs)
        else:
            pairs = generate_qa_pairs(doc)
            new_examples.extend(pairs)
            
        print(f"Generated {len(pairs)} pairs.")

    # 3. Append to Dataset
    print(f"Appending {len(new_examples)} new examples to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for example in new_examples:
            f.write(json.dumps(example) + "\n")
    
    print("Done!")

if __name__ == "__main__":
    main()
