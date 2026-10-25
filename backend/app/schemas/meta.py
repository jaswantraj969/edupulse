"""Public installation facts for the login page."""

from typing import Literal

from pydantic import BaseModel, Field


class DemoAccount(BaseModel):
    role: Literal["admin", "teacher"]
    label: str
    email: str
    password: str


class Meta(BaseModel):
    demo_mode: bool = Field(description="The installation holds synthetic demo data")
    public_demo: bool = Field(description="Anyone can use this installation; it is reset regularly")
    demo_reset_hours: int = Field(description="Reset interval of the public demo, in hours")
    demo_accounts: list[DemoAccount] = Field(
        description="Sign-in details shown on the login page; always empty unless demo_mode"
    )
