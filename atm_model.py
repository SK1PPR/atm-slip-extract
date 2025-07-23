from pydantic import BaseModel

class Denomination(BaseModel):
    denomination: int
    end: int

class ATM(BaseModel):
    atm_number: str
    branch: str
    date: str
    denominations: list[Denomination]
    
class DiffSlip(BaseModel):
    slip_1: ATM
    slip_2: ATM