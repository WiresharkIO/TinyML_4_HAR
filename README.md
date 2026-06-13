
## Overview

This project focuses on classifying human activities using data collected from IMU sensor embedded in the M5-watch [StickC Plus] based on ESP32 SoC, that's the most layman way of putting it forward, but what we try to do precisely is cross dataset (or also called cross device) learning by maintaining a standardized view across the dataset (other platform vs M5-watch IMU) and fine-tuning the learned model to adapt to the M5-watch intricacies.
<p align="center">
      <img width="500" height="500" alt="image" src="https://github.com/user-attachments/assets/ab424573-25b6-45ad-8dc0-066bc712dba5" />
      <!--<img width="500" height="500" alt="Activities" src="https://github.com/user-attachments/assets/368f163e-0d20-4d4e-861f-2c9253e3491a" />--> 
</p>

This is an end-to-end work which involves steps similar to:



<p align="center">
      <img width="900" height="300" alt="pretrain_flow (1)" src="https://github.com/user-attachments/assets/c73981fa-4ec5-45a0-8634-a66c40c60b69" />
</p>


## Dataset

- WISDM - Standardized dataset for wide-patterns.

      This dataset was created by Gary M. Weiss at Fordham University's WISDM (Wireless Sensor Data Mining) Lab and donated to 
      the UCI Machine Learning Repository (2019). It contains raw accelerometer and gyroscope time-series data 
      from both a smartphone and a smartwatch, with the watch component being the LG G Watch running Android Wear 1.5, worn on
      the dominant hand of each subject.
      51 subjects, each performing 18 activities for 3 minutes each, yielding 54 minutes of data per subject.
      
      Non-hand-oriented:
         Walking (A), Jogging (B), Stairs (C), Standing (E), Kicking (M)
      
      Hand-oriented (general):
         Typing (F), Brushing Teeth (G), Dribbling (P), Playing Catch (O), Writing (Q), Clapping (R), Folding Clothes (S)
      
      Hand-oriented (eating):
         Eating Soup (H), Eating Chips (I), Eating Pasta (J), Drinking from Cup (K), Eating Sandwich (L)


- M5-WATCH Stick C Plus based dataset. 

      Activity chosen for this project:
        - Walking
        - Eating 
        - Typing
        - Sedentary (standing and sitting)
        - Writing

## Hardware - ESP32-PICO-D4 Dual-Core Processor

> Constraints

- Flash - 4MB
- SRAM - 520KB
- Frequency - 240MHz
  
> 6-Axis IMU (MPU6886)

<p align="center">
      <img width="400" height="400" alt="image" src="https://github.com/user-attachments/assets/b0de1805-d42e-4e03-b09d-33931e227cc9"/>      
</p>

- Accelerometer - points to be considered for proper $\pm g$ selection :
  
  - The __MPU-6886__ features a 16-bit (-32,768 to +32,767) Analog-to-Digital Converter (ADC) for each axis (X, Y, Z), meaning the sensor has exactly 65,536 total steps to describe the physical acceleration it feels.
  - The __Full Scale Range - FSR__ is the maximum physical linear acceleration the sensor can measure before it "clips" or "saturates" (maxes out). The MPU-6886 has a programmable FSR with four options:
        - ±2g
        - ±4g
        - ±8g (M5StickC Plus default value of 'g' via M5Stack library)
        - ±16g
  
  - Lower g values can help capture incredibly fine, detailed nuances of gentle movements. While higher g values are used to capture movements such as falling and activities like shock.
  - Sensitivity (LSB/g), the scale Factor answers the question - "How many raw steps make up 1g of physical acceleration?" which is given by __Sensitivity = $\frac{32768}{FSR Max}$__.

      Example: For $\pm 8g$ --> Sensitivity (LSB/g) = 4,096 (LSB/g) --> meaning at $\pm 8g$ FSR: 1 step = 1 / 4096 = 0.000244 g (the resolution) !!
  - To convert the raw data into standard SI units compatible with machine learning datasets like WISDM:
    
      Step A: Converting Raw sampled ADC value to g, Acceleration (g) = $\frac{Raw ADC Value}{Sensitivity (LSB/g)}$

      Step B: Converting the g-value to m/s², Acceleration (m/ $s^2$) = Acceleration (g) × 9.81
    
   __"These should be kept in mind while selecting or changing the firmware(library functions) for g values to capture an activity"__
  
- Gyroscope - Instead of measuring linear acceleration (g), the gyroscope measures angular velocity (how fast the device is spinning).
  
  - The __Full Scale Range - FSR__ is the maximum physical angular acceleration the sensor can measure. The MPU-6886 has a programmable FSR with four options:
        - ±250 dps
        - ±500 dps
        - ±1000 dps
        - ±2000 dps (M5StickC Plus default value of dps via M5Stack library)
    
  - The standard physical unit for a gyroscope is Degrees Per Second (dps or °/s) but ususally converted to standard SI unit - Radians Per Second (rad/s) to compatible with machine learning datasets like WISDM:
    
      Step A: Converting raw sampled ADC values to Degrees Per Second (dps), Angular Velocity (dps) = $\frac{Raw ADC Value}{Sensitivity (LSB/dps)}$

      Step B: Converting dps to Radians Per Second (rad/s), Angular Velocity (rad/s) = Angular Velocity (dps) X $\frac{π}{180}$

> Power On / Off

- Power On: Press the reset button for at least 2 seconds
- Power Off: Press the reset button for at least 6 seconds

