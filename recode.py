from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtCore import QFileSystemWatcher, QCoreApplication, QThread, Signal
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from qt_material import apply_stylesheet
import threading
import pymem
import pymem.process
import win32api
import win32con
import win32gui
import subprocess
from pynput.mouse import Controller, Button
import json
import os
import sys
import time
import shutil

CONFIG_DIR = os.path.join(os.environ['LOCALAPPDATA'], 'temp', 'althea')
CONFIGS_DIR = os.path.join(CONFIG_DIR, 'configs')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
DEFAULT_SETTINGS = {
    "esp_rendering": 1,
    "esp_mode": 1,
    "line_rendering": 1,
    "hp_bar_rendering": 1,
    "head_hitbox_rendering": 1,
    "bons": 1,
    "nickname": 1,
    "radius": 50,
    "delay_shot": 0,
    "keyboard": "V",
    "aim_active": 0,
    "aim_mode": 1,
    "aim_mode_distance": 1,
    "trigger_bot_active": 0,
    "keyboards": "X", 
    "weapon": 1,
    "bomb_esp": 1,
    "anti_flash": 0,
    "bhop": 0,
    "fov": 90
}
BombPlantedTime = 0
BombDefusedTime = 0

def load_settings(config_file=CONFIG_FILE):
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if not os.path.exists(CONFIGS_DIR):
        os.makedirs(CONFIGS_DIR)

    if not os.path.exists(config_file):
        with open(config_file, "w") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=4)
        return DEFAULT_SETTINGS.copy()
    
    try:
        with open(config_file, "r") as f:
            content = f.read().strip()
            if not content:
                with open(config_file, "w") as f:
                    json.dump(DEFAULT_SETTINGS, f, indent=4)
                return DEFAULT_SETTINGS.copy()
            
            settings = json.loads(content)
            return settings
    except (json.JSONDecodeError, UnicodeDecodeError):
        with open(config_file, "w") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=4)
        return DEFAULT_SETTINGS.copy()
    
def get_config_list():
    if not os.path.exists(CONFIGS_DIR):
        os.makedirs(CONFIGS_DIR)
        return []
    
    configs = []
    for file in os.listdir(CONFIGS_DIR):
        if file.endswith('.json'):
            configs.append(file[:-5])
    
    return configs

def save_config(name):
    if not os.path.exists(CONFIGS_DIR):
        os.makedirs(CONFIGS_DIR)
    
    config_path = os.path.join(CONFIGS_DIR, f"{name}.json")
    with open(config_path, "w") as f:
        json.dump(load_settings(), f, indent=4)
    
    return config_path

def load_config(name):
    config_path = os.path.join(CONFIGS_DIR, f"{name}.json")
    if os.path.exists(config_path):
        shutil.copyfile(config_path, CONFIG_FILE)
        return True
    return False

def delete_config(name):
    config_path = os.path.join(CONFIGS_DIR, f"{name}.json")
    if os.path.exists(config_path):
        os.remove(config_path)
        return True
    return False

def save_settings(settings):
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings, f, indent=4)

def get_offsets_and_client_dll():
    offsets = 1
    client_dll = 1
    return offsets, client_dll

def get_window_size(window_title):
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd:
        rect = win32gui.GetClientRect(hwnd)
        return rect[2], rect[3]
    return None, None

def w2s(mtx, posx, posy, posz, width, height):
    screenW = (mtx[12] * posx) + (mtx[13] * posy) + (mtx[14] * posz) + mtx[15]
    if screenW > 0.001:
        screenX = (mtx[0] * posx) + (mtx[1] * posy) + (mtx[2] * posz) + mtx[3]
        screenY = (mtx[4] * posx) + (mtx[5] * posy) + (mtx[6] * posz) + mtx[7]
        camX = width / 2
        camY = height / 2
        x = camX + (camX * screenX / screenW)
        y = camY - (camY * screenY / screenW)
        return [int(x), int(y)]
    return [-999, -999]

class ModernCheckBox(QtWidgets.QCheckBox):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 12px;
                spacing: 8px;
                background-color: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #ffffff;
                border-radius: 4px;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #666666;
                border-color: #ffffff;
                image: none;
            }
            QCheckBox::indicator:checked:hover {
                border-color: #cccccc;
                background-color: #888888;
            }
            QCheckBox::indicator:hover {
                border-color: #cccccc;
            }
        """)
        
class ModernComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setStyleSheet("""
            QComboBox {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333333;
                padding: 4px 8px;
                font-size: 12px;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: #666666;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                width: 20px;
                border-left: 1px solid #333333;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a1a;
                color: #ffffff;
                selection-background-color: #333333;
                border: 1px solid #333333;
            }
        """)

class ModernLineEdit(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333333;
                padding: 4px 8px;
                font-size: 12px;
                selection-background-color: #333333;
            }
            QLineEdit:hover {
                border-color: #666666;
            }
            QLineEdit:focus {
                border-color: #999999;
            }
        """)

