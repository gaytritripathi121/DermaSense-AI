# Local dataset setup

Download PAD-UFES-20 from <https://doi.org/10.17632/zr7vgbcyr2.1> using its
publisher-provided flow. Extract the files so this directory contains:

```text
data/raw/
  metadata.csv
  imgs_part_1/
  imgs_part_2/
  imgs_part_3/
```

Run `python -m src.data.dataset` from the `artifacts/dermasense-ai` directory
to verify the expected files and print the number of usable image rows. The
verifier uses the CSV's `img_id` values to locate images and reports missing
files instead of silently treating them as usable examples.

The dataset is not included in this repository. Keep source images, generated
patient splits, checkpoints, and metrics out of version control. Verify the
dataset license and terms before use.
