"""Skills by category with an LLM (Module 12): discover a skill list, then tag postings against it."""
import json
from collections import Counter
from pathlib import Path

import anthropic
import yaml

from core import settings


# LLM model constants and limits
MODEL = "claude-haiku-5-5"
# USD per million tokens for MODEL, for prompts under 100K tokens (October 2026 prices).
PRICE_IN = 0.10
PRICE_OUT = 0.50
MAX_TEXT_CHARS = 8000  # long descriptions are cut here to cap the cost per job


# Skill discovery constants
CATEGORIES = ["technical", "communication", "business", "leadership"]
LEVELS = ["required", "preferred"]
MAX_OTHER = 5  # new skills kept per posting

CATEGORY_HELP = (
    "Categories:\n"
    "- technical: tools, languages, methods and engineering practices\n"
    "- communication: presenting, writing, explaining, influencing, collaborating\n"
    "- business: domain knowledge, metrics, product and commercial judgment\n"
    "- leadership: ownership, mentoring, managing ambiguity, driving work forward"
)
IGNORE = (
    "Ignore the company description, benefits, pay, legal and equal-opportunity text. "
    "Do not count education, years of experience or work authorization as skills."
)

class Claude:
    
    def __init__(self,client=None,model:str=MODEL):
        self.client = client or anthropic.Anthropic(api_key=settings.get("ANTHROPIC_API_KEY"))
        self.model = model
        self.input_tokens = 0
        self.output_tokens = 0
        
    def ask(self,*,system:str,content:str,schema:dict, max_tokens:int, effort:str = 'low') -> dict:
        response = self.client.messages.create(
            model = self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
            thinking={"type": "disabled"},
        )
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        return json.loads(next(block.text for block in response.content if block.type == "text"))
    
    @property
    def cost_usd(self) -> float:
        return self.input_tokens / 1_000_000 * PRICE_IN + self.output_tokens / 1_000_000 * PRICE_OUT


# ---------- Pass 1: discover the skill list ----------
"""_summary_
Pass 1 is about building a skill pool from a sample. 
Pass 2 is about going through each of the queried postings and tagging    
them using the skills from the pool 
"""

OPEN_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "category": {"type": "string", "enum": CATEGORIES}},
                "required": ["name", "category"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["skills"],
    "additionalProperties": False,
}

LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "skill": {"type": "string"},
                    "category": {"type": "string", "enum": CATEGORIES},
                    "definition": {"type": "string"},
                },
                "required": ["skill", "category", "definition"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["skills"],
    "additionalProperties": False,
}

def extract_open(claude:Claude, text: str) -> list[dict]:
    """Extract a list of skills from job postings, in short words of the model's choosing.
    48 | technical | sql
    21 | technical | sql queries
    12 | technical | advanced sql
    9  | technical | writing sql
    7  | technical | postgresql  
    """
    if not text:
        return []
    system = (
        "You extract skills from job postings for a labor-market analysis. List every skill the "
        "posting asks for, as a short noun phrase (2 to 6 words), with its category. Include "
        f"non-technical skills as well as technical ones. {IGNORE}\n\n{CATEGORY_HELP}"
    )
    reply = claude.ask(system = system, content = text[:MAX_TEXT_CHARS], schema = OPEN_SCHEMA, max_tokens = 800)
    return reply['skills']


def build_list(claude: Claude, counts: Counter, size: str = "40 to 60") -> list[dict]:
    """Group raw phrases (with how often each appeared) into one list of named, categorized skills."""
    lines = "\n".join(f"{n} | {category} | {phrase}" for (phrase, category), n in counts.most_common(400))
    system = (
        "You design a skill taxonomy for a labor-market analysis of data jobs. You get skill phrases "
        "extracted from job postings, with how many postings used each. Merge phrases that mean the "
        f"same thing into one skill, and return a list of {size} skills that covers the frequent "
        "phrases. Give each skill a clear name (2 to 6 words), one category, and a one-sentence "
        "definition that says what counts as this skill.\n\n" + CATEGORY_HELP
    )
    reply = claude.ask(system=system, content="count | category | phrase\n" + lines,
                       schema=LIST_SCHEMA, max_tokens=8000, effort="medium")
    return reply["skills"]

# ---------- Pass 2: tag postings against the list ----------
class SkillTagger:
    
    def __init__(self, skills: list[dict], claude: Claude):
        self.skills = skills
        self.claude = claude
        self.names = {s["skill"] for s in skills}
        
        by_category = []
        for category in CATEGORIES:
            lines = [f"- {s['skill']}: {s['definition']}" for s in skills if s["category"] == category]
            if lines:
                by_category.append(f"{category.capitalize()}:\n" + "\n".join(lines))
                
        self.system = (
            "You tag job postings for a labor-market analysis. From the skill list below, choose "
            "every skill the posting asks for, and mark each 'required', or 'preferred' when the "
            "posting calls it a plus, a bonus, nice to have or preferred. Choose a skill only if "
            "the posting asks for it; a passing mention is not enough.\n"
            f"Then list up to {MAX_OTHER} other skills the posting asks for that none of the listed "
            f"skills cover, as short noun phrases. {IGNORE}\n\n" + "\n\n".join(by_category)
        )
        self.schema = {
            "type": "object",
            "properties": {
                "skills": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "skill": {"type": "string", "enum": self.names},
                            "level": {"type": "string", "enum": LEVELS},
                        },
                        "required": ["skill", "level"],
                        "additionalProperties": False,
                    },
                },
                "other_skills": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["skills", "other_skills"],
            "additionalProperties": False,
        }
    
    @classmethod
    def from_yaml(cls,path:str | Path, **kwargs) -> "SkillTagger":
       return cls(yaml.safe_load(Path(path).read_text(encoding='utf-8')), **kwargs)
   
    def tag(self, text:str|None) -> tuple[dict[str,str],list[str]]:
        if not text:
            return {}, []
        reply = self.claude.ask(
            system=self.system, 
            content = text[:MAX_TEXT_CHARS], 
            schema=self.schema,
            max_tokens=800
            )
        known = {n.lower(): n for n in self.names}
        found: dict[str,str]={}
        
        for item in reply['skills']:
            # reply['skills'] has blocks like {"skill": "sql", "level": "required"} or {"skill": "sql queries", "level": "preferred"}
            name = known.get(item['skill'].lower())
            # name is original capitalization skill name from the list, or None if the skill is not in the list
            if name and found.get(name) != "required":
            # add it if it’s (1) not empty, (2) not already added as required.
                found[name] = item['level']

        """
        Pass 1: item = {"skill": "Mentoring", "level": "required"}
        name = known.get("mentoring")   → "Mentoring"
        found.get("Mentoring")          → None (not written yet)
        condition: "Mentoring" and None != "required"  → True
        found = {"Mentoring": "required"}

        Pass 2: item = {"skill": "SQL", "level": "required"}
        name = known.get("sql")         → "SQL"
        found.get("SQL")                → None
        condition → True
        found = {"Mentoring": "required", "SQL": "required"}

        Pass 3: item = {"skill": "SQL", "level": "preferred"}
        name = known.get("sql")         → "SQL"
        found.get("SQL")                → "required"   ← already on the sheet as required
        condition: "SQL" and "required" != "required"  → False
        skipped: found is unchanged
        """
        
        other = []
        for phrase in reply["other_skills"]:
            phrase = " ".join(phrase.lower().split())
            if phrase and phrase not in other and phrase not in known:
                other.append(phrase)
        return found, other[:MAX_OTHER]
        
