class ModernSlider(QtWidgets.QSlider):
    def __init__(self, orientation=QtCore.Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #333333;
                height: 4px;
            }
            QSlider::sub-page:horizontal {
                background: #ffffff;
                height: 4px;
            }
            QSlider::add-page:horizontal {
                background: #666666;
                height: 4px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 1px solid #333333;
                width: 12px;
                margin: -4px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #f0f0f0;
            }
        """)

class TabButton(QtWidgets.QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setFixedHeight(35)
        self.setStyleSheet("""
            QPushButton {
                background-color: #0a0a0a;
                color: #999999;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
                border-bottom: 2px solid transparent;
            }
            QPushButton:hover {
                background-color: #1a1a1a;
                color: #cccccc;
            }
            QPushButton:checked {
                background-color: #000000;
                color: #ffffff;
                border-bottom: 2px solid #ffffff;
            }
        """)

class ConfigWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('althea | external')
        self.settings = load_settings()
        self.initUI()
        self.is_dragging = False
        self.drag_start_position = None
        self.setStyleSheet("background-color: #000000;")

    def initUI(self):
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setFixedSize(800, 550)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header = QtWidgets.QWidget()
        header.setFixedHeight(35)
        header.setStyleSheet("background-color: #0a0a0a; border-bottom: 1px solid #333333;")
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(15, 0, 10, 0)

        title_label = QtWidgets.QLabel("althea | external")
        title_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")

        close_btn = QtWidgets.QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #ffffff;
                border: none;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        close_btn.clicked.connect(self.close)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)

        tab_widget = QtWidgets.QWidget()
        tab_widget.setFixedHeight(40)
        tab_widget.setStyleSheet("background-color: 0a0a0a; border-bottom: 1px solid #333333;")
        self.tab_layout = QtWidgets.QHBoxLayout(tab_widget)
        self.tab_layout.setContentsMargins(10, 5, 10, 5)
        self.tab_layout.setSpacing(0)

        self.visual_tab = TabButton("VISUAL")
        self.aim_tab = TabButton("AIM")
        self.trigger_tab = TabButton("TRIGGER")
        self.misc_tab = TabButton("MISC")
        self.configs_tab = TabButton("CONFIGS")

        self.visual_tab.setChecked(True)

        self.tab_layout.addWidget(self.visual_tab)
        self.tab_layout.addWidget(self.aim_tab)
        self.tab_layout.addWidget(self.trigger_tab)
        self.tab_layout.addWidget(self.misc_tab)
        self.tab_layout.addWidget(self.configs_tab)
        self.tab_layout.addStretch()

        self.stacked_widget = QtWidgets.QStackedWidget()
        self.stacked_widget.setStyleSheet("""
            QStackedWidget {
                background-color: #000000;
                border: none;
            }
        """)

        self.visual_content = self.create_visual_tab()
        self.aim_content = self.create_aim_tab()
        self.trigger_content = self.create_trigger_tab()
        self.misc_content = self.create_misc_tab()
        self.configs_content = self.create_configs_tab()

        self.stacked_widget.addWidget(self.visual_content)
        self.stacked_widget.addWidget(self.aim_content)
        self.stacked_widget.addWidget(self.trigger_content)
        self.stacked_widget.addWidget(self.misc_content)
        self.stacked_widget.addWidget(self.configs_content)

        self.visual_tab.clicked.connect(lambda: self.switch_tab(0))
        self.aim_tab.clicked.connect(lambda: self.switch_tab(1))
        self.trigger_tab.clicked.connect(lambda: self.switch_tab(2))
        self.misc_tab.clicked.connect(lambda: self.switch_tab(3))
        self.configs_tab.clicked.connect(lambda: self.switch_tab(4))

        main_layout.addWidget(header)
        main_layout.addWidget(tab_widget)
        main_layout.addWidget(self.stacked_widget)

        self.setLayout(main_layout)

    def switch_tab(self, index):
        self.stacked_widget.setCurrentIndex(index)
        self.visual_tab.setChecked(index == 0)
        self.aim_tab.setChecked(index == 1)
        self.trigger_tab.setChecked(index == 2)
        self.misc_tab.setChecked(index == 3)
        self.configs_tab.setChecked(index == 4)
        
        if index == 4:
            self.refresh_config_list()

    def create_visual_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        esp_group = QtWidgets.QGroupBox("ESP SETTINGS")
        esp_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #333333;
                margin-top: 5px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
        """)
        esp_layout = QtWidgets.QVBoxLayout(esp_group)
        esp_layout.setSpacing(8)

        self.esp_rendering_cb = ModernCheckBox("ESP Enable")
        self.esp_rendering_cb.setChecked(self.settings["esp_rendering"] == 1)
        self.esp_rendering_cb.stateChanged.connect(self.save_settings)
        esp_layout.addWidget(self.esp_rendering_cb)

        mode_layout = QtWidgets.QHBoxLayout()
        mode_layout.addWidget(QtWidgets.QLabel("ESP Mode:"))
        self.esp_mode_cb = ModernComboBox()
        self.esp_mode_cb.addItems(["Enemies Only", "All Players"])
        self.esp_mode_cb.setCurrentIndex(self.settings["esp_mode"])
        self.esp_mode_cb.currentIndexChanged.connect(self.save_settings)
        mode_layout.addWidget(self.esp_mode_cb)
        mode_layout.addStretch()
        esp_layout.addLayout(mode_layout)

        features_group = QtWidgets.QGroupBox("Visuals")
        features_group.setStyleSheet(esp_group.styleSheet())
        features_layout = QtWidgets.QVBoxLayout(features_group)
        features_layout.setSpacing(8)

        self.line_rendering_cb = ModernCheckBox("ESP Lines")
        self.line_rendering_cb.setChecked(self.settings["line_rendering"] == 1)
        self.line_rendering_cb.stateChanged.connect(self.save_settings)
        features_layout.addWidget(self.line_rendering_cb)

        self.hp_bar_rendering_cb = ModernCheckBox("ESP Bars")
        self.hp_bar_rendering_cb.setChecked(self.settings["hp_bar_rendering"] == 1)
        self.hp_bar_rendering_cb.stateChanged.connect(self.save_settings)
        features_layout.addWidget(self.hp_bar_rendering_cb)

        self.head_hitbox_rendering_cb = ModernCheckBox("ESP Head")
        self.head_hitbox_rendering_cb.setChecked(self.settings["head_hitbox_rendering"] == 1)
        self.head_hitbox_rendering_cb.stateChanged.connect(self.save_settings)
        features_layout.addWidget(self.head_hitbox_rendering_cb)

        self.bons_cb = ModernCheckBox("ESP Bones")
        self.bons_cb.setChecked(self.settings["bons"] == 1)
        self.bons_cb.stateChanged.connect(self.save_settings)
        features_layout.addWidget(self.bons_cb)

        self.nickname_cb = ModernCheckBox("ESP Name")
        self.nickname_cb.setChecked(self.settings["nickname"] == 1)
        self.nickname_cb.stateChanged.connect(self.save_settings)
        features_layout.addWidget(self.nickname_cb)

        self.weapon_cb = ModernCheckBox("ESP Weapon")
        self.weapon_cb.setChecked(self.settings["weapon"] == 1)
        self.weapon_cb.stateChanged.connect(self.save_settings)
        features_layout.addWidget(self.weapon_cb)

        self.bomb_esp_cb = ModernCheckBox("ESP Bomb")
        self.bomb_esp_cb.setChecked(self.settings["bomb_esp"] == 1)
        self.bomb_esp_cb.stateChanged.connect(self.save_settings)
        features_layout.addWidget(self.bomb_esp_cb)

        layout.addWidget(esp_group)
        layout.addWidget(features_group)
        layout.addStretch()

        return widget

    def create_aim_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        aim_group = QtWidgets.QGroupBox("Aim")
        aim_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #333333;
                margin-top: 5px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
        """)
        aim_layout = QtWidgets.QVBoxLayout(aim_group)
        aim_layout.setSpacing(8)

        self.aim_active_cb = ModernCheckBox("Enable Aim")
        self.aim_active_cb.setChecked(self.settings["aim_active"] == 1)
        self.aim_active_cb.stateChanged.connect(self.save_settings)
        aim_layout.addWidget(self.aim_active_cb)

        aim_layout.addWidget(QtWidgets.QLabel("Aim Radius:"))
        radius_layout = QtWidgets.QHBoxLayout()
        self.radius_slider = ModernSlider(QtCore.Qt.Horizontal)
        self.radius_slider.setMinimum(0)
        self.radius_slider.setMaximum(100)
        self.radius_slider.setValue(self.settings["radius"])
        self.radius_slider.valueChanged.connect(self.save_settings)
        
        self.radius_label = QtWidgets.QLabel(f"{self.settings['radius']}")
        self.radius_label.setStyleSheet("color: #ffffff; min-width: 30px; font-size: 11px;")
        self.radius_slider.valueChanged.connect(lambda v: self.radius_label.setText(f"{v}%"))
        
        radius_layout.addWidget(self.radius_slider)
        radius_layout.addWidget(self.radius_label)
        aim_layout.addLayout(radius_layout)

        aim_layout.addWidget(QtWidgets.QLabel("Aim Key:"))
        self.keyboard_input = ModernLineEdit()
        self.keyboard_input.setText(self.settings["keyboard"])
        self.keyboard_input.textChanged.connect(self.save_settings)
        aim_layout.addWidget(self.keyboard_input)

        mode_layout = QtWidgets.QHBoxLayout()
        mode_layout.addWidget(QtWidgets.QLabel("Aim Mode:"))
        self.aim_mode_cb = ModernComboBox()
        self.aim_mode_cb.addItems(["Body", "Head"])
        self.aim_mode_cb.setCurrentIndex(self.settings["aim_mode"])
        self.aim_mode_cb.currentIndexChanged.connect(self.save_settings)
        mode_layout.addWidget(self.aim_mode_cb)
        mode_layout.addStretch()
        aim_layout.addLayout(mode_layout)

        target_layout = QtWidgets.QHBoxLayout()
        target_layout.addWidget(QtWidgets.QLabel("Target Selection:"))
        self.aim_mode_distance_cb = ModernComboBox()
        self.aim_mode_distance_cb.addItems(["Closest to Crosshair", "Closest in 3D"])
        self.aim_mode_distance_cb.setCurrentIndex(self.settings["aim_mode_distance"])
        self.aim_mode_distance_cb.currentIndexChanged.connect(self.save_settings)
        target_layout.addWidget(self.aim_mode_distance_cb)
        target_layout.addStretch()
        aim_layout.addLayout(target_layout)

        layout.addWidget(aim_group)
        layout.addStretch()

        return widget

    def create_trigger_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        trigger_group = QtWidgets.QGroupBox("Trigger Bot")
        trigger_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #333333;
                margin-top: 5px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
        """)
        trigger_layout = QtWidgets.QVBoxLayout(trigger_group)
        trigger_layout.setSpacing(8)

        self.trigger_bot_active_cb = ModernCheckBox("Trigger Bot")
        self.trigger_bot_active_cb.setChecked(self.settings["trigger_bot_active"] == 1)
        self.trigger_bot_active_cb.stateChanged.connect(self.save_settings)
        trigger_layout.addWidget(self.trigger_bot_active_cb)

        trigger_layout.addWidget(QtWidgets.QLabel("Delay Shot"))
        delay_layout = QtWidgets.QHBoxLayout()
        self.delay_slider = ModernSlider(QtCore.Qt.Horizontal)
        self.delay_slider.setMinimum(0)
        self.delay_slider.setMaximum(100)
        self.delay_slider.setValue(self.settings["delay_shot"])
        self.delay_slider.valueChanged.connect(self.save_settings)
        
        self.delay_label = QtWidgets.QLabel(f"{self.settings['delay_shot']}")
        self.delay_label.setStyleSheet("color: #ffffff; min-width: 30px; font-size: 11px;")
        self.delay_slider.valueChanged.connect(lambda v: self.delay_label.setText(f"{v} ms"))
        
        delay_layout.addWidget(self.delay_slider)
        delay_layout.addWidget(self.delay_label)
        trigger_layout.addLayout(delay_layout)

        trigger_layout.addWidget(QtWidgets.QLabel("Trigger Key:"))
        self.trigger_key_input = ModernLineEdit()
        self.trigger_key_input.setText(self.settings["keyboards"])
        self.trigger_key_input.textChanged.connect(self.save_settings)
        trigger_layout.addWidget(self.trigger_key_input)

        layout.addWidget(trigger_group)
        layout.addStretch()

        return widget

    def create_misc_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        misc_group = QtWidgets.QGroupBox("Misc")
        misc_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #333333;
                margin-top: 5px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
        """)
        misc_layout = QtWidgets.QVBoxLayout(misc_group)
        misc_layout.setSpacing(8)

        self.anti_flash_cb = ModernCheckBox("Anti Flash")
        self.anti_flash_cb.setChecked(self.settings["anti_flash"] == 1)
        self.anti_flash_cb.stateChanged.connect(self.save_settings)
        misc_layout.addWidget(self.anti_flash_cb)

        self.bhop_cb = ModernCheckBox("Bunny Hop")
        self.bhop_cb.setChecked(self.settings["bhop"] == 1)
        self.bhop_cb.stateChanged.connect(self.save_settings)
        misc_layout.addWidget(self.bhop_cb)

        misc_layout.addWidget(QtWidgets.QLabel("FOV:"))
        fov_layout = QtWidgets.QHBoxLayout()
        self.fov_slider = ModernSlider(QtCore.Qt.Horizontal)
        self.fov_slider.setMinimum(50)
        self.fov_slider.setMaximum(180)
        self.fov_slider.setValue(self.settings["fov"])
        self.fov_slider.valueChanged.connect(self.save_settings)
        
        self.fov_label = QtWidgets.QLabel(f"{self.settings['fov']}")
        self.fov_label.setStyleSheet("color: #ffffff; min-width: 30px; font-size: 11px;")
        self.fov_slider.valueChanged.connect(lambda v: self.fov_label.setText(f"{v}%"))

        layout.addWidget(misc_group)
        fov_layout.addWidget(self.fov_slider)
        fov_layout.addWidget(self.fov_label)
        misc_layout.addLayout(fov_layout)
        layout.addStretch()

        return widget
    
    def create_configs_tab(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        configs_group = QtWidgets.QGroupBox("Config")
        configs_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #333333;
                margin-top: 5px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #ffffff;
            }
        """)
        configs_layout = QtWidgets.QVBoxLayout(configs_group)

        name_layout = QtWidgets.QHBoxLayout()
        name_layout.addWidget(QtWidgets.QLabel("Config Name:"))
        self.config_name_input = ModernLineEdit()
        name_layout.addWidget(self.config_name_input)
        configs_layout.addLayout(name_layout)

        buttons_layout = QtWidgets.QHBoxLayout()

        self.save_config_btn = QtWidgets.QPushButton()
        self.save_config_btn.setIcon(QtGui.QIcon("C:\\althea\\assets\\icons\\save.png"))
        self.save_config_btn.setIconSize(QtCore.QSize(16, 16))
        self.save_config_btn.setFixedSize(32, 32)
        self.save_config_btn.setToolTip("Save current config")
        self.save_config_btn.clicked.connect(self.save_current_config)
        self.save_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
                border-color: #666666;
            }
            QPushButton:disabled {
                background-color: #0a0a0a;
                border-color: #222222;
            }
        """)

        self.load_config_btn = QtWidgets.QPushButton()
        self.load_config_btn.setIcon(QtGui.QIcon("C:\\althea\\assets\\icons\\load.png"))
        self.load_config_btn.setIconSize(QtCore.QSize(16, 16))
        self.load_config_btn.setFixedSize(32, 32)
        self.load_config_btn.setToolTip("Load selected config")
        self.load_config_btn.clicked.connect(self.load_selected_config)
        self.load_config_btn.setStyleSheet(self.save_config_btn.styleSheet())

        self.delete_config_btn = QtWidgets.QPushButton()
        self.delete_config_btn.setIcon(QtGui.QIcon("C:\\althea\\assets\\icons\\delete.png"))
        self.delete_config_btn.setIconSize(QtCore.QSize(16, 16))
        self.delete_config_btn.setFixedSize(32, 32)
        self.delete_config_btn.setToolTip("Delete selected config")
        self.delete_config_btn.clicked.connect(self.delete_selected_config)
        self.delete_config_btn.setStyleSheet(self.save_config_btn.styleSheet())
        
        buttons_layout.addWidget(self.save_config_btn)
        buttons_layout.addWidget(self.load_config_btn)
        buttons_layout.addWidget(self.delete_config_btn)
        buttons_layout.addStretch()
        
        configs_layout.addLayout(buttons_layout)

        configs_layout.addWidget(QtWidgets.QLabel("Saved Configs:"))
        self.config_list = QtWidgets.QListWidget()
        self.config_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333333;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:selected {
                background-color: #333333;
            }
        """)
        configs_layout.addWidget(self.config_list)
        
        layout.addWidget(configs_group)
        layout.addStretch()

        self.config_list.itemSelectionChanged.connect(self.update_config_buttons_state)

        return widget
    
    def switch_tab(self, index):
        self.stacked_widget.setCurrentIndex(index)
        self.visual_tab.setChecked(index == 0)
        self.aim_tab.setChecked(index == 1)
        self.trigger_tab.setChecked(index == 2)
        self.misc_tab.setChecked(index == 3)
        self.configs_tab.setChecked(index == 4)

        if index == 4:
            self.refresh_config_list()

    def update_config_buttons_state(self):
        has_selection = len(self.config_list.selectedItems()) > 0
        self.load_config_btn.setEnabled(has_selection)
        self.delete_config_btn.setEnabled(has_selection)

    def refresh_config_list(self):
        self.config_list.clear()
        configs = get_config_list()
        for config in configs:
            self.config_list.addItem(config)

    def save_current_config(self):
        config_name = self.config_name_input.text().strip()
        if not config_name:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please enter a config name")
            return

        self.save_settings()
        
        save_config(config_name)
        self.refresh_config_list()
        self.config_name_input.clear()


    def load_selected_config(self):
        selected_items = self.config_list.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a config to load")
            return
        
        config_name = selected_items[0].text()
        if load_config(config_name):
            self.settings = load_settings()
            self.update_ui_from_settings()

    def delete_selected_config(self):
        selected_items = self.config_list.selectedItems()
        if not selected_items:
            return
        
        config_name = selected_items[0].text()
        reply = 1
        
        if reply == 1:
            if delete_config(config_name):
                self.refresh_config_list()

    def update_ui_from_settings(self):
        self.esp_rendering_cb.setChecked(self.settings["esp_rendering"] == 1)
        self.esp_mode_cb.setCurrentIndex(self.settings["esp_mode"])
        self.line_rendering_cb.setChecked(self.settings["line_rendering"] == 1)
        self.hp_bar_rendering_cb.setChecked(self.settings["hp_bar_rendering"] == 1)
        self.head_hitbox_rendering_cb.setChecked(self.settings["head_hitbox_rendering"] == 1)
        self.bons_cb.setChecked(self.settings["bons"] == 1)
        self.nickname_cb.setChecked(self.settings["nickname"] == 1)
        self.weapon_cb.setChecked(self.settings["weapon"] == 1)
        self.bomb_esp_cb.setChecked(self.settings["bomb_esp"] == 1)
        self.anti_flash_cb.setChecked(self.settings["anti_flash"] == 1)
        self.bhop_cb.setChecked(self.settings["bhop"] == 1)
        self.aim_active_cb.setChecked(self.settings["aim_active"] == 1)
        self.radius_slider.setValue(self.settings["radius"])
        self.delay_slider.setValue(self.settings["delay_shot"])
        self.fov_slider.setValue(self.settings["fov"])
        self.keyboard_input.setText(self.settings["keyboard"])
        self.aim_mode_cb.setCurrentIndex(self.settings["aim_mode"])
        self.aim_mode_distance_cb.setCurrentIndex(self.settings["aim_mode_distance"])
        self.trigger_bot_active_cb.setChecked(self.settings["trigger_bot_active"] == 1)
        self.trigger_key_input.setText(self.settings["keyboards"])

    def save_settings(self):
        try:
            self.settings["esp_rendering"] = 1 if self.esp_rendering_cb.isChecked() else 0
            self.settings["esp_mode"] = self.esp_mode_cb.currentIndex()
            self.settings["line_rendering"] = 1 if self.line_rendering_cb.isChecked() else 0
            self.settings["hp_bar_rendering"] = 1 if self.hp_bar_rendering_cb.isChecked() else 0
            self.settings["head_hitbox_rendering"] = 1 if self.head_hitbox_rendering_cb.isChecked() else 0
            self.settings["bons"] = 1 if self.bons_cb.isChecked() else 0
            self.settings["nickname"] = 1 if self.nickname_cb.isChecked() else 0
            self.settings["weapon"] = 1 if self.weapon_cb.isChecked() else 0
            self.settings["bomb_esp"] = 1 if self.bomb_esp_cb.isChecked() else 0
            self.settings["anti_flash"] = 1 if self.anti_flash_cb.isChecked() else 0
            self.settings["bhop"] = 1 if self.bhop_cb.isChecked() else 0
            self.settings["aim_active"] = 1 if self.aim_active_cb.isChecked() else 0
            self.settings["radius"] = self.radius_slider.value()
            self.settings["delay_shot"] = self.delay_slider.value()
            self.settings["fov"] = self.fov_slider.value()
            self.settings["keyboard"] = self.keyboard_input.text()
            self.settings["aim_mode"] = self.aim_mode_cb.currentIndex()
            self.settings["aim_mode_distance"] = self.aim_mode_distance_cb.currentIndex()
            self.settings["trigger_bot_active"] = 1 if self.trigger_bot_active_cb.isChecked() else 0
            self.settings["keyboards"] = self.trigger_key_input.text()
            
            save_settings(self.settings)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self.is_dragging = True
            self.drag_start_position = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.is_dragging:
            delta = event.globalPosition().toPoint() - self.drag_start_position
            self.move(self.pos() + delta)
            self.drag_start_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self.is_dragging = False

