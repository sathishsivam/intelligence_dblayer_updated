from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from decimal import Decimal

app = FastAPI(
    title="Banking Fund Transfer API",
    description="Simple API for transferring funds between accounts",
    version="1.0.0"
)


# ============================================================
# DATA MODEL
# ============================================================

class Account:
    def __init__(self, account_id: int, holder_name: str, balance: Decimal):
        self.account_id = account_id
        self.holder_name = holder_name
        self.balance = balance


class TransferRequest(BaseModel):
    from_account: int
    to_account: int
    amount: Decimal = Field(gt=0)

class BeneficiaryRequest(BaseModel): 
    beneficiary_name: str = Field(min_length=2, max_length=100) 
    beneficiary_account: int 
    bank_name: str = Field(min_length=2, max_length=100) 
    ifsc_code: str = Field(min_length=11, max_length=11)



# ============================================================
# IN-MEMORY ACCOUNTS
# ============================================================

accounts = {
    101: Account(101, "Ravi", Decimal("50000.00")),
    102: Account(102, "Kumar", Decimal("25000.00")),
    103: Account(103, "Suresh", Decimal("10000.00")),
}

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "UP"
    }

# ============================================================
# GET ACCOUNT
# ============================================================

@app.get("/accounts/{account_id}")
def get_account(account_id: int):

    account = accounts.get(account_id)

    if not account:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )

    return {
        "account_id": account.account_id,
        "holder_name": account.holder_name,
        "balance": str(account.balance)
    }


# ============================================================
# FUND TRANSFER
# ============================================================

@app.post("/transfer")
def transfer_funds(request: TransferRequest):

    # 1. Check source account
    from_account = accounts.get(request.from_account)

    if not from_account:
        raise HTTPException(
            status_code=404,
            detail="Source account not found"
        )

    # 2. Check destination account
    to_account = accounts.get(request.to_account)

    if not to_account:
        raise HTTPException(
            status_code=404,
            detail="Destination account not found"
        )

    # 3. Prevent same-account transfer
    if request.from_account == request.to_account:
        raise HTTPException(
            status_code=400,
            detail="Source and destination accounts cannot be the same"
        )

    # 4. Check sufficient balance
    if from_account.balance < request.amount:
        raise HTTPException(
            status_code=400,
            detail="Insufficient balance"
        )

    # 5. Debit source account
    from_account.balance -= request.amount

    # 6. Credit destination account
    to_account.balance += request.amount

    # 7. Return transfer result
    return {
        "status": "SUCCESS",
        "message": "Fund transfer completed successfully",
        "from_account": request.from_account,
        "to_account": request.to_account,
        "amount": str(request.amount),
        "from_account_balance": str(from_account.balance),
        "to_account_balance": str(to_account.balance)
    }




# ============================================================
# IN-MEMORY BENEFICIARY DATA
# Key = source account ID
# ============================================================

beneficiaries = {
    101: [
        {
            "beneficiary_id": "BEN001",
            "beneficiary_name": "Kumar",
            "beneficiary_account": 102,
            "bank_name": "Mock Bank",
            "ifsc_code": "MOCK0000001",
            "status": "ACTIVE",
        },
        {
            "beneficiary_id": "BEN002",
            "beneficiary_name": "Suresh",
            "beneficiary_account": 103,
            "bank_name": "Mock Bank",
            "ifsc_code": "MOCK0000001",
            "status": "ACTIVE",
        },
    ],
    102: [
        {
            "beneficiary_id": "BEN003",
            "beneficiary_name": "Ravi",
            "beneficiary_account": 101,
            "bank_name": "Mock Bank",
            "ifsc_code": "MOCK0000001",
            "status": "ACTIVE",
        }
    ],
}


# ============================================================
# LIST BENEFICIARIES
# ============================================================

@app.get("/accounts/{account_id}/beneficiaries")
def get_beneficiaries(account_id: int):

    if account_id not in accounts:
        raise HTTPException(
            status_code=404,
            detail="Source account not found",
        )

    return {
        "source_account": account_id,
        "total_beneficiaries": len(beneficiaries.get(account_id, [])),
        "beneficiaries": beneficiaries.get(account_id, []),
    }


# ============================================================
# GET A SINGLE BENEFICIARY
# ============================================================

@app.get(
    "/accounts/{account_id}/beneficiaries/{beneficiary_id}"
)
def get_beneficiary(account_id: int, beneficiary_id: str):

    if account_id not in accounts:
        raise HTTPException(
            status_code=404,
            detail="Source account not found",
        )

    beneficiary = next(
        (
            item
            for item in beneficiaries.get(account_id, [])
            if item["beneficiary_id"] == beneficiary_id
        ),
        None,
    )

    if not beneficiary:
        raise HTTPException(
            status_code=404,
            detail="Beneficiary not found",
        )

    return beneficiary


# ============================================================
# REGISTER A BENEFICIARY
# ============================================================

@app.post(
    "/accounts/{account_id}/beneficiaries",
    status_code=201,
)
def add_beneficiary(
    account_id: int,
    request: BeneficiaryRequest,
):

    if account_id not in accounts:
        raise HTTPException(
            status_code=404,
            detail="Source account not found",
        )

    if request.beneficiary_account not in accounts:
        raise HTTPException(
            status_code=404,
            detail="Beneficiary account not found",
        )

    if account_id == request.beneficiary_account:
        raise HTTPException(
            status_code=400,
            detail="Cannot add the same account as a beneficiary",
        )

    account_beneficiaries = beneficiaries.setdefault(
        account_id, []
    )

    # Prevent duplicate beneficiary accounts for this source
    if any(
        item["beneficiary_account"] == request.beneficiary_account
        for item in account_beneficiaries
    ):
        raise HTTPException(
            status_code=409,
            detail="Beneficiary account already registered",
        )

    beneficiary_id = f"BEN{sum(len(v) for v in beneficiaries.values()) + 1:03d}"

    beneficiary = {
        "beneficiary_id": beneficiary_id,
        "beneficiary_name": request.beneficiary_name,
        "beneficiary_account": request.beneficiary_account,
        "bank_name": request.bank_name,
        "ifsc_code": request.ifsc_code,
        "status": "ACTIVE",
    }

    account_beneficiaries.append(beneficiary)

    return {
        "message": "Beneficiary registered successfully",
        "beneficiary": beneficiary,
    }
