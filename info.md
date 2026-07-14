<p align="center">
  <img src="https://raw.githubusercontent.com/Lunar0sh/smart_climate/main/images/logo.png" alt="Smart Room Climate Logo" width="300" />
</p>

# Smart Room Climate

An advanced, intelligent climate and ventilation management system for Home Assistant.

## Features

This integration optimizes your indoor climate by intelligently aggregating sensor data and providing actionable insights:

* **Hardware Flexibility:** Works with any indoor temperature sensor. Humidity sensors are automatically integrated into the logic when provided.
* **Virtual Room Aggregation:** Group multiple sensors in one large room into a single virtual sensor (Support for Average, Median, Min, and Max).
* **Smart Ventilation:** Recommends ventilation based on absolute humidity, effectively preventing mold and condensation by ensuring you only bring in drier air.
* **Forecast Curves:** Uses weather forecasts to calculate and display the optimal time window for ventilation (e.g., "Open at 22:00, close at 07:30").
* **PC Heat Warning:** Monitors your gaming PC or workstation and issues a warning if the room temperature approaches a discomfort threshold while the PC is under load.
* **Min/Max Tracking:** Automatically tracks and exposes daily extreme temperatures without the need for manual helpers.

## Installation

1. Ensure you have **HACS** (Home Assistant Community Store) installed.
2. Add this repository as a **Custom Repository** in HACS:
   `https://github.com/Lunar0sh/smart_climate`
3. Search for "Smart Room Climate" and click **Download**.
4. Restart Home Assistant.
5. Go to **Settings > Devices & Services > Add Integration** and search for "Smart Room Climate".

## Configuration

Setup is performed entirely via the Home Assistant UI (Config Flow). You will be guided step-by-step through sensor selection, aggregation method configuration, and PC monitoring setup.

## Support & Feedback

If you encounter issues or have suggestions for improvements, please open an **Issue** in this GitHub repository.

---
*Developed for Home Assistant. Optimized for total control over your room climate.*