class WorkerThread(QThread):
    update_signal = Signal()
    
    def __init__(self, function, settings):
        super().__init__()
        self.function = function
        self.settings = settings
        self.running = True
        
    def run(self):
        while self.running:
            try:
                self.function(self.settings)
                time.sleep(0.01)
            except Exception as e:
                print(f"Error in worker thread: {e}")
                time.sleep(1)
                
    def stop(self):
        self.running = False

def configurator():
    app = QtWidgets.QApplication(sys.argv)
    apply_stylesheet(app, theme='altea.xml')
    window = ConfigWindow()
    window.show()
    sys.exit(app.exec())

class ESPWindow(QtWidgets.QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle('Overlay (DONT CLOSE IT!!!)')
        self.window_width, self.window_height = get_window_size("Counter-Strike 2")
        if self.window_width is None or self.window_height is None:
            print("Ошибка: окно игры не найдено.")
            sys.exit(1)
        self.setGeometry(0, 0, self.window_width, self.window_height)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        hwnd = self.winId()
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)

        self.file_watcher = QFileSystemWatcher([CONFIG_FILE])
        self.file_watcher.fileChanged.connect(self.reload_settings)

        self.offsets, self.client_dll = get_offsets_and_client_dll()
        self.pm = pymem.Pymem("cs2.exe")
        self.client = pymem.process.module_from_name(self.pm.process_handle, "client.dll").lpBaseOfDll

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setGeometry(0, 0, self.window_width, self.window_height)
        self.view.setRenderHint(QtGui.QPainter.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.view.setStyleSheet("background: transparent;")
        self.view.setSceneRect(0, 0, self.window_width, self.window_height)
        self.view.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_scene)
        self.timer.start(0)

        self.last_time = time.time()
        self.frame_count = 0
        self.fps = 60

    def reload_settings(self):
        try:
            self.settings = load_settings()
            self.window_width, self.window_height = get_window_size("Counter-Strike 2")
            if self.window_width is None or self.window_height is None:
                print("Error: game window not found.")
                return
            
            self.setGeometry(0, 0, self.window_width, self.window_height)
            self.update_scene()
        except Exception as e:
            print(f"Error reloading settings: {e}")


    def update_scene(self):
        if not self.is_game_window_active():
            self.scene.clear()
            return

        self.scene.clear()
        try:
            esp(self.scene, self.pm, self.client, self.offsets, self.client_dll, self.window_width, self.window_height, self.settings)

            
            current_time = time.time()
            self.frame_count += 1
            if current_time - self.last_time >= 1.0:
                self.fps = self.frame_count
                self.frame_count = 0
                self.last_time = current_time
            font_path = "C:\\althea\\assets\\fonts\\Roboto.ttf"
            watermark_render = self.scene.addText(f"althea | t.me/dylib_developer", QtGui.QFont(font_path, 10, QtGui.QFont.Bold))
            watermark_render.setPos(self.window_width - 210, 5)
            watermark_render.setDefaultTextColor(QtGui.QColor(255, 255, 255))

        except Exception as e:
            print(f"Scene Update Error: {e}")
            QtWidgets.QApplication.quit()
    
    def is_game_window_active(self):
        hwnd = win32gui.FindWindow(None, "Counter-Strike 2")
        if hwnd:
            foreground_hwnd = win32gui.GetForegroundWindow()
            return hwnd == foreground_hwnd
        return False

