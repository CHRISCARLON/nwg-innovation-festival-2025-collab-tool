# Rapid Street Assessment Tool

## Overview

Rapid Street Assessment (RSAs) are designed to provide quick, comprehensive analysis of street and land use data - using USRNs (Unique Street Reference Numbers).

It consists of a Python backend using Robyn framework and a frontend built with Taipy GUI.

![Screenshot 2025-02-14 at 13 37 07](https://github.com/user-attachments/assets/7d05f8f4-cb00-490d-ab88-926bec951c69)

## Core Features

### 1. Street Information Analysis

- Fetches and analyses street network data and special designations
- Provides detailed information about:
  - Street characteristics
  - Special designations and restrictions
  - Engineering difficulties
  - Traffic sensitivity
  - Street Impact Score
  - Street Manager Aggregated Stats
- Uses GPT-4 to generate human-readable analysis of the technical data

### 2. Land Use Analysis

- Retrieves and processes land use and building data
- Provides insights about:
  - Property types and distributions
  - Land use categories
  - Total area statistics
  - Building characteristics
- Uses GPT-4 to generate human-readable analysis of the technical data

## Technical Architecture

### Frontend (Taipy GUI)

TBC - currently just a basic frontend to test the backend and is out of date.

### Backend (Robyn)

- RESTful API endpoints:
  - `/street-info`: Street network and RAMI data
  - `/land-use-info`: Land use and building information
- Asynchronous processing of multiple OS NGD API calls
- Intelligent data filtering and data aggregation
- Integration with OpenAI's GPT-4 for data interpretation

### Key Dependencies

- Python ≥3.11
- Robyn (API framework)
- Taipy (GUI framework)
- LangChain (AI processing)
- MotherDuck (data storage)

## Data Sources

- Ordnance Survey National Geographic Database (NGD)
- Supports multiple OS data collections:
  - RAMI (Routing and Asset Management Information)
  - Network data
  - Land use data
- Street Manager data from MotherDuck
- Street Impact scores from MotherDuck (created monthly by myself)
