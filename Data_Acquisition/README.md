--------------------------------------------------------------------------------------------------------------------------------
1. *imu_collector.py* has everything related to the data acquisition process, including BLE scanning, connecting to the M5StickC, subscribing to the characteristic UUID, receiving JSON packets, parsing the data, and writing it to .csv and .txt files.

    But before running this, the firmware side of the data acquisition should be in place. Meaning the M5StickC must be flashed with firmware (using Arduino IDE in this project).


--------------------------------------------------------------------------------------------------------------------------------

2. Run this command in the terminal to create a standalone executable for the data acquisition application:

```console
(HAR_ESP32_venv) PS D:\research_project\HAR_ESP32\studio> pyinstaller --onefile --windowed --name "HAR Data Acquisition"
 --icon=data_acq_icon.ico imu_collector.py
```

   Output of this will be application file with the name "HAR Data Acquisition.exe" in the "dist" folder. You can run this executable (or run [Notebook4Data](/Data_Acquisition/01_data_acquisition.ipynb)) to start the data acquisition process. The application will create .csv and .txt files with the collected IMU data. <img width="30" height="30" alt="image" src="https://github.com/user-attachments/assets/cc45387d-9c0a-45e1-88aa-46c15328c386" />
  

<!-- <img width="30" height="30" alt="image" src="https://github.com/user-attachments/assets/cc45387d-9c0a-45e1-88aa-46c15328c386" /> -->

<!--<p align="center">
  <img width="600" height="400" alt="data_acquisition" src="https://github.com/user-attachments/assets/b182c4aa-f533-4abc-bb63-1b013ec0d8b2"/>
</p>-->


--------------------------------------------------------------------------------------------------------------------------------

3. What this Desktop-Application does (data perspective):
   
   3.1. Scans for BLE devices and connects to the M5StickC by address.
   
   3.2. Subscribes to the characteristic UUID and receives JSON packets at 20Hz.
   
   3.3. Parses each packet and extracts 6-axis IMU data (m/s², rad/s), activity label, timestamps.
   
   3.4. Writes every packet to a timestamped .csv and .txt file in real time.
   

--------------------------------------------------------------------------------------------------------------------------------