class MainApplication:
    def __init__(self):
        self.settings = load_settings()
        self.threads = []
        self.running = True
        
    def start_esp(self):
        try:
            app = QtWidgets.QApplication(sys.argv)
            window = ESPWindow(self.settings)
            window.show()
            app.exec()
        except Exception as e:
            print(f"ESP error: {e}")

    def open_configurator(self):
        try:
            subprocess.Popen([sys.executable, __file__, "--config"])
        except Exception as e:
            print(f"Failed to open configurator: {e}")


    def start_triggerbot(self):
        dwEntityList = 30495944
        dwLocalPlayerPawn = 29299872
        m_iTeamNum = 1003
        m_iIDEntIndex = 5680
        m_iHealth = 844
        m_vecVelocity = 1072
        m_pClippingWeapon = 15936
        m_AttributeManager = 5024
        m_Item = 80
        m_iItemDefinitionIndex = 442
        mouse = Controller()

        def load_settings_internal():
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r') as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    pass
            return DEFAULT_SETTINGS

        def is_moving(player):
            try:
                velocity_x = pm.read_float(player + m_vecVelocity)
                velocity_y = pm.read_float(player + m_vecVelocity + 0x4)
                velocity_z = pm.read_float(player + m_vecVelocity + 0x8)
                speed = (velocity_x**2 + velocity_y**2 + velocity_z**2)**0.5
                return speed > 5.0
            except:
                return False

        def stop_movement():
            win32api.keybd_event(0x53, 0, 0, 0)
            time.sleep(0.01)
            win32api.keybd_event(0x53, 0, win32con.KEYEVENTF_KEYUP, 0)

        def get_weapon_index(player):
            try:
                weapon_pointer = pm.read_longlong(player + m_pClippingWeapon)
                weapon_index = pm.read_int(weapon_pointer + m_AttributeManager + m_Item + m_iItemDefinitionIndex)
                return weapon_index
            except:
                return -1

        def is_revolver(weapon_index):
            return weapon_index == 262208

        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        while self.running:
            try:
                current_settings = load_settings_internal()
                trigger_bot_active = current_settings["trigger_bot_active"]
                attack_all = current_settings["esp_mode"]
                keyboards = current_settings["keyboards"]
                delay_shot = current_settings["delay_shot"]
                
                if win32api.GetAsyncKeyState(ord(keyboards)):
                    if trigger_bot_active == 1:
                        try:
                            player = pm.read_longlong(client + dwLocalPlayerPawn)
                            entityId = pm.read_int(player + m_iIDEntIndex)
                            
                            if entityId > 0:
                                entList = pm.read_longlong(client + dwEntityList)
                                entEntry = pm.read_longlong(entList + 0x8 * (entityId >> 9) + 0x10)
                                entity = pm.read_longlong(entEntry + 120 * (entityId & 0x1FF))
                                entityTeam = pm.read_int(entity + m_iTeamNum)
                                playerTeam = pm.read_int(player + m_iTeamNum)
                                
                                if (attack_all == 1) or (entityTeam != playerTeam and attack_all == 0):
                                    entityHp = pm.read_int(entity + m_iHealth)
                                    
                                    if entityHp > 0:
                                        current_weapon_index = get_weapon_index(player)
                                        is_revolver_equipped = is_revolver(current_weapon_index)
                                        
                                        if is_revolver_equipped:
                                            mouse.press(Button.left)
                                            time.sleep(0.4)
                                            mouse.release(Button.left)
                                        else:
                                            mouse.press(Button.left)
                                            mouse.release(Button.left)
                                        
                                            time.sleep(delay_shot/100)

                        except Exception as e:
                            pass
                    time.sleep(0.03)
                else:
                    time.sleep(0.1)
            except Exception as e:
                time.sleep(1)

    def start_aim(self):
        def get_window_size_internal(window_name="Counter-Strike 2"):
            hwnd = win32gui.FindWindow(None, window_name)
            if hwnd:
                rect = win32gui.GetClientRect(hwnd)
                return rect[2] - rect[0], rect[3] - rect[1]
            return 1920, 1080

        def load_settings_internal():
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r') as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    pass
            return DEFAULT_SETTINGS

        def esp_internal(pm, client, window_size, target_list):
            width, height = window_size
            dwEntityList = 30495944
            dwLocalPlayerPawn = 29299872
            dwViewMatrix = 31664176
            m_iTeamNum = 1003
            m_lifeState = 848
            m_pGameSceneNode = 816
            m_modelState = 400
            m_hPlayerPawn = 2300
            
            current_settings = load_settings_internal()
            if current_settings['aim_active'] == 0:
                return target_list
                
            view_matrix = [pm.read_float(client + dwViewMatrix + i * 4) for i in range(16)]
            local_player_pawn_addr = pm.read_longlong(client + dwLocalPlayerPawn)
            
            try:
                local_player_team = pm.read_int(local_player_pawn_addr + m_iTeamNum)
            except:
                return target_list
                
            entity_list = pm.read_longlong(client + dwEntityList)
            entity_ptr = pm.read_longlong(entity_list + 0x10)

            for i in range(1, 64):
                try:
                    if entity_ptr == 0:
                        break

                    entity_controller = pm.read_longlong(entity_ptr + 0x78 * (i & 0x1FF))
                    if entity_controller == 0:
                        continue

                    entity_controller_pawn = pm.read_longlong(entity_controller + m_hPlayerPawn)
                    if entity_controller_pawn == 0:
                        continue

                    entity_list_pawn = pm.read_longlong(entity_list + 0x8 * ((entity_controller_pawn & 0x7FFF) >> 0x9) + 0x10)
                    if entity_list_pawn == 0:
                        continue

                    entity_pawn_addr = pm.read_longlong(entity_list_pawn + 0x78 * (entity_controller_pawn & 0x1FF))
                    if entity_pawn_addr == 0 or entity_pawn_addr == local_player_pawn_addr:
                        continue

                    entity_team = pm.read_int(entity_pawn_addr + m_iTeamNum)
                    if entity_team == local_player_team and current_settings['esp_mode'] == 0:
                        continue

                    entity_alive = pm.read_int(entity_pawn_addr + m_lifeState)
                    if entity_alive != 256:
                        continue
                        
                    game_scene = pm.read_longlong(entity_pawn_addr + m_pGameSceneNode)
                    bone_matrix = pm.read_longlong(game_scene + m_modelState + 0x80)
                    
                    try:
                        bone_id = 6 if current_settings['aim_mode'] == 1 else 4
                        headX = pm.read_float(bone_matrix + bone_id * 0x20)
                        headY = pm.read_float(bone_matrix + bone_id * 0x20 + 0x4)
                        headZ = pm.read_float(bone_matrix + bone_id * 0x20 + 0x8)
                        head_pos = w2s(view_matrix, headX, headY, headZ, width, height)
                        
                        if head_pos[0] != -999 and head_pos[1] != -999:
                            if current_settings['aim_mode_distance'] == 1:
                                legZ = pm.read_float(bone_matrix + 28 * 0x20 + 0x8)
                                leg_pos = w2s(view_matrix, headX, headY, legZ, width, height)
                                deltaZ = abs(head_pos[1] - leg_pos[1])
                                target_list.append({
                                    'pos': head_pos,
                                    'deltaZ': deltaZ
                                })
                            else:
                                target_list.append({
                                    'pos': head_pos,
                                    'deltaZ': None
                                })
                    except:
                        pass
                except:
                    continue
            return target_list

        def aimbot_internal(target_list, radius, aim_mode_distance):
            if not target_list:
                return
                
            center_x = win32api.GetSystemMetrics(0) // 2
            center_y = win32api.GetSystemMetrics(1) // 2

            if radius == 0:
                closest_target = None
                closest_dist = float('inf')
                for target in target_list:
                    dist = ((target['pos'][0] - center_x) ** 2 + (target['pos'][1] - center_y) ** 2) ** 0.5
                    if dist < closest_dist:
                        closest_target = target['pos']
                        closest_dist = dist
            else:
                screen_radius = radius / 100.0 * min(center_x, center_y)
                closest_target = None
                closest_dist = float('inf')
                
                if aim_mode_distance == 1:
                    target_with_max_deltaZ = None
                    max_deltaZ = -float('inf')
                    for target in target_list:
                        dist = ((target['pos'][0] - center_x) ** 2 + (target['pos'][1] - center_y) ** 2) ** 0.5
                        if dist < screen_radius and target['deltaZ'] > max_deltaZ:
                            max_deltaZ = target['deltaZ']
                            target_with_max_deltaZ = target
                    closest_target = target_with_max_deltaZ['pos'] if target_with_max_deltaZ else None
                else:
                    for target in target_list:
                        dist = ((target['pos'][0] - center_x) ** 2 + (target['pos'][1] - center_y) ** 2) ** 0.5
                        if dist < screen_radius and dist < closest_dist:
                            closest_target = target['pos']
                            closest_dist = dist
                            
            if closest_target:
                target_x, target_y = closest_target
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(target_x - center_x), int(target_y - center_y), 0, 0)

        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        window_size = get_window_size_internal()
        
        while self.running:
            try:
                current_settings = load_settings_internal()
                target_list = []
                target_list = esp_internal(pm, client, window_size, target_list)
                
                if win32api.GetAsyncKeyState(ord(current_settings['keyboard'])):
                    aimbot_internal(target_list, current_settings['radius'], current_settings['aim_mode_distance'])
                    
                time.sleep(0.005)
            except Exception as e:
                time.sleep(0.1)

    def start_misc(self):
        def load_settings_internal():
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r') as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    pass
            return DEFAULT_SETTINGS

        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        
        while self.running:
            try:
                current_settings = load_settings_internal()

                if current_settings.get("anti_flash", 0) == 1:
                    dwLocalPlayerPawn = 29299872
                    player = pm.read_longlong(client + dwLocalPlayerPawn)
                    pm.write_int(player + 5660, 0)

                if current_settings.get('fov', 90) > 0:
                    dwLocalPlayerController = 31582104
                    controller = pm.read_longlong(client + dwLocalPlayerController)
                    pm.write_int(controller + 1916, current_settings.get('fov', 90))

                if current_settings.get('bhop', 0) == 1:
                    dwLocalPlayerPawn = 29299872
                    m_fFlags = 1016
                    local_player_pawn_addr = pm.read_longlong(client + dwLocalPlayerPawn)
                    
                    if win32api.GetAsyncKeyState(win32con.VK_SPACE):
                        try:
                            PlayerMoveFlag = pm.read_int(local_player_pawn_addr + m_fFlags)
                            if (PlayerMoveFlag == 65665 or PlayerMoveFlag == 65667):
                                hwnd = win32gui.FindWindow(None, 'Counter-Strike 2')
                                win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_SPACE, 0)
                                time.sleep(0.001)
                                win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_SPACE, 0)
                        except:
                            pass
                
                time.sleep(0.01)
            except Exception as e:
                time.sleep(0.1)

    def hotkey_checker(self):
        while self.running:
            if win32api.GetAsyncKeyState(win32con.VK_INSERT):  # F12
                self.open_configurator()
                time.sleep(1)
            time.sleep(0.1)

    def run(self):
        non_qt_functions = [
            self.start_triggerbot,
            self.start_aim,
            self.start_misc
        ]
        
        for func in non_qt_functions:
            thread = threading.Thread(target=func, daemon=True)
            thread.start()
            self.threads.append(thread)

        hotkey_thread = threading.Thread(target=self.hotkey_checker, daemon=True)
        hotkey_thread.start()
        self.threads.append(hotkey_thread)

        self.start_esp()

        self.running = False
        for thread in self.threads:
            thread.join(timeout=1)

