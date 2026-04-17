import sys
import asyncio
import json
import csv
import os
import threading
import time
from collections import deque
from datetime import datetime

import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QFileDialog,
    QStatusBar, QFrame, QSplitter, QGroupBox, QProgressBar
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPalette
from bleak import BleakScanner, BleakClient

# ── BLE Configuration ──────────────────────────────────────────────────────
DEVICE_NAME    = "M5StickC_Data_acquisition"
SERVICE_UUID   = "4fe76cf0-8c00-4e81-b3e7-3e12c89106f2"
CHAR_UUID      = "99e68ef6-225d-4ca7-ae62-d90e3df5368e"
SAVE_DIRECTORY = r"D:\research_project\HAR_ESP32\dataset\data_M5stickC"

ACTIVITY_COLORS = {
    "Walking":     "#6daa45",
    "Eating":   "#4f98a3",
    # "stairs_down": "#5591c7",
    "standing":    "#e8af34",
    "sitting":     "#fdab43",
    "typing":      "#a86fdf",
    "unknown":     "#797876",
}

# ── BLE ──────────────────────────────────────────────────────
class BLEWorker(QThread):
    new_packet   = pyqtSignal(dict)
    scan_done    = pyqtSignal(list)
    status_msg   = pyqtSignal(str)
    connected    = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._mode    = None
        self._address = None
        self._paused  = False
        self._running = False
        self._loop    = None

    def start_scan(self):
        self._mode = "scan"
        self.start()

    def start_stream(self, address):
        self._address = address
        self._mode    = "stream"
        self._running = True
        self.start()

    def pause(self):  self._paused = True
    def resume(self): self._paused = False

    def stop(self):
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def run(self):
        self._loop = asyncio.new_event_loop()
        if self._mode == "scan":
            self._loop.run_until_complete(self._do_scan())
        elif self._mode == "stream":
            self._loop.run_until_complete(self._do_stream())

    async def _do_scan(self):
        self.status_msg.emit("Scanning for BLE devices (5s)...")
        try:
            devices = await BleakScanner.discover(timeout=5.0)
            results = [(d.name or "Unknown", d.address) for d in devices]
            self.scan_done.emit(results)
            self.status_msg.emit(f"Scan complete — {len(results)} device(s) found")
        except Exception as e:
            self.status_msg.emit(f"Scan error: {e}")
            self.scan_done.emit([])

    async def _do_stream(self):
        self.status_msg.emit(f"Connecting to {self._address}…")

        try:
            async with BleakClient(self._address) as client:
                self._client = client  # ← store reference
                self.connected.emit(True)
                self.status_msg.emit("Connected — streaming data")

                def _handler(sender, raw):
                    if self._paused:
                        return
                    try:
                        packet = json.loads(raw.decode("utf-8", errors="ignore"))
                        packet.setdefault("received_at", datetime.now().isoformat())
                        self.new_packet.emit(packet)
                    except Exception:
                        pass

                await client.start_notify(CHAR_UUID, _handler)
                while self._running and client.is_connected:
                    await asyncio.sleep(0.05)
                await client.stop_notify(CHAR_UUID)
                await client.disconnect()

        except Exception as e:
            self.status_msg.emit(f"BLE error: {e}")
        finally:
            self._client = None
            self.connected.emit(False)


