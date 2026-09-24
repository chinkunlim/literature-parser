import re
from typing import Optional
from book_processor.verification.ollama_healer import OllamaHealer

class SemanticHeaderFormatter:
    """Uses Ollama to accurately extract and format the Title, Author Block, and Abstract from the first page of an academic journal."""
    
    @staticmethod
    def format_header(full_md: str) -> str:
        healer = OllamaHealer(auto_start=False)
        if not healer.is_available:
            return full_md
            
        first_page_end = full_md.find("<!-- Page 2 -->")
        if first_page_end == -1:
            first_page_end = min(len(full_md), 4000)
            
        header_text = full_md[:first_page_end]
        rest_of_text = full_md[first_page_end:]
        
        prompt = f"""
You are an expert academic typesetter. Rewrite the following raw text from the first page of an academic journal article.
You must return the ENTIRE text provided, but format the Title, Authors, and Abstract exactly as follows:

Requirements:
1. Title MUST be an H1 heading (# Title)
2. Authors and Affiliations MUST be formatted exactly like this:
<div class="author-block">
  <div class="author-name">Author 1</div>
  <div class="author-affiliation">Affiliation 1</div>
</div>
3. Then insert a Table of Contents placeholder:
<details open>
<summary>📑 <b>Table of Contents</b></summary>
[TOC]
</details>
4. The Abstract MUST be an H2 heading followed by a blockquote:
## Abstract
> [Full text of the abstract]
5. Retain all other text (Introduction, etc.) exactly as it is without summarizing.

RAW TEXT TO REWRITE:
{header_text}
"""
        
        try:
            print("  [*] Dispatching Local Ollama AI for semantic header formatting...")
            import json
            import urllib.request
            payload = {
                "model": healer.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 3000}
            }
            req = urllib.request.Request(
                f"{healer.api_base}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                formatted_header = result.get("response", "").strip()
            
            # Remove <think> blocks if Qwen uses them
            formatted_header = re.sub(r'<think>.*?</think>', '', formatted_header, flags=re.DOTALL).strip()
            
            if "author-block" not in formatted_header:
                return full_md
                
            return formatted_header + "\n\n<!-- Page 2 -->\n" + rest_of_text.replace("<!-- Page 2 -->", "", 1).strip()
        except Exception as e:
            print(f"  [⚠️ Semantic Formatter] Failed to format header: {e}")
            return full_md