def esp(scene, pm, client, offsets, client_dll, window_width, window_height, settings):
    if settings['esp_rendering'] == 0:
        return 

    dwEntityList = 30495944
    dwLocalPlayerPawn = 29299872
    dwViewMatrix = 31664176
    dwPlantedC4 = 31685392
    m_iTeamNum = 1003
    m_lifeState = 848
    m_pGameSceneNode = 816
    m_modelState = 400
    m_hPlayerPawn = 2300
    m_iHealth = 844
    m_iszPlayerName = 1768
    m_pClippingWeapon = 15936
    m_AttributeManager = 5024
    m_Item = 80
    m_iItemDefinitionIndex = 442
    m_AarmorValue = 10156
    m_vecAbsOrigin = 208
    m_flTimerLength = 4520
    m_flDefuseLength = 4540
    m_bBeingDefused = 4524

    view_matrix = [pm.read_float(client + dwViewMatrix + i * 4) for i in range(16)]

    local_player_pawn_addr = pm.read_longlong(client + dwLocalPlayerPawn)
    try:
        time.sleep(0.000001)
        local_player_team = pm.read_int(local_player_pawn_addr + m_iTeamNum)
        
    except:
        return

    no_center_x = window_width / 2
    no_center_y = window_height
    entity_list = pm.read_longlong(client + dwEntityList)
    entity_ptr = pm.read_longlong(entity_list + 0x10)

    def bombisplant():
        global BombPlantedTime
        bombisplant = pm.read_bool(client + dwPlantedC4 - 0x8)
        if bombisplant:
            if (BombPlantedTime == 0):
                BombPlantedTime = time.time()
        else:
            BombPlantedTime = 0
        return bombisplant
    
    def getC4BaseClass():
        plantedc4 = pm.read_longlong(client + dwPlantedC4)
        plantedc4class = pm.read_longlong(plantedc4)
        return plantedc4class
    
    def getPositionWTS():
        c4node = pm.read_longlong(getC4BaseClass() + m_pGameSceneNode)
        c4posX = pm.read_float(c4node + m_vecAbsOrigin)
        c4posY = pm.read_float(c4node + m_vecAbsOrigin + 0x4)
        c4posZ = pm.read_float(c4node + m_vecAbsOrigin + 0x8)
        bomb_pos = w2s(view_matrix, c4posX, c4posY, c4posZ, window_width, window_height)
        return bomb_pos
    
    def getBombTime():
        BombTime = pm.read_float(getC4BaseClass() + m_flTimerLength) - (time.time() - BombPlantedTime)
        return BombTime if (BombTime >= 0) else 0
    
    def isBeingDefused():
        global BombDefusedTime
        BombIsDefused = pm.read_bool(getC4BaseClass() + m_bBeingDefused)
        if (BombIsDefused):
            if (BombDefusedTime == 0):
                BombDefusedTime = time.time() 
        else:
            BombDefusedTime = 0
        return BombIsDefused
    
    def getDefuseTime():
        DefuseTime = pm.read_float(getC4BaseClass() + m_flDefuseLength) - (time.time() - BombDefusedTime)
        return DefuseTime if (isBeingDefused() and DefuseTime >= 0) else 0
    
    font_path = "C:\\althea\\assets\\fonts\\Roboto.ttf"
    bfont = QtGui.QFont(font_path, 7, QtGui.QFont.Bold)

    if settings.get('bomb_esp', 0) == 1:
        if bombisplant():
            BombPosition = getPositionWTS()
            BombTime = getBombTime()
            DefuseTime = getDefuseTime()
        
            if (BombPosition[0] > 0 and BombPosition[1] > 0):
                if DefuseTime > 0:
                    c4_name_text = scene.addText(f'BOMB {round(BombTime, 2)} | DIF {round(DefuseTime, 2)}', bfont)
                else:
                    c4_name_text = scene.addText(f'BOMB {round(BombTime, 2)}', bfont)
                c4_name_x = BombPosition[0]
                c4_name_y = BombPosition[1]
                c4_name_text.setPos(c4_name_x, c4_name_y)
                c4_name_text.setDefaultTextColor(QtGui.QColor(255, 255, 255))
            c4_render_time = scene.addText(f"C4 Time: {round(BombTime, 2)}", QtGui.QFont(font_path, 11, QtGui.QFont.Bold))
            c4_render_defuse_time = scene.addText(f"Defuse time: {round(DefuseTime, 2)}", QtGui.QFont(font_path, 11, QtGui.QFont.Bold))
            c4_render_rect = scene.addRect(1, 1, 200, 65, QtGui.QColor(0, 0, 0,))
            c4_render_time.setPos(window_width/2 - 60, window_height/5)
            c4_render_defuse_time.setPos(window_width/2 - 60, window_height/5 + 20)
            c4_render_rect.setPos(window_width/2 - 100, window_height/5)
            c4_render_time.setDefaultTextColor(QtGui.QColor(255, 255, 255))
            c4_render_defuse_time.setDefaultTextColor(QtGui.QColor(255, 255, 255))

    for i in range(1, 64):
        try:
            if entity_ptr == 0:
                break

            entity_controller = pm.read_longlong(entity_ptr + 0x78 * (i & 0x1FF))
            if entity_controller == 0:
                continue

            entity_controller_pawn = pm.read_longlong(entity_controller + m_hPlayerPawn)
            if entity_controller_pawn == 0:
                continue

            entity_list_pawn = pm.read_longlong(entity_list + 0x8 * ((entity_controller_pawn & 0x7FFF) >> 0x9) + 0x10)
            if entity_list_pawn == 0:
                continue

            entity_pawn_addr = pm.read_longlong(entity_list_pawn + 0x78 * (entity_controller_pawn & 0x1FF))
            if entity_pawn_addr == 0 or entity_pawn_addr == local_player_pawn_addr:
                continue

            entity_team = pm.read_int(entity_pawn_addr + m_iTeamNum)
            if entity_team == local_player_team and settings['esp_mode'] == 0:
                continue

            entity_hp = pm.read_int(entity_pawn_addr + m_iHealth)
            armor_hp = pm.read_int(entity_pawn_addr + m_AarmorValue)
            if entity_hp <= 0:
                continue

            entity_alive = pm.read_int(entity_pawn_addr + m_lifeState)
            if entity_alive != 256:
                continue

            weapon_pointer = pm.read_longlong(entity_pawn_addr + m_pClippingWeapon)
            weapon_index = pm.read_int(weapon_pointer + m_AttributeManager + m_Item + m_iItemDefinitionIndex)
            weapon_name = get_weapon_name_by_index(weapon_index)

            color = QtGui.QColor(255, 255, 255) if entity_team == local_player_team else QtGui.QColor(255, 255, 255)
            color_outline = QtGui.QColor(0, 0, 0) if entity_team == local_player_team else QtGui.QColor(0, 0, 0)
            game_scene = pm.read_longlong(entity_pawn_addr + m_pGameSceneNode)
            bone_matrix = pm.read_longlong(game_scene + m_modelState + 0x80)

            try:
                headX = pm.read_float(bone_matrix + 6 * 0x20)
                headY = pm.read_float(bone_matrix + 6 * 0x20 + 0x4)
                headZ = pm.read_float(bone_matrix + 6 * 0x20 + 0x8) + 8
                head_pos = w2s(view_matrix, headX, headY, headZ, window_width, window_height)
                if head_pos[1] < 0:
                    continue
                if settings['line_rendering'] == 1:
                    legZ = pm.read_float(bone_matrix + 28 * 0x20 + 0x8)
                    leg_pos = w2s(view_matrix, headX, headY, legZ, window_width, window_height)
                    bottom_left_x = head_pos[0] - (head_pos[0] - leg_pos[0]) // 2
                    bottom_y = leg_pos[1]
                    line = scene.addLine(bottom_left_x, bottom_y, no_center_x, no_center_y, QtGui.QPen(color, 1))

                legZ = pm.read_float(bone_matrix + 28 * 0x20 + 0x8)
                leg_pos = w2s(view_matrix, headX, headY, legZ, window_width, window_height)
                deltaZ = abs(head_pos[1] - leg_pos[1])
                leftX = head_pos[0] - deltaZ // 4
                rightX = head_pos[0] + deltaZ // 4

                #1000$ ESP$$$$$$$$$$$$$

                rect = scene.addRect(QtCore.QRectF(leftX, head_pos[1], rightX - leftX, leg_pos[1] - head_pos[1]), 
                    QtGui.QPen(color, 1.5), QtCore.Qt.NoBrush)

                outline_thickness = 1
                rect_out = scene.addRect(QtCore.QRectF(leftX - outline_thickness/2, 
                                                head_pos[1] - outline_thickness/2, 
                                                (rightX - leftX) + outline_thickness, 
                                                (leg_pos[1] - head_pos[1]) + outline_thickness), 
                                    QtGui.QPen(color_outline, outline_thickness), 
                                    QtCore.Qt.NoBrush)

                inner_offset = 2
                rect_in = scene.addRect(QtCore.QRectF(leftX + inner_offset,
                                                head_pos[1] + inner_offset,
                                                (rightX - leftX) - 2 * inner_offset,
                                                (leg_pos[1] - head_pos[1]) - 2 * inner_offset),
                                    QtGui.QPen(color_outline, outline_thickness), 
                                    QtCore.Qt.NoBrush)
                
                #1000$ ESP$$$$$$$$$$$$$

                if settings['hp_bar_rendering'] == 1:
                    max_hp = 100
                    hp_percentage = min(1.0, max(0.0, entity_hp / max_hp))
                    hp_bar_width = 2
                    hp_bar_height = deltaZ
                    hp_bar_x_left = leftX - hp_bar_width - 2
                    hp_bar_y_top = head_pos[1]
                    
                    hp_bar = scene.addRect(QtCore.QRectF(hp_bar_x_left, hp_bar_y_top, hp_bar_width, hp_bar_height), 
                                        QtGui.QPen(QtCore.Qt.NoPen), QtGui.QColor(0, 0, 0))
                    
                    current_hp_height = hp_bar_height * hp_percentage
                    hp_bar_y_bottom = hp_bar_y_top + hp_bar_height - current_hp_height
                    
                    if entity_hp > 50:
                        green = 255
                        red = int(255 * (1 - (entity_hp - 50) / 50))
                    else:
                        red = 255
                        green = int(255 * (entity_hp / 50))
                    
                    hp_color = QtGui.QColor(red, green, 0)

                    hp_bar_current = scene.addRect(QtCore.QRectF(hp_bar_x_left, hp_bar_y_bottom, hp_bar_width, current_hp_height), 
                                                QtGui.QPen(QtCore.Qt.NoPen), hp_color)

                    max_armor_hp = 100
                    armor_hp_percentage = min(1.0, max(0.0, armor_hp / max_armor_hp))
                    armor_bar_width = rightX - leftX
                    armor_bar_height = 2.5
                    armor_bar_x_left = leftX
                    armor_bar_y_top = leg_pos[1] + 2

                    armor_bar = scene.addRect(QtCore.QRectF(armor_bar_x_left, armor_bar_y_top, armor_bar_width, armor_bar_height), 
                                            QtGui.QPen(QtCore.Qt.NoPen), QtGui.QColor(0, 0, 0))
                    
                    current_armor_width = armor_bar_width * armor_hp_percentage

                    if armor_hp > 0:
                        armor_bar_current = scene.addRect(QtCore.QRectF(armor_bar_x_left, 
                                                                armor_bar_y_top, 
                                                                current_armor_width, 
                                                                armor_bar_height), 
                                        QtGui.QPen(QtCore.Qt.NoPen), QtGui.QColor(0, 131, 196))
            

                if settings['head_hitbox_rendering'] == 1:
                    head_hitbox_size = (rightX - leftX) / 5
                    head_hitbox_radius = head_hitbox_size * 2 ** 0.5 / 2
                    head_hitbox_x = leftX + 2.5 * head_hitbox_size
                    head_hitbox_y = head_pos[1] + deltaZ / 9
                    ellipse = scene.addEllipse(QtCore.QRectF(head_hitbox_x - head_hitbox_radius, head_hitbox_y - head_hitbox_radius, head_hitbox_radius * 2, head_hitbox_radius * 2), QtGui.QPen(QtCore.Qt.NoPen), QtGui.QColor(255, 255, 255, 128))

                if settings.get('bons', 0) == 1:
                    draw_bones(scene, pm, bone_matrix, view_matrix, window_width, window_height)

                if settings.get('nickname', 0) == 1:
                    player_name = pm.read_string(entity_controller + m_iszPlayerName, 32)
                    font_path = "C:\\althea\\assets\\fonts\\Roboto.ttf"
                    font = QtGui.QFont(font_path, 8, QtGui.QFont.Bold)
                    name_text = scene.addText(player_name, font)
                    text_rect = name_text.boundingRect()
                    name_x = head_pos[0] - text_rect.width() / 2
                    name_y = head_pos[1] - text_rect.height()
                    name_text.setPos(name_x, name_y)
                    name_text.setDefaultTextColor(QtGui.QColor(255, 255, 255))
                
                if settings.get('weapon', 0) == 1:
                    weapon_font_path = "C:\\althea\\assets\\fonts\\csgo.ttf"
                    weapon_font = QtGui.QFont(weapon_font_path, 7, QtGui.QFont.Bold)
                    weapon_name_text = scene.addText(weapon_name, weapon_font)
                    text_rect = weapon_name_text.boundingRect()
                    weapon_name_x = head_pos[0] - text_rect.width() / 2
                    weapon_name_y = head_pos[1] + deltaZ + 1
                    weapon_name_text.setPos(weapon_name_x, weapon_name_y)
                    weapon_name_text.setDefaultTextColor(QtGui.QColor(255, 255, 255))

            except:
                return
        except:
            return
        
    if 'radius' in settings:
        if settings['radius'] != 0:
            center_x = window_width / 2
            center_y = window_height / 2
            screen_radius = settings['radius'] / 100.0 * min(center_x, center_y)
            ellipse = scene.addEllipse(QtCore.QRectF(center_x - screen_radius, center_y - screen_radius, screen_radius * 2, screen_radius * 2), QtGui.QPen(QtGui.QColor(255, 255, 255, 255), 1), QtCore.Qt.NoBrush)
        
    


