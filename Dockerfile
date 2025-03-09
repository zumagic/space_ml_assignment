FROM python:3.12-slim-bullseye

# Install dependencies
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
WORKDIR /app/src
COPY ./src ./

CMD ["uvicorn", "features_api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Command to run container: docker run --rm -p 8000:8000 my-fastapi-app