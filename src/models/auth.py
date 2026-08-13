from pydantic import BaseModel,Field

class UserSignup(BaseModel):
    email:str=Field(max_length=20)
    password:str = Field(max_length=10)
    role:str
    user_name:str=Field(max_length=15)


class UserLogin(BaseModel):
    email:str
    password:str