def get_weapon_name_by_index(index):
    weapon_names = {
    32: "P2000",
    61: "USP-S",
    4: "Glock",
    2: "Dual Berettas",
    36: "P250",
    30: "Tec-9",
    63: "CZ75-Auto",
    1: "Desert Eagle",
    3: "Five-SeveN",
    262208: "R8",
    35: "Nova",
    25: "XM1014",
    27: "MAG-7",
    29: "Sawed-Off",
    14: "M249",
    28: "Negev",
    17: "MAC-10",
    23: "MP5-SD",
    24: "UMP-45",
    19: "P90",
    26: "Bizon",
    34: "MP9",
    33: "MP7",
    10: "FAMAS",
    16: "M4A4",
    60: "M4A1-S",
    8: "AUG",
    13: "Galil",
    7: "AK-47",
    39: "SG 553",
    40: "SSG 08",
    9: "AWP",
    38: "SCAR-20",
    11: "G3SG1",
    43: "Flashbang",
    44: "Hegrenade",
    45: "Smoke",
    46: "Molotov",
    47: "Decoy",
    48: "Incgrenade",
    49: "C4",
    31: "Taser",
    42: 'Knife',
    41: "Knife Gold",
    59: 'Knife',
    80: "Knife Ghost",
    500: "Knife Bayonet",
    505: "Knife Flip",
    506: "Knife Gut",
    507: "Knife Karambit",
    508: "Knife M9",
    509: "Knife Tactica",
    512: "Knife Falchion",
    514: "Knife Survival Bowie",
    515: "Knife Butterfly",
    516: "Knife Rush",
    519: "Knife Ursus",
    520: "Knife Gypsy Jackknife",
    522: "Knife Stiletto",
    523: "Knife Widowmaker"
}
    return weapon_names.get(index, 'Unknown')

def draw_bones(scene, pm, bone_matrix, view_matrix, width, height):
    bone_ids = {
        "head": 6,
        "neck": 5,
        "spine": 4,
        "pelvis": 0,
        "left_shoulder": 13,
        "left_elbow": 14,
        "left_wrist": 15,
        "right_shoulder": 9,
        "right_elbow": 10,
        "right_wrist": 11,
        "left_hip": 25,
        "left_knee": 26,
        "left_ankle": 27,
        "right_hip": 22,
        "right_knee": 23,
        "right_ankle": 24,
    }
    bone_connections = [
        ("head", "neck"),
        ("neck", "spine"),
        ("spine", "pelvis"),
        ("pelvis", "left_hip"),
        ("left_hip", "left_knee"),
        ("left_knee", "left_ankle"),
        ("pelvis", "right_hip"),
        ("right_hip", "right_knee"),
        ("right_knee", "right_ankle"),
        ("neck", "left_shoulder"),
        ("left_shoulder", "left_elbow"),
        ("left_elbow", "left_wrist"),
        ("neck", "right_shoulder"),
        ("right_shoulder", "right_elbow"),
        ("right_elbow", "right_wrist"),
    ]
    bone_positions = {}
    try:
        for bone_name, bone_id in bone_ids.items():
            boneX = pm.read_float(bone_matrix + bone_id * 0x20)
            boneY = pm.read_float(bone_matrix + bone_id * 0x20 + 0x4)
            boneZ = pm.read_float(bone_matrix + bone_id * 0x20 + 0x8)
            bone_pos = w2s(view_matrix, boneX, boneY, boneZ, width, height)
            if bone_pos[0] != -999 and bone_pos[1] != -999:
                bone_positions[bone_name] = bone_pos
        for connection in bone_connections:
            if connection[0] in bone_positions and connection[1] in bone_positions:
                scene.addLine(
                    bone_positions[connection[0]][0], bone_positions[connection[0]][1],
                    bone_positions[connection[1]][0], bone_positions[connection[1]][1],
                    QtGui.QPen(QtGui.QColor(255, 255, 255, 128), 1)
                )
    except Exception as e:
        print(f"Error drawing bones: {e}")

def esp_main():
    settings = load_settings()
    app = QtWidgets.QApplication(sys.argv)
    window = ESPWindow(settings)
    window.show()
    sys.exit(app.exec())

def triggerbot():
    global trigger_active_indicator
    dwEntityList = 30495944
    dwLocalPlayerPawn = 29299872
    m_iTeamNum = 1003
    m_iIDEntIndex = 5680
    m_iHealth = 844
    m_vecVelocity = 1072
    mouse = Controller()
    default_settings = {
        "keyboards": "X",
        "trigger_bot_active": 1,
        "esp_mode": 1
    }

    def load_settings():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return default_settings

    def is_moving(player):
        try:
            velocity_x = pm.read_float(player + m_vecVelocity)
            velocity_y = pm.read_float(player + m_vecVelocity + 0x4)
            velocity_z = pm.read_float(player + m_vecVelocity + 0x8)
            
            speed = (velocity_x**2 + velocity_y**2 + velocity_z**2)**0.5
            return speed > 5.0
        except:
            return False

    def autostop():
        win32api.keybd_event(0x53, 0, 0, 0)
        time.sleep(0.01)
        win32api.keybd_event(0x53, 0, win32con.KEYEVENTF_KEYUP, 0)

    def main(settings):

        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        while True:
            try:
                trigger_bot_active = settings["trigger_bot_active"]
                attack_all = settings["esp_mode"]
                keyboards = settings["keyboards"]
                
                if win32api.GetAsyncKeyState(ord(keyboards)):
                    trigger_active_indicator.value = True
                    
                    if trigger_bot_active == 1:
                        try:
                            player = pm.read_longlong(client + dwLocalPlayerPawn)
                            entityId = pm.read_int(player + m_iIDEntIndex)
                            
                            if entityId > 0:
                                entList = pm.read_longlong(client + dwEntityList)
                                entEntry = pm.read_longlong(entList + 0x8 * (entityId >> 9) + 0x10)
                                entity = pm.read_longlong(entEntry + 120 * (entityId & 0x1FF))
                                entityTeam = pm.read_int(entity + m_iTeamNum)
                                playerTeam = pm.read_int(player + m_iTeamNum)
                                
                                if (attack_all == 1) or (entityTeam != playerTeam and attack_all == 0):
                                    entityHp = pm.read_int(entity + m_iHealth)
                                    
                                    if entityHp > 0:
                                        
                                        mouse.press(Button.left)
                                        time.sleep(0.05)
                                        mouse.release(Button.left)
                                        
                                        time.sleep(0.03)

                        except Exception as e:
                            pass
                    time.sleep(0.03)
                else:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                break
            except Exception:
                time.sleep(1)

    def start_main_thread(settings):
        while True:
            main(settings)

    def setup_watcher(app, settings):
        watcher = QFileSystemWatcher()
        watcher.addPath(CONFIG_FILE)
        def reload_settings():
            new_settings = load_settings()
            settings.update(new_settings)
        watcher.fileChanged.connect(reload_settings)
        app.exec()

    def main_program():
        app = QCoreApplication(sys.argv)
        settings = load_settings()
        threading.Thread(target=start_main_thread, args=(settings,), daemon=True).start()
        setup_watcher(app, settings)

    main_program()


