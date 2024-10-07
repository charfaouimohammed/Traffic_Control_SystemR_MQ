# Traffic Control System

## Overview

A traffic control system that simulates vehicle passages, calculates speeds, issues fines for speeding violations, and notifies vehicle owners via email.

## Components

1. **camera_Simulation (`camera_simulation.py`):** Simulates vehicles passing through entry and exit cameras.
2. **traffic_control_Service (`traffic_control_Service.py`):** Records vehicle entries and exits, calculates speeds.
3. **Collect Fine Service (`collect_fine_service.py`):** Handles fine calculations and notifications.
4. **Vehicle Information Service (`vehicle_info_service.py`):** Provides vehicle owner information.
5. **Configuration (`config.yaml`):** Centralized configuration for all services.

## Setup

### Prerequisites

- Python 3.7+
- MongoDB
- Mailtrap account (for SMTP testing)

### Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/mocharfa/traffic_control_system.git
   cd traffic_control_system
