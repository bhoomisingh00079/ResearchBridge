from fastapi import FastAPI

app = FastAPI(
    title="ResearchBridge API",
    description="REST API for the Student Research Collaboration Platform",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "ResearchBridge API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }