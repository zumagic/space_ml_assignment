import pandas as pd
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from feature_processor import process_application_features


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello, world!"}


# Pydantic model for input data
class ApplicationData(BaseModel):
    id: float
    application_date: str
    contracts: str


# Endpoint to process application data
@app.post("/process_application")
async def process_application(application_data: ApplicationData):
    """Processes a single application and returns calculated features."""
    try:
        # Create a DataFrame using model_dump
        df = pd.DataFrame([application_data.model_dump()])  # Corrected line

        # Process features
        results_df = process_application_features(df)

        # Convert results to a dictionary
        results_dict = results_df.to_dict(orient='records')[0]

        return results_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing application: {e}")
