from pydantic import BaseModel, ConfigDict, Field, field_validator

class DynamicDiscussion(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: str
    topic: str
    nature: str
    score: float = 0.0
    reason: str
    people_mentioned: list[str] = Field(default_factory=list)

    @field_validator('score', mode='before')
    @classmethod
    def fix_score(cls, v):
        try: return float(v) if v is not None else 0.0
        except: return 0.0

    @field_validator('reason', mode='before')
    @classmethod
    def fix_reason(cls, v):
        if isinstance(v, list): return " ".join(str(i) for i in v)
        return str(v) if v else "No reason"

    @field_validator('people_mentioned', mode='before')
    @classmethod
    def fix_people(cls, v):
        if isinstance(v, list):
            return [str(i['name']) if isinstance(i, dict) and 'name' in i else str(i) for i in v]
        return [str(v)] if v else []

class BatchDiscussionResponse(BaseModel):
    results: list[DynamicDiscussion]