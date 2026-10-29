# DermaSense AI

DermaSense AI is a privacy-first skin-lesion screening-support prototype. It
contains a React web flow for preparing clinician visit notes and a separate,
CPU-oriented PyTorch research pipeline for PAD-UFES-20.

**This is not a diagnostic device.** The web prototype currently has no
trained model connected and does not analyze images, estimate risk, or provide
diagnoses. Do not use it to delay medical care. A clinician should assess skin
concerns.

## Web app

The web app includes consent, structured history intake, a local JPG/PNG
preview, basic image-quality signals, a non-fabricated visit summary, and a
general wellness checklist with local check-off persistence and calendar
export. Images and medical history stay in the open browser session; they are
not uploaded or saved by the app. The checklist alone is saved in local storage.

From the workspace root:

```bash
pnpm --filter @workspace/dermasense-ai run dev
```

## Research pipeline setup

Use Python 3.10 or newer and a CPU-only environment. From this directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m src.data.dataset
```

Download PAD-UFES-20 separately and place its `metadata.csv` and three image
folders as documented in [`data/README.md`](data/README.md). No dataset or
weights are bundled. The dataset verifier checks required columns and image
paths before training begins.

## Train and evaluate

Run from this directory. The default run uses ImageNet-pretrained MobileNetV2,
patient-grouped train/validation/test partitions, train-only clinical-feature
preprocessing, class-weighted loss, CPU training, early stopping on validation
macro-F1, and validation-set temperature scaling:

```bash
python -m src.models.train
```

To measure the image-only ablation, run:

```bash
python -m src.models.train --image-only
```

After both actual runs finish, the project writes
`outputs/ablation-comparison.md` from their measured held-out metrics.

Training writes checkpoints, fitted preprocessing, metrics, and plots beneath
`outputs/`. A resized-image cache and patient-grouped split CSVs are written to
`data/processed/`. These generated files are ignored by Git. Reported numbers
are generated only by an actual run on the local dataset; this repository
intentionally contains no placeholder results. Results from the test partition are patient-disjoint from
training and validation. Review the printed per-class recall, especially for
MEL, BCC, and SCC, and the limits of the dataset before interpreting any
metric.

Optional quick checks:

```bash
python -m pytest
python -m src.models.evaluate --help
```

The research pipeline does not currently serve predictions to the React app.
The browser app continues to state that model inference is unavailable rather
than presenting unvalidated output.

## Explainability, reports, and routine planner

The Python package includes LIME (no Grad-CAM), occlusion sensitivity, image
quality checks, a confidence/quality gate, a PDF report helper, and a
deterministic Safe Corner planner. These modules are research utilities and
are not connected to the current browser workflow. Explanations describe
model behavior, not clinical evidence.

## Evaluation and limitations

No trained weights or evaluation metrics are included. PAD-UFES-20 is a
single-source dataset with class imbalance and limited population and skin-tone
coverage. A patient-grouped test split reduces leakage but does not establish
clinical validity, safety, fairness, or performance in other populations.
Never present a model output as a diagnosis or substitute for professional
care.
