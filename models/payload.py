from pydantic import BaseModel


class GiveawayConfig(BaseModel):
    prize_name: str
    keyword: str
    winners: int
    duration: int
