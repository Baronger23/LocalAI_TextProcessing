"""
LLM module using Ollama.
"""
from typing import Optional, List, Dict, Any
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.config import OLLAMA_BASE_URL, LLM_MODEL, LLM_TEMPERATURE


class LLMManager:
    """Manage LLM interactions using Ollama."""
    
    def __init__(
        self,
        model: str = LLM_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        temperature: float = LLM_TEMPERATURE
    ):
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self._llm = None
    
    @property
    def llm(self) -> OllamaLLM:
        """Get or create LLM instance."""
        if self._llm is None:
            self._llm = OllamaLLM(
                model=self.model,
                base_url=self.base_url,
                temperature=self.temperature
            )
        return self._llm
    
    def invoke(self, prompt: str) -> str:
        """Send a prompt to the LLM and get response."""
        return self.llm.invoke(prompt)
    
    def create_chain(self, prompt_template: str):
        """Create a chain with a prompt template."""
        prompt = PromptTemplate.from_template(prompt_template)
        chain = prompt | self.llm | StrOutputParser()
        return chain
    
    def generate_response(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate a response using context."""
        if system_prompt is None:
            system_prompt = """Bạn là trợ lý AI thông minh. Hãy trả lời câu hỏi dựa trên ngữ cảnh được cung cấp.
Nếu không tìm thấy thông tin trong ngữ cảnh, hãy nói rằng bạn không có đủ thông tin.
Trả lời bằng tiếng Việt một cách rõ ràng và chính xác."""
        
        prompt_template = f"""{system_prompt}

Ngữ cảnh:
{{context}}

Câu hỏi: {{query}}

Trả lời:"""
        
        chain = self.create_chain(prompt_template)
        return chain.invoke({"context": context, "query": query})
