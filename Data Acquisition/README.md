

<img width="7968" height="3470" align="left" alt="data_acquisition" src="https://github.com/user-attachments/assets/b182c4aa-f533-4abc-bb63-1b013ec0d8b2" />


What this Desktop-Application does (data perspective):

1. Scans for BLE devices and connects to the M5StickC by address.

2. Subscribes to the characteristic UUID and receives JSON packets at 20Hz.

3. Parses each packet and extracts 6-axis IMU data (m/s², rad/s), activity label, timestamps.

4. Writes every packet to a timestamped .csv and .txt file in real time.