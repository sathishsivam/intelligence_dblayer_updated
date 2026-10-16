
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import RLock
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


app = FastAPI(
    title="Banking API",
    description="Account details, statements, beneficiaries and fund transfers",
    version="1.0.0",
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development testing only
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Protect in-memory balance updates from concurrent transfers.
bank_lock = RLock()


# ---------------------------------------------------------
# Account data
# ---------------------------------------------------------

class Account:
    def __init__(
        self,
        account_id: int,
        holder_name: str,
        balance: str,
        account_type: str = "SAVINGS",
    ):
        self.account_id = account_id
        self.holder_name = holder_name
        self.balance = Decimal(balance)
        self.account_type = account_type
        self.currency = "INR"
        self.status = "ACTIVE"


accounts = {
    101: Account(101, "Ravi", "50000.00"),
    102: Account(102, "Kumar", "25000.00"),
    103: Account(103, "Suresh", "10000.00"),
    104: Account(104, "Priya", "32500.00"),
    105: Account(105, "Meena", "18750.00"),
    106: Account(106, "Arun", "42000.00"),
    107: Account(107, "Divya", "27600.00"),
    108: Account(108, "Karthik", "51500.00"),
    109: Account(109, "Anitha", "19800.00"),
    110: Account(110, "Vijay", "64000.00"),
    111: Account(111, "Nila", "22300.00"),
}


def money(value: Decimal) -> str:
    """Return a consistent two-decimal monetary value."""
    return str(value.quantize(Decimal("0.01")))


def account_response(account: Account) -> dict:
    return {
        "account_id": account.account_id,
        "account_holder": account.holder_name,
        "account_type": account.account_type,
        "balance": money(account.balance),
        "currency": account.currency,
        "status": account.status,
    }


# ---------------------------------------------------------
# Beneficiary data: 10 beneficiaries for account 101
# ---------------------------------------------------------

beneficiaries = {
    101: [
        {
            "beneficiary_id": f"BEN{i:03d}",
            "beneficiary_name": accounts[account_id].holder_name,
            "beneficiary_account": account_id,
            "bank_name": "Mock Bank",
            "ifsc": f"MOCK000{account_id}",
            "status": "ACTIVE",
        }
        for i, account_id in enumerate(range(102, 112), start=1)
    ]
}


# ---------------------------------------------------------
# Statement data
# ---------------------------------------------------------

# This is an in-memory demonstration. These 10 SAMPLE entries
# are illustrative statement history and do not change balances.
# Successful transfers append LIVE statement entries.
statement_entries = []

sample_balance = Decimal("50000.00")
sample_amounts = [
    Decimal("1000.00"),
    Decimal("1200.00"),
    Decimal("1400.00"),
    Decimal("1600.00"),
    Decimal("1800.00"),
]

for i, amount in enumerate(sample_amounts):
    beneficiary_account = 102 + i

    # Credit entry
    sample_balance += amount
    credit_date = (
        datetime.now(timezone.utc) - timedelta(days=10 - i * 2)
    ).isoformat()

    statement_entries.append({
        "account_id": 101,
        "transaction_id": f"TXNHIST{i * 2 + 1:04d}",
        "transaction_date": credit_date,
        "transaction_type": "CREDIT",
        "description": f"Sample incoming transfer from account {beneficiary_account}",
        "debit": "0.00",
        "credit": money(amount),
        "balance_after": money(sample_balance),
        "status": "SUCCESS",
        "record_type": "SAMPLE",
    })

    # Matching debit entry: the sample sequence nets to zero.
    sample_balance -= amount
    debit_date = (
        datetime.now(timezone.utc) - timedelta(days=9 - i * 2)
    ).isoformat()

    statement_entries.append({
        "account_id": 101,
        "transaction_id": f"TXNHIST{i * 2 + 2:04d}",
        "transaction_date": debit_date,
        "transaction_type": "DEBIT",
        "description": f"Sample payment to account {beneficiary_account}",
        "debit": money(amount),
        "credit": "0.00",
        "balance_after": money(sample_balance),
        "status": "SUCCESS",
        "record_type": "SAMPLE",
    })


# ---------------------------------------------------------
# Request model
# ---------------------------------------------------------

class TransferRequest(BaseModel):
    from_account: int = Field(gt=0)
    to_account: int = Field(gt=0)
    amount: Decimal = Field(
        gt=0,
        max_digits=14,
        decimal_places=2,
    )
    remarks: str = Field(
        default="Fund transfer",
        min_length=1,
        max_length=140,
    )


# ---------------------------------------------------------
# Standard error responses
# ---------------------------------------------------------

@app.exception_handler(HTTPException)
async def banking_http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    if isinstance(exc.detail, dict):
        error = exc.detail
    else:
        error = {
            "error_code": "HTTP_ERROR",
            "description": str(exc.detail),
        }

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "FAILURE",
            **error,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content={
            "status": "FAILURE",
            "error_code": "VALIDATION_ERROR",
            "description": "Invalid request. Check account IDs, amount and required fields.",
            "details": [
                {
                    "field": ".".join(str(part) for part in error["loc"]),
                    "message": error["msg"],
                }
                for error in exc.errors()
            ],
        },
    )


def banking_error(
    status_code: int,
    error_code: str,
    description: str,
):
    raise HTTPException(
        status_code=status_code,
        detail={
            "error_code": error_code,
            "description": description,
        },
    )


# ---------------------------------------------------------
# 1. Health API
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "service": "Mock Banking API",
        "status": "UP",
        "database": "IN_MEMORY",
    }


# ---------------------------------------------------------
# 2. Account details API
# ---------------------------------------------------------

