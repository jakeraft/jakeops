from pydantic import BaseModel


class GitHubIssue(BaseModel):
    number: int
    title: str
    html_url: str
    state: str
    body: str = ""
