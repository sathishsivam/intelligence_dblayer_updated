from fastapi import FastAPI, HTTPException

app = FastAPI(title="Mock Banking API")


accounts = {
    "101": {
        "account_number": "101",
        "balance": 423000,
        "currency": "INR",
    },
    "102": {
        "account_number": "102",
        "balance": 185500,
        "currency": "INR",
    },
}


@app.get("/accounts/{account_number}/balance")
async def get_account_balance(account_number: str):

    account = accounts.get(account_number)

    if not account:
        raise HTTPException(
            status_code=404,
            detail="Account not found",
        )

    return account
