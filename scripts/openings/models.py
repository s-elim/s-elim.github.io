from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class RelevanceExplanation(BaseModel):
    matched_topics: List[str] = Field(default_factory=list)
    technical_alignment: Optional[str] = None
    research_alignment: Optional[str] = None
    qualification_alignment: Optional[str] = None
    potential_gaps: Optional[str] = None

class HistoryEvent(BaseModel):
    date: str
    event: str

class Opening(BaseModel):
    id: str
    title: str
    position_type: str
    institution: str
    department: Optional[str] = "Not specified"
    lab: Optional[str] = "Not specified"
    principal_investigator: Optional[str] = "Not specified"
    city: Optional[str] = "Not specified"
    country: str
    region: str
    research_topics: List[str] = Field(default_factory=list)
    description: Optional[str] = ""
    requirements: List[str] = Field(default_factory=list)
    preferred_qualifications: List[str] = Field(default_factory=list)
    salary: Optional[str] = "Not specified"
    funding: Optional[str] = "Not specified"
    deadline: Optional[str] = None
    deadline_human: Optional[str] = "Rolling / Open until filled"
    start_date: Optional[str] = "Not specified"
    employment_type: Optional[str] = "Full-time"
    status: str = "Open"
    relevance: str = "Potentially Relevant"
    relevance_explanation: Optional[RelevanceExplanation] = None
    source: str
    source_url: str
    application_url: Optional[str] = None
    first_seen: str
    last_seen: str
    last_verified: str
    history: List[HistoryEvent] = Field(default_factory=list)
    source_urls: List[str] = Field(default_factory=list)
    content_hash: Optional[str] = None

class DiscoveredItem(BaseModel):
    title: str
    url: str
    source_name: str
    source_type: str  # official_university, official_lab, euraxess, linkedin, etc.
    snippet: Optional[str] = ""
    raw_html: Optional[str] = ""
    detected_institution: Optional[str] = None
    detected_country: Optional[str] = None
