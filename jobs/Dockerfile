FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app
# Job command is set at launch, e.g.: python -m jobs.eval_policy 300
