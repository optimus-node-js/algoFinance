import os
import uvicorn
from risk_service.risk_service import app

if __name__ == "__main__":
    port = int(os.getenv("RISK_API_PORT", "8003"))
    host = os.getenv("RISK_API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port, log_level="info")
