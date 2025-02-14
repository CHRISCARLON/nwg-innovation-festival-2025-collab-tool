# Rapid Street Assessments (RSAs)

## Overview

Rapid Street Assessments (RSAs) are designed to quickly retrieve comprehensive information about streets and the surrounding area.

Example flow for Land Use Query:

![Screenshot 2025-02-14 at 13 37 07](https://github.com/user-attachments/assets/7d05f8f4-cb00-490d-ab88-926bec951c69)

### 1. Routing and Asset Management Information (RAMI) Query

```bash
curl "http://localhost:8080/rami?collection_id=trn-rami-specialdesignationline-1&usrn=8100239"
```

- **Purpose**: Retrieve Routing and Asset Management Information about a specific street - e.g. engineering difficulties/traffic sensitivity.
- **Parameters**:
  - `collection_id`: Identifies the special designation line collection within the RAMI data
  - `usrn`: Unique Street Reference Number - used as a direct filter

### 2. Land Use Query

```bash
curl "http://localhost:8080/land-use?collection_id=lus-fts-site-1&usrn=11720125"
```

- **Purpose**: Retrieve land use information for a specific geographic area - e.g. land for commercial and residential purposes, etc.
- **Parameters**:
  - `collection_id`: Identifies the land use collection within the land use data
  - `usrn`: Unique Street Reference Number - used to calculate bbox

## Key Benefits

- **Fast Retrieval**: Quickly access detailed street and land use information
- **Precise Targeting**: All you need is a USRN
- **Multiple Data Sources**: Access different collections (rami and land use)

## Typical Use Cases

- Urban planning
- Infrastructure assessment
- Land use analysis
- Rapid geographic information retrieval

## Coordinate System Note

The bbox, bbox_crs, and crs query parametres use the British National Grid (EPSG:27700) coordinate system.

## Frontend 

Currently building a basic frontend for this too!

![Screenshot 2025-02-14 at 23 22 13](https://github.com/user-attachments/assets/74a9b63f-c64c-4b77-8e82-8f611146c243)


