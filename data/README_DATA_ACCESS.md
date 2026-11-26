# Data Access and Provenance

Third-party raw data are not redistributed by default.

## PulseBat processed data
Local source during the study: `Data/PulseBat/`.
The primary model used processed U1-U21 pulse-voltage features from:
LFP 35Ah, LMO 10Ah, NMC 2.1Ah, and NMC 21Ah.

Use the dataset citation in the manuscript and respect its original license.

## Second-life LFP23
DOI: https://doi.org/10.5281/zenodo.18630889

## Bipolar709
DOI: https://doi.org/10.5281/zenodo.23634967

170 overlapping raw IDs were excluded before cross-dataset evaluation,
leaving 539 target cells.

`data/provenance/raw_file_inventory_sha256.csv` records local file identity.

Set `INCLUDE_RAW_DATA = True` only after confirming redistribution permission.
