# 🔥 Weather Dependent Automation Sensor for Home Assistant

This integration allows you to create a sensor that calculates the required **heating system temperature** based on the **heating curve number** (from 1 to 200) and an **outdoor temperature sensor**. The calculated temperature can be used to control your heating boiler.

## ⚙ Features
- Define **minimum and maximum temperature limits** to match your boiler's supported range.
- Create **multiple independent sensors**, each with its own settings.
- Customize the **heating curve shape** by adjusting the exponent range for more precise control.
- Adjust sensor parameters **at any time** without restarting Home Assistant.

## 📌 Additional Factors (Optional)
The sensor can also consider the following parameters to refine its calculations:
- **Indoor temperature**
- **Wind speed**
- **Outdoor humidity**

---

## 🔢 **How These Parameters Affect the Calculation**

### 🌡 Indoor Temperature Correction
- **Default correction factor:** `2`
- **Adjustable range:** `0 to 10`
- For every **1°C difference** between the desired and actual indoor temperature, the heating system temperature is adjusted by **±2°C**.

### 🌬 Wind Speed Correction
- **Default correction factor:** `0.2`
- **Adjustable range:** `0 to 1`
- For every **5 m/s wind speed**, the heating system temperature is increased by **1°C**.

### 💧 Outdoor Humidity Correction
- **Default correction factor:** `0.05`
- **Adjustable range:** `0 to 0.2`
- For every **10% humidity above 50%**, the heating system temperature is increased by **0.5°C**.

---

## 📌 Example Usage
This sensor can be integrated into **Home Assistant automations** to dynamically adjust the boiler's temperature, ensuring a more **efficient** and **comfortable** heating experience.

🚀 **With this sensor, your heating system will automatically adapt to changing weather conditions!**
