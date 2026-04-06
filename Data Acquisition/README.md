
- **"imu_collector.py"** has everything related to the data acquisition process, including BLE scanning, connecting to the M5StickC, subscribing to the characteristic UUID, receiving JSON packets, parsing the data, and writing it to .csv and .txt files.

- Run this command in the terminal to create a standalone executable for the data acquisition application:

```console
(HAR_ESP32_venv) PS D:\research_project\HAR_ESP32\studio> pyinstaller --onefile --windowed --name "HAR Data Acquisition"
 --icon=data_acq_icon.ico imu_collector.py
```

<img align="left" width="600" height="400" alt="data_acquisition" src="https://github.com/user-attachments/assets/b182c4aa-f533-4abc-bb63-1b013ec0d8b2" />



What this Desktop-Application does (data perspective):

1. Scans for BLE devices and connects to the M5StickC by address.

2. Subscribes to the characteristic UUID and receives JSON packets at 20Hz.

3. Parses each packet and extracts 6-axis IMU data (m/s², rad/s), activity label, timestamps.

4. Writes every packet to a timestamped .csv and .txt file in real time.