# Rapid Street Assessments (RSAs)

## Overview
Rapid Street Assessments (RSAs) are designed to quickly retrieve comprehensive information about streets and the surrounding area.

### 1. Routing and Asset Management Information (RAMI) Query
```bash
curl "http://localhost:8080/features?collection_id=trn-rami-specialdesignationline-1&usrn=8100239"
```
- **Purpose**: Retrieve detailed information about a specific street
- **Parameters**:
  - `collection_id`: Identifies the specific feature (in this case, transportation-related special designation lines)
  - `usrn`: Unique Street Reference Number

### 2. Land Use Query
```bash
curl "http://localhost:8080/features?collection_id=lus-fts-site-1&usrn=11720125"
```
- **Purpose**: Retrieve land use information for a specific geographic area
- **Parameters**:
  - `collection_id`: Identifies the land use site feature
  - `usrn`: Unique Street Reference Number

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
The queries use the British National Grid (EPSG:27700) coordinate system, which is standard for UK-based geographic data.