def misc():
    default_settings = {
        'anti_flash': 0,
        'fov': 90,
        'bhop': 0
    }

    def load_settings():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return default_settings

    def main(settings):

        if settings.get("anti_flash", 0) == 1:
                dwLocalPlayerPawn = 29299872
                pm = pymem.Pymem("cs2.exe")
                client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
                player = pm.read_longlong(client + dwLocalPlayerPawn)
                pm.write_int(player + 5660, 0)
        
        if settings.get("anti_flash", 1) == 0:
                dwLocalPlayerPawn = 29299872
                pm = pymem.Pymem("cs2.exe")
                client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
                player = pm.read_longlong(client + dwLocalPlayerPawn)
                pm.write_int(player + 5660, 0)

        if settings.get('fov') > 0:
                dwLocalPlayerController = 31582104
                pm = pymem.Pymem("cs2.exe")
                client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
                a = pm.read_longlong(client + dwLocalPlayerController)
                pm.write_int(a + 1916, settings.get('fov'))
        
        if settings.get('bhop', 0) == 1:
            dwLocalPlayerPawn = 29299872
            m_fFlags = 1016
            pm = pymem.Pymem("cs2.exe")
            client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
            local_player_pawn_addr = pm.read_longlong(client + dwLocalPlayerPawn)
            while True:
                if win32api.GetAsyncKeyState(win32con.VK_SPACE):
                    try:
                        PlayerMoveFlag = pm.read_int(local_player_pawn_addr + m_fFlags)
                        if (PlayerMoveFlag == 65665 or PlayerMoveFlag == 65667):
                            hwnd = win32gui.FindWindow(None, 'Counter-Strike 2')
                            win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_SPACE, 0)
                            time.sleep(0)
                            win32api.SendMessage(hwnd, win32con.WM_KEYUP, win32con.VK_SPACE, 0)
                    except:
                        time.sleep(0)
                        pass
                time.sleep(0)

    def start_main_thread(settings):
        while True:
            main(settings)

    def setup_watcher(app, settings):
        watcher = QFileSystemWatcher()
        watcher.addPath(CONFIG_FILE)
        def reload_settings():
            new_settings = load_settings()
            settings.update(new_settings)
        watcher.fileChanged.connect(reload_settings)
        app.exec()

    def main_program():
        app = QCoreApplication(sys.argv)
        settings = load_settings()
        threading.Thread(target=start_main_thread, args=(settings,), daemon=True).start()
        setup_watcher(app, settings)

    main_program()

def aim():
    default_settings = {
        'esp_rendering': 1,
        'esp_mode': 1,
        'keyboard': "V",
        'aim_active': 1,
        'aim_mode': 1,
        'radius': 20,
        'aim_mode_distance': 1,
    }

    def get_window_size(window_name="Counter-Strike 2"):
        hwnd = win32gui.FindWindow(None, window_name)
        if hwnd:
            rect = win32gui.GetClientRect(hwnd)
            return rect[2] - rect[0], rect[3] - rect[1]
        return 1920, 1080

    def load_settings():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return default_settings

    def get_offsets_and_client_dll():
        offsets = 1
        client_dll = 1
        return offsets, client_dll

    def esp(pm, client, offsets, client_dll, settings, target_list, window_size):
        width, height = window_size
        if settings['aim_active'] == 0:
            return
        dwEntityList = 30495944
        dwLocalPlayerPawn = 29299872
        dwViewMatrix = 31664176
        m_iTeamNum = 1003
        m_lifeState = 848
        m_pGameSceneNode = 816
        m_modelState = 400
        m_hPlayerPawn = 2300
        view_matrix = [pm.read_float(client + dwViewMatrix + i * 4) for i in range(16)]
        local_player_pawn_addr = pm.read_longlong(client + dwLocalPlayerPawn)
        try:
            local_player_team = pm.read_int(local_player_pawn_addr + m_iTeamNum)
        except:
            return
        entity_list = pm.read_longlong(client + dwEntityList)
        entity_ptr = pm.read_longlong(entity_list + 0x10)

        for i in range(1, 64):
            try:
                if entity_ptr == 0:
                    break
    
                entity_controller = pm.read_longlong(entity_ptr + 0x78 * (i & 0x1FF))
                if entity_controller == 0:
                    continue
    
                entity_controller_pawn = pm.read_longlong(entity_controller + m_hPlayerPawn)
                if entity_controller_pawn == 0:
                    continue
    
                entity_list_pawn = pm.read_longlong(entity_list + 0x8 * ((entity_controller_pawn & 0x7FFF) >> 0x9) + 0x10)
                if entity_list_pawn == 0:
                    continue
    
                entity_pawn_addr = pm.read_longlong(entity_list_pawn + 0x78 * (entity_controller_pawn & 0x1FF))
                if entity_pawn_addr == 0 or entity_pawn_addr == local_player_pawn_addr:
                    continue
    
                entity_team = pm.read_int(entity_pawn_addr + m_iTeamNum)
                if entity_team == local_player_team and settings['esp_mode'] == 0:
                    continue
    
                entity_alive = pm.read_int(entity_pawn_addr + m_lifeState)
                if entity_alive != 256:
                    continue
                game_scene = pm.read_longlong(entity_pawn_addr + m_pGameSceneNode)
                bone_matrix = pm.read_longlong(game_scene + m_modelState + 0x80)
                try:
                    bone_id = 6 if settings['aim_mode'] == 1 else 4
                    headX = pm.read_float(bone_matrix + bone_id * 0x20)
                    headY = pm.read_float(bone_matrix + bone_id * 0x20 + 0x4)
                    headZ = pm.read_float(bone_matrix + bone_id * 0x20 + 0x8)
                    head_pos = w2s(view_matrix, headX, headY, headZ, width, height)
                    legZ = pm.read_float(bone_matrix + 28 * 0x20 + 0x8)
                    leg_pos = w2s(view_matrix, headX, headY, legZ, width, height)
                    deltaZ = abs(head_pos[1] - leg_pos[1])
                    if head_pos[0] != -999 and head_pos[1] != -999:
                        if settings['aim_mode_distance'] == 1:
                            target_list.append({
                                'pos': head_pos,
                                'deltaZ': deltaZ
                            })
                        else:
                            target_list.append({
                                'pos': head_pos,
                                'deltaZ': None
                            })

                except Exception as e:
                    pass
            except:
                return
        return target_list

    def aimbot(target_list, radius, aim_mode_distance):
        if not target_list:
            return
        center_x = win32api.GetSystemMetrics(0) // 2
        center_y = win32api.GetSystemMetrics(1) // 2

        if radius == 0:
            closest_target = None
            closest_dist = float('inf')
            for target in target_list:
                dist = ((target['pos'][0] - center_x) ** 2 + (target['pos'][1] - center_y) ** 2) ** 0.5
                if dist < closest_dist:
                    closest_target = target['pos']
                    closest_dist = dist
        else:
            screen_radius = radius / 100.0 * min(center_x, center_y)
            closest_target = None
            closest_dist = float('inf')
            if aim_mode_distance == 1:
                target_with_max_deltaZ = None
                max_deltaZ = -float('inf')
                for target in target_list:
                    dist = ((target['pos'][0] - center_x) ** 2 + (target['pos'][1] - center_y) ** 2) ** 0.5
                    if dist < screen_radius and target['deltaZ'] > max_deltaZ:
                        max_deltaZ = target['deltaZ']
                        target_with_max_deltaZ = target
                closest_target = target_with_max_deltaZ['pos'] if target_with_max_deltaZ else None
            else:
                for target in target_list:
                    dist = ((target['pos'][0] - center_x) ** 2 + (target['pos'][1] - center_y) ** 2) ** 0.5
                    if dist < screen_radius and dist < closest_dist:
                        closest_target = target['pos']
                        closest_dist = dist
        if closest_target:
            target_x, target_y = closest_target
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(target_x - center_x), int(target_y - center_y), 0, 0)

    def main(settings):
        offsets, client_dll = get_offsets_and_client_dll()
        window_size = get_window_size()
        pm = pymem.Pymem("cs2.exe")
        client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
        while True:
            target_list = []
            target_list = esp(pm, client, offsets, client_dll, settings, target_list, window_size)
            if win32api.GetAsyncKeyState(ord(settings['keyboard'])):
                aimbot(target_list, settings['radius'], settings['aim_mode_distance'])
            time.sleep(0.01)

    def start_main_thread(settings):
        while True:
            main(settings)

    def setup_watcher(app, settings):
        watcher = QFileSystemWatcher()
        watcher.addPath(CONFIG_FILE)
        def reload_settings():
            new_settings = load_settings()
            settings.update(new_settings)
        watcher.fileChanged.connect(reload_settings)
        app.exec()

    def main_program():
        app = QCoreApplication(sys.argv)
        settings = load_settings()
        threading.Thread(target=start_main_thread, args=(settings,), daemon=True).start()
        setup_watcher(app, settings)

    main_program()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--config":
        app = QtWidgets.QApplication(sys.argv)
        apply_stylesheet(app, theme='altea.xml')
        window = ConfigWindow()
        window.show()
        app.exec()
    else:
        os.system("cls")
        print("waiting for cs2.exe.")
        
        while True:
            try:
                pm = pymem.Pymem("cs2.exe")
                client = pymem.process.module_from_name(pm.process_handle, "client.dll").lpBaseOfDll
                print(f"process cs2.exe is found.")
                break
            except Exception as e:
                time.sleep(1)

        print("cheat started.")
        app = MainApplication()
        app.run()