# RailGuard: Autonomous Rail Track Inspection Patrol Agent

Built for the Nebius x NVIDIA Global AI Hackathon (Physical AI track).

RailGuard runs a **sense, detect, verify, act, log** loop on a patrol vehicle:

- **Sense:** camera frame plus odometer
- **Detect:** EfficientNet-B0 classifier, Grad-CAM explanation, feature-distance anomaly check (edge)
- **Verify:** uncertain or conflicting frames go to a vision-language model on a Nebius Serverless Endpoint
- **Act:** stop the motor, sound a buzzer, log the location
- **Scale:** Nebius Serverless Jobs generate synthetic lighting and weather variants and evaluate the stop policy

## Limits

This is a binary defective or non-defective screening model trained on a small dataset. It does not identify fault types and is not a certified safety system.

## Folder structure

```
app/            Streamlit app (app.py, pages/2_Live_Patrol.py)
src/            config, data, inference, LLM client, guideline retrieval, training
edge/           patrol_agent.py (runs on laptop, Raspberry Pi or Jetson)
jobs/           Nebius Serverless Jobs (eval_policy.py, synth_augment.py, Dockerfile)
data/           dataset (not committed if large)
models/         trained weights
reports/        metrics and patrol logs
```

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file (never commit it):

```
NEBIUS_API_KEY=your-key
NEBIUS_MODEL=text-model-id
NEBIUS_MODEL_VLM=vision-model-id
```

## Train

Put the dataset in `data/` with `train/` and `test/` folders, each containing one folder per class (for example `Defective` and `Non defective`).

```bash
python -m src.train --epochs 5
```

Output: `models/efficientnet_b0.pt`, `models/anomaly_stats.npz`, `reports/metrics.json`.

## Run

```bash
# Streamlit app
streamlit run app/app.py

# Patrol agent in simulation
python -m edge.patrol_agent --source data/test --no-cloud

# Patrol agent with the cloud verifier
python -m edge.patrol_agent --source data/test

# Raspberry Pi with buzzer and motor
python -m edge.patrol_agent --source camera --gpio
```

## Nebius jobs

```bash
python -m jobs.synth_augment
python -m jobs.eval_policy 300
```

Build the image with `docker build -f jobs/Dockerfile -t <registry>/railguard-jobs:v1 .`, push it, and submit it as a Serverless Job following the current Nebius docs.

## Live demo

Streamlit link: add your `.streamlit.app` URL here.