# ── Main Window ────────────────────────────────────────────────────────────
class IMUCollector(QMainWindow):
    PLOT_WINDOW = 200   # rolling samples

    def __init__(self):
        super().__init__()
        self.setWindowTitle("M5StickC IMU Data")
        self.resize(1280, 820)

        self.ble_worker  = None
        self.device_map  = {}
        self.is_connected = False
        self.is_paused   = False
        self.is_saving   = False

        self.csv_file    = None
        self.txt_file    = None
        self.csv_writer  = None
        self.sample_count = 0
        self.session_count = 0

        # Rolling buffers
        keys = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z"]
        self.bufs = {k: deque([0.0] * self.PLOT_WINDOW, maxlen=self.PLOT_WINDOW)
                     for k in keys}
        self.current_activity = "unknown"

        self._build_ui()
        self._apply_dark_theme()

    # ── UI Construction ────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # Left panel
        left = QVBoxLayout()
        left.setSpacing(8)

        # ── Connection group ──
        conn_group = QGroupBox("BLE Connection")
        conn_layout = QVBoxLayout(conn_group)

        self.btn_scan = QPushButton("⟳  Scan Devices")
        self.btn_scan.setFixedHeight(36)
        self.btn_scan.clicked.connect(self.do_scan)
        conn_layout.addWidget(self.btn_scan)

        self.device_list = QListWidget()
        self.device_list.setFixedHeight(140)
        self.device_list.setAlternatingRowColors(True)
        conn_layout.addWidget(self.device_list)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setFixedHeight(36)
        self.btn_connect.setEnabled(False)
        self.btn_connect.clicked.connect(self.toggle_connect)
        conn_layout.addWidget(self.btn_connect)

        self.device_list.itemSelectionChanged.connect(
            lambda: self.btn_connect.setEnabled(bool(self.device_list.currentItem()) and not self.is_connected)
        )
        left.addWidget(conn_group)

        # ── Session group ──
        sess_group = QGroupBox("Session Control")
        sess_layout = QVBoxLayout(sess_group)

        self.btn_pause = QPushButton("⏸  Pause")
        self.btn_pause.setFixedHeight(36)
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self.toggle_pause)
        sess_layout.addWidget(self.btn_pause)

        self.btn_reset = QPushButton("↺  Reset Counter")
        self.btn_reset.setFixedHeight(36)
        self.btn_reset.setEnabled(False)
        self.btn_reset.clicked.connect(self.do_reset)
        sess_layout.addWidget(self.btn_reset)

        self.btn_save = QPushButton("💾  Start Saving")
        self.btn_save.setFixedHeight(36)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.toggle_save)
        sess_layout.addWidget(self.btn_save)

        left.addWidget(sess_group)

        # ── Stats group ──
        stats_group = QGroupBox("Live Stats")
        stats_layout = QVBoxLayout(stats_group)

        self.lbl_samples   = QLabel("Samples:  0")
        self.lbl_activity  = QLabel("Activity:  —")
        self.lbl_gravity   = QLabel("Gravity:   — m/s²")
        self.lbl_saved     = QLabel("Saved:     0 files")
        for lbl in [self.lbl_samples, self.lbl_activity, self.lbl_gravity, self.lbl_saved]:
            lbl.setFont(QFont("Courier New", 10))
            stats_layout.addWidget(lbl)

        self.activity_badge = QLabel("—")
        self.activity_badge.setAlignment(Qt.AlignCenter)
        self.activity_badge.setFixedHeight(32)
        self.activity_badge.setStyleSheet(
            "border-radius: 6px; background: #393836; color: #cdccca; font-weight: bold; font-size: 13px;"
        )
        stats_layout.addWidget(self.activity_badge)
        left.addWidget(stats_group)

        left.addStretch()

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setFixedWidth(240)
        root.addWidget(left_widget)

        # Right panel — plots
        right = QVBoxLayout()
        right.setSpacing(6)

        pg.setConfigOption("background", "#1c1b19")
        pg.setConfigOption("foreground", "#cdccca")

        # Accel plot
        self.accel_plot = pg.PlotWidget(title="Accelerometer  (m/s²)")
        self.accel_plot.showGrid(x=True, y=True, alpha=0.25)
        self.accel_plot.addLegend(offset=(10, 10))

        # Gyro plot
        self.gyro_plot = pg.PlotWidget(title="Gyroscope  (rad/s)")
        self.gyro_plot.showGrid(x=True, y=True, alpha=0.25)
        self.gyro_plot.addLegend(offset=(10, 10))

        accel_colors = {"acc_x": "#e8af34", "acc_y": "#4f98a3", "acc_z": "#a86fdf"}
        gyro_colors  = {"gyro_x": "#6daa45", "gyro_y": "#dd6974", "gyro_z": "#fdab43"}

        x = list(range(self.PLOT_WINDOW))
        self.curves = {}
        for key, color in accel_colors.items():
            self.curves[key] = self.accel_plot.plot(
                x, list(self.bufs[key]),
                pen=pg.mkPen(color=color, width=1.8),
                name=key.replace("acc_", "").upper()
            )
        for key, color in gyro_colors.items():
            self.curves[key] = self.gyro_plot.plot(
                x, list(self.bufs[key]),
                pen=pg.mkPen(color=color, width=1.8),
                name=key.replace("gyro_", "").upper()
            )

        right.addWidget(self.accel_plot, 1)
        right.addWidget(self.gyro_plot,  1)

        right_widget = QWidget()
        right_widget.setLayout(right)
        root.addWidget(right_widget, 1)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready — scan for devices to begin")

    # ── Dark theme ─────────────────────────────────────────────────────────
    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #171614;
                color: #cdccca;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #393836;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 6px;
                font-weight: 600;
                color: #cdccca;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
            }
            QPushButton {
                background-color: #2d2c2a;
                border: 1px solid #393836;
                border-radius: 5px;
                padding: 4px 12px;
                color: #cdccca;
                font-size: 13px;
            }
            QPushButton:hover  { background-color: #393836; }
            QPushButton:pressed { background-color: #4f98a3; color: #1c1b19; }
            QPushButton:disabled { color: #5a5957; border-color: #262523; }
            QPushButton#primary {
                background-color: #01696f;
                color: #f9f8f5;
                border-color: #01696f;
                font-weight: 600;
            }
            QPushButton#primary:hover  { background-color: #0c4e54; }
            QPushButton#danger {
                background-color: #a13544;
                color: #f9f8f5;
                border-color: #a13544;
                font-weight: 600;
            }
            QPushButton#danger:hover { background-color: #782b33; }
            QListWidget {
                background-color: #1c1b19;
                border: 1px solid #393836;
                border-radius: 5px;
                color: #cdccca;
                alternate-background-color: #201f1d;
            }
            QListWidget::item:selected { background-color: #313b3b; color: #4f98a3; }
            QStatusBar { background-color: #1c1b19; color: #797876; font-size: 12px; }
            QLabel { color: #cdccca; }
        """)

    # ── BLE Scan ───────────────────────────────────────────────────────────
    def do_scan(self):
        self.device_list.clear()
        self.device_map.clear()
        self.btn_scan.setEnabled(False)
        self.btn_connect.setEnabled(False)

        worker = BLEWorker()
        worker.scan_done.connect(self._on_scan_done)
        worker.status_msg.connect(self.status_bar.showMessage)
        worker.start_scan()
        self._scan_worker = worker   # keep reference

    def _on_scan_done(self, devices):
        self.btn_scan.setEnabled(True)
        for name, addr in devices:
            label = f"{name}  [{addr}]"
            item  = QListWidgetItem(label)

            # Highlight M5StickC if found
            if DEVICE_NAME in name:
                item.setForeground(QColor("#4f98a3"))
                item.setFont(QFont("Segoe UI", 11, QFont.Bold))
            self.device_list.addItem(item)
            self.device_map[label] = addr

        if not devices:
            self.device_list.addItem("No devices found — try again")

    # ── Connect / Disconnect ───────────────────────────────────────────────
    def toggle_connect(self):
        if not self.is_connected:
            item = self.device_list.currentItem()
            if not item or item.text() not in self.device_map:
                self.status_bar.showMessage("Select a device from the list first")
                return
            addr = self.device_map[item.text()]

            self.ble_worker = BLEWorker()
            self.ble_worker.new_packet.connect(self.on_packet)
            self.ble_worker.status_msg.connect(self.status_bar.showMessage)
            self.ble_worker.connected.connect(self._on_connection_change)
            self.ble_worker.start_stream(addr)
        else:
            if self.ble_worker:
                self.ble_worker.stop()
            if self.is_saving:
                self.toggle_save()

    def _on_connection_change(self, connected):
        self.is_connected = connected
        if connected:
            self.btn_connect.setText("Disconnect")
            self.btn_connect.setObjectName("danger")
            self.btn_pause.setEnabled(True)
            self.btn_reset.setEnabled(True)
            self.btn_save.setEnabled(True)
            self.btn_scan.setEnabled(False)
        else:
            self.btn_connect.setText("Connect")
            self.btn_connect.setObjectName("")
            self.btn_pause.setEnabled(False)
            self.btn_reset.setEnabled(False)
            self.btn_save.setEnabled(False)
            self.btn_scan.setEnabled(True)
            self.btn_connect.setEnabled(bool(self.device_list.currentItem()))
            self.status_bar.showMessage("Disconnected")
        self.btn_connect.setStyle(self.btn_connect.style())  # refresh stylesheet

    # ── Pause / Resume ─────────────────────────────────────────────────────
    def toggle_pause(self):
        if not self.is_paused:
            if self.ble_worker:
                self.ble_worker.pause()
            self.btn_pause.setText("▶  Resume")
            self.is_paused = True
            self.status_bar.showMessage("Paused — plot and saving frozen")
        else:
            if self.ble_worker:
                self.ble_worker.resume()
            self.btn_pause.setText("⏸  Pause")
            self.is_paused = False
            self.status_bar.showMessage("Resumed")

    def do_reset(self):
        self.sample_count = 0
        for key in self.bufs:
            self.bufs[key] = deque([0.0] * self.PLOT_WINDOW, maxlen=self.PLOT_WINDOW)
        self.lbl_samples.setText("Samples:  0")
        self.lbl_activity.setText("Activity:  —")
        self.lbl_gravity.setText("Gravity:   — m/s²")
        self.activity_badge.setText("—")
        self.activity_badge.setStyleSheet(
            "border-radius: 6px; background: #393836; color: #cdccca; font-weight: bold; font-size: 13px;"
        )
        self.status_bar.showMessage("Counter reset to 0")

    # ── Save ───────────────────────────────────────────────────────────────
    def toggle_save(self):
        if not self.is_saving:
            # Use default save dir; fallback to file dialog if it doesn't exist
            save_dir = SAVE_DIRECTORY if os.path.isdir(SAVE_DIRECTORY) else None
            if not save_dir:
                save_dir = QFileDialog.getExistingDirectory(self, "Choose save folder")
            if not save_dir:
                return

            ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = os.path.join(save_dir, f"m5stick_{ts}.csv")
            txt_path = os.path.join(save_dir, f"m5stick_{ts}.txt")

            self.csv_file   = open(csv_path, "w", newline="", encoding="utf-8")
            self.txt_file   = open(txt_path, "w", encoding="utf-8")
            self.csv_writer = csv.writer(self.csv_file)

            header = ["timestamp", "activity", "sample_id",
                      "acc_x", "acc_y", "acc_z",  # m/s²
                      "gyro_x", "gyro_y", "gyro_z",  # rad/s
                      "acc_x_raw", "acc_y_raw", "acc_z_raw",  # g-force
                      "gyro_x_raw", "gyro_y_raw", "gyro_z_raw",  # deg/s
                      "gravity_mag", "received_at"]
            self.csv_writer.writerow(header)
            self.txt_file.write(",".join(header) + "\n")

            self.is_saving = True
            self.session_count += 1
            self.lbl_saved.setText(f"Saved:     {self.session_count} file(s)")
            self.btn_save.setText("⏹  Stop Saving")
            self.btn_save.setObjectName("danger")
            self.btn_save.setStyle(self.btn_save.style())
            self.status_bar.showMessage(f"Saving → {csv_path}")

        else:
            self._close_files()
            self.is_saving = False
            self.btn_save.setText("💾  Start Saving")
            self.btn_save.setObjectName("")
            self.btn_save.setStyle(self.btn_save.style())
            self.status_bar.showMessage("Saving stopped")

    def _close_files(self):
        if self.csv_file:
            self.csv_file.flush()
            self.csv_file.close()
            self.csv_file = None
        if self.txt_file:
            self.txt_file.flush()
            self.txt_file.close()
            self.txt_file = None
        self.csv_writer = None

    # ── Incoming Packet ────────────────────────────────────────────────────
    def on_packet(self, packet):
        # Extract fields safely
        acc_x  = float(packet.get("acc_x",  0))
        acc_y  = float(packet.get("acc_y",  0))
        acc_z  = float(packet.get("acc_z",  0))
        gyro_x = float(packet.get("gyro_x", 0))
        gyro_y = float(packet.get("gyro_y", 0))
        gyro_z = float(packet.get("gyro_z", 0))

        acc_x_raw = float(packet.get("acc_x_raw", 0))
        acc_y_raw = float(packet.get("acc_y_raw", 0))
        acc_z_raw = float(packet.get("acc_z_raw", 0))
        gyro_x_raw = float(packet.get("gyro_x_raw", 0))
        gyro_y_raw = float(packet.get("gyro_y_raw", 0))
        gyro_z_raw = float(packet.get("gyro_z_raw", 0))


        activity   = packet.get("activity",   "unknown")
        gravity    = float(packet.get("gravity_mag", 0))
        sample_id  = int(packet.get("sample_id", self.sample_count))
        timestamp  = packet.get("timestamp", 0)
        received   = packet.get("received_at", "")

        # Update buffers
        for key, val in zip(
            ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z"],
            [acc_x,   acc_y,   acc_z,   gyro_x,   gyro_y,   gyro_z]
        ):
            self.bufs[key].append(val)

        # Refresh plots
        x = list(range(self.PLOT_WINDOW))
        for key in self.bufs:
            self.curves[key].setData(x, list(self.bufs[key]))

        # Update stats
        self.sample_count += 1
        self.current_activity = activity
        self.lbl_samples.setText(f"Samples:  {self.sample_count:,}")
        self.lbl_activity.setText(f"Activity:  {activity}")
        self.lbl_gravity.setText(f"Gravity:   {gravity:.2f} m/s²")

        # Activity badge colour
        color = ACTIVITY_COLORS.get(activity, "#797876")
        self.activity_badge.setText(activity.replace("_", " ").title())
        self.activity_badge.setStyleSheet(
            f"border-radius: 6px; background: {color}33; "
            f"color: {color}; font-weight: bold; font-size: 13px; "
            f"border: 1px solid {color}66;"
        )

        # Write to files
        if self.is_saving and self.csv_writer:
            row = [timestamp, activity, sample_id,
                   acc_x, acc_y, acc_z,
                   gyro_x, gyro_y, gyro_z,
                   acc_x_raw, acc_y_raw, acc_z_raw,  # ← added
                   gyro_x_raw, gyro_y_raw, gyro_z_raw,  # ← added
                   gravity, received]
            self.csv_writer.writerow(row)
            self.csv_file.flush()
            self.txt_file.write(",".join(map(str, row)) + "\n")
            self.txt_file.flush()

    # ── Cleanup ────────────────────────────────────────────────────────────
    def closeEvent(self, event):
        if self.ble_worker:
            self.ble_worker.stop()
            self.ble_worker.wait(2000)
        self._close_files()
        event.accept()


# ── Trigger Point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = IMUCollector()
    window.show()
    sys.exit(app.exec_())
