FROM python:3.12-slim-bullseye

# Set the working directory inside the container
WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
WORKDIR /app/src
COPY ./src ./

EXPOSE 8000

CMD ["uvicorn", "features_api:app", "--reload"]