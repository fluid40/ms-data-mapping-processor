# Use official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Copy requirements first and install
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the app code
COPY . .

# Expose the port Uvicorn will run on
EXPOSE 3088

ENV APP_HOST=0.0.0.0

# Run the app with Uvicorn
CMD ["python", "-m", "ms_data_mapping_processor.__main__"]
