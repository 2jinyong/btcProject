from fastapi import FastAPI
from fastapi.responses import FileResponse

from service.market_analysis import get_market_analysis

app = FastAPI(
    title="BTC Market Analysis"
)

@app.get("/")
def home():
    return FileResponse("views/index.html")

@app.get("/analysis")
def analysis():
    return get_market_analysis()