@app.get("/accounts/{account_id}")
def get_account_details(account_id: int):
    with bank_lock:
        account = accounts.get(account_id)

        if account is None:
            banking_error(
                404,
                "ACCOUNT_NOT_FOUND",
                f"Account {account_id} does not exist.",
            )

        return {
            "status": "SUCCESS",
            "data": account_response(account),
        }


# ---------------------------------------------------------
# 3. Account statement API
# ---------------------------------------------------------

@app.get("/accounts/{account_id}/statement")
def get_account_statement(
    account_id: int,
    limit: int = Query(default=10, ge=1, le=10),
):
    with bank_lock:
        account = accounts.get(account_id)

        if account is None:
            banking_error(
                404,
                "ACCOUNT_NOT_FOUND",
                f"Account {account_id} does not exist.",
            )

        # Include sample history for account 101 and live
        # transactions for any account.
        entries = [
            entry
            for entry in statement_entries
            if entry["account_id"] == account_id
        ]

        entries.sort(
            key=lambda entry: entry["transaction_date"],
            reverse=True,
        )

        selected = entries[:limit]

        return {
            "status": "SUCCESS",
            "account_id": account_id,
            "account_holder": account.holder_name,
            "currency": account.currency,
            "record_count": len(selected),
            "transactions": selected,
        }


# ---------------------------------------------------------
# 4. List beneficiaries API
# ---------------------------------------------------------

@app.get("/accounts/{account_id}/beneficiaries")
def get_beneficiaries(account_id: int):
    with bank_lock:
        account = accounts.get(account_id)

        if account is None:
            banking_error(
                404,
                "ACCOUNT_NOT_FOUND",
                f"Account {account_id} does not exist.",
            )

        beneficiary_list = beneficiaries.get(account_id, [])

        return {
            "status": "SUCCESS",
            "account_id": account_id,
            "beneficiary_count": len(beneficiary_list),
            "beneficiaries": beneficiary_list,
        }


# ---------------------------------------------------------
# 5. Fund transfer API
# ---------------------------------------------------------

@app.post("/transfer")
def transfer_funds(request: TransferRequest):
    with bank_lock:
        source = accounts.get(request.from_account)
        destination = accounts.get(request.to_account)

        # Validate accounts
        if source is None:
            banking_error(
                404,
                "SOURCE_ACCOUNT_NOT_FOUND",
                f"Source account {request.from_account} does not exist.",
            )

        if destination is None:
            banking_error(
                404,
                "DESTINATION_ACCOUNT_NOT_FOUND",
                f"Destination account {request.to_account} does not exist.",
            )

        if source.status != "ACTIVE":
            banking_error(
                400,
                "SOURCE_ACCOUNT_INACTIVE",
                "The source account is not active.",
            )

        if destination.status != "ACTIVE":
            banking_error(
                400,
                "DESTINATION_ACCOUNT_INACTIVE",
                "The destination account is not active.",
            )

        if request.from_account == request.to_account:
            banking_error(
                400,
                "SAME_ACCOUNT_TRANSFER",
                "Source and destination accounts must be different.",
            )

        # Require the destination to be a registered beneficiary.
        registered_beneficiaries = beneficiaries.get(
            request.from_account, []
        )

        beneficiary_exists = any(
            item["beneficiary_account"] == request.to_account
            and item["status"] == "ACTIVE"
            for item in registered_beneficiaries
        )

        if not beneficiary_exists:
            banking_error(
                400,
                "BENEFICIARY_NOT_REGISTERED",
                f"Account {request.to_account} is not an active registered beneficiary.",
            )

        if request.amount <= Decimal("0.00"):
            banking_error(
                400,
                "INVALID_AMOUNT",
                "Transfer amount must be greater than zero.",
            )

        # Check sufficient funds before changing either balance.
        if source.balance < request.amount:
            banking_error(
                400,
                "INSUFFICIENT_BALANCE",
                (
                    f"Insufficient balance. Available balance is "
                    f"INR {money(source.balance)}."
                ),
            )

        # Perform the transfer while holding the lock.
        # Neither balance is changed until all checks have passed.
        source.balance -= request.amount
        destination.balance += request.amount

        transaction_id = f"TXN{uuid4().hex[:12].upper()}"
        transaction_date = datetime.now(timezone.utc).isoformat()
        amount_text = money(request.amount)

        # Record a debit entry for the sender.
        statement_entries.append({
            "account_id": source.account_id,
            "transaction_id": transaction_id,
            "transaction_date": transaction_date,
            "transaction_type": "DEBIT",
            "description": request.remarks,
            "debit": amount_text,
            "credit": "0.00",
            "balance_after": money(source.balance),
            "status": "SUCCESS",
            "record_type": "LIVE",
        })

        # Record a credit entry for the recipient.
        statement_entries.append({
            "account_id": destination.account_id,
            "transaction_id": transaction_id,
            "transaction_date": transaction_date,
            "transaction_type": "CREDIT",
            "description": request.remarks,
            "debit": "0.00",
            "credit": amount_text,
            "balance_after": money(destination.balance),
            "status": "SUCCESS",
            "record_type": "LIVE",
        })

        return {
            "status": "SUCCESS",
            "transaction_id": transaction_id,
            "description": "Fund transfer completed successfully.",
            "amount": amount_text,
            "currency": source.currency,
            "from_account": {
                "account_id": source.account_id,
                "account_holder": source.holder_name,
                "new_balance": money(source.balance),
            },
            "to_account": {
                "account_id": destination.account_id,
                "account_holder": destination.holder_name,
                "new_balance": money(destination.balance),
            },
            "transaction_date": transaction_date,
        }
