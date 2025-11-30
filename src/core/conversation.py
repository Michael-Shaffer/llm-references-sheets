from typing import Dict
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

# Configuration
VLLM_API_BASE = "http://localhost:8000/v1"
MODEL_NAME = "/models/Meta-Llama-3.1-8B-Instruct"
MAX_TOKEN_LIMIT = 2000

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, ConversationChain] = {}
        
        # Initialize the LLM (shared across sessions to save resources, 
        # though chains are per-session)
        self.llm = ChatOpenAI(
            openai_api_key="EMPTY",
            openai_api_base=VLLM_API_BASE,
            model_name=MODEL_NAME,
            max_tokens=1024,
            temperature=0.7,
            streaming=True
        )

    def get_chain(self, session_id: str) -> ConversationChain:
        """
        Retrieve or create a ConversationChain for the given session_id.
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = self._create_new_chain()
        return self.sessions[session_id]

    def _create_new_chain(self) -> ConversationChain:
        # Memory with summary buffer
        memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            max_token_limit=MAX_TOKEN_LIMIT,
            return_messages=True
        )

        # Custom Prompt
        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(
                "You are Polaris, an intelligent assistant. "
                "Use the conversation history to provide relevant context."
            ),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{input}")
        ])

        return ConversationChain(
            llm=self.llm,
            memory=memory,
            prompt=prompt,
            verbose=True
        )

# Global instance
session_manager = SessionManager()
