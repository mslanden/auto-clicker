#!/usr/bin/env python3
"""
Auto Clicker Web - Beautiful web-based interface
"""

from flask import Flask, render_template, jsonify, request
import pyautogui
import threading
import time
import json
import os
import random
import webbrowser
from datetime import datetime
from pynput import keyboard
import re
import logging

# Disable PyAutoGUI's fail-safe
pyautogui.FAILSAFE = False

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

# Global state
class ClickerState:
    def __init__(self):
        self.positions = []
        self.sequences = []
        self.running = False
        self.paused = False
        self.threads = []
        self.sequence_threads = []
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.total_clicks = 0
        self.session_start_time = None
        self.variance_enabled = True
        # Global variance defaults
        self.global_jitter_px = 3
        self.global_time_jitter = 0.10  # 10%
        # Limits
        self.max_total_clicks = None  # int or None
        self.max_session_minutes = None  # int or None
        # Default start delay (seconds)
        self.default_start_delay = 0
        # Hotkeys (single-character, lowercased)
        self.hotkeys = {
            'pause': 'p',
            'stop': 'q',
        }
        # Concurrency lock for state changes
        self.lock = threading.Lock()
        
clicker = ClickerState()

# Configuration directory
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_configs")
os.makedirs(CONFIG_DIR, exist_ok=True)

@app.route('/')
def index():
    """Serve the main page"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Auto Clicker Pro</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 900px;
            width: 100%;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .stats {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-top: 20px;
        }
        
        .stat {
            text-align: center;
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: bold;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .controls {
            padding: 30px;
            background: #f8f9fa;
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn-start {
            background: #4CAF50;
            color: white;
        }
        
        .btn-pause {
            background: #FF9800;
            color: white;
        }
        
        .btn-stop {
            background: #F44336;
            color: white;
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .content {
            padding: 30px;
        }
        
        .section {
            margin-bottom: 30px;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .section-title {
            font-size: 1.5em;
            color: #333;
        }
        
        .add-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .add-btn:hover {
            transform: scale(1.05);
        }
        
        .icon { width: 16px; height: 16px; display: inline-block; vertical-align: -2px; margin-right: 6px; }
        .icon-btn .icon { margin-right: 0; }

        .positions-list {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .position-item {
            padding: 20px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.3s ease;
        }
        
        .position-item:hover {
            background: #f8f9fa;
        }
        
        .position-info {
            flex: 1;
        }
        
        .position-name {
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        
        .position-details {
            color: #666;
            font-size: 0.9em;
        }
        
        .position-actions {
            display: flex;
            gap: 10px;
        }
        
        .icon-btn {
            width: 35px;
            height: 35px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }
        
        .icon-btn:hover {
            transform: scale(1.1);
        }
        
        .btn-delete {
            background: #ffebee;
            color: #F44336;
        }
        
        .btn-edit {
            background: #e3f2fd;
            color: #2196F3;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        
        .modal.active {
            display: flex;
        }
        
        .modal-content {
            background: white;
            border-radius: 15px;
            padding: 30px;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        
        .modal-header {
            font-size: 1.5em;
            margin-bottom: 20px;
            color: #333;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-label {
            display: block;
            margin-bottom: 8px;
            color: #666;
            font-weight: 500;
        }
        
        .form-input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
            transition: border-color 0.3s ease;
        }
        
        .form-input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .form-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 25px;
        }
        
        .capture-info {
            background: #f3e5f5;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
            color: #7b1fa2;
        }
        
        .current-position {
            font-size: 1.2em;
            font-weight: bold;
            color: #667eea;
            margin-top: 10px;
        }
        
        .settings {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
        }
        
        .checkbox-group {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .checkbox-group input[type="checkbox"] {
            width: 20px;
            height: 20px;
            margin-right: 10px;
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        
        .empty-state-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        
        .empty-state-text {
            font-size: 1.2em;
        }
        
        kbd {
            background-color: #f7f7f7;
            border: 1px solid #ccc;
            border-radius: 3px;
            box-shadow: 0 1px 0 rgba(0,0,0,0.2), 0 0 0 2px #fff inset;
            color: #333;
            display: inline-block;
            font-family: monospace;
            font-size: 0.9em;
            font-weight: bold;
            line-height: 1;
            padding: 2px 4px;
            white-space: nowrap;
        }

        /* ---- Modern dark/glass overrides for a cooler look ---- */
        :root {
            --bg: #0b0f1a;
            --surface: rgba(18, 24, 38, 0.8);
            --surface-2: rgba(20, 28, 46, 0.7);
            --border: rgba(255,255,255,0.08);
            --text: #e7ecf4;
            --muted: #97a2b1;
            --brand: #7c5cff;
            --brand-2: #2cd4d9;
            --ok: #32d583;
            --warn: #ffb020;
            --danger: #ff5d5d;
            --ring: rgba(124,92,255,0.45);
        }
        body {
            background:
              radial-gradient(1200px 700px at 15% -10%, rgba(124,92,255,0.18), transparent 60%),
              radial-gradient(1000px 600px at 110% 0%, rgba(44,212,217,0.14), transparent 60%),
              var(--bg) !important;
            color: var(--text);
        }
        .container {
            background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
            border: 1px solid var(--border);
            backdrop-filter: blur(10px);
            box-shadow: 0 20px 60px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.05);
        }
        .header {
            background:
              linear-gradient(135deg, rgba(124,92,255,0.22), rgba(44,212,217,0.18));
            border-bottom: 1px solid var(--border);
        }
        .header h1 { text-shadow: 0 6px 28px rgba(124,92,255,0.35); }
        .stats { gap: 18px !important; }
        .stat {
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 16px 18px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        }
        .stat-value { color: var(--text); }
        .stat-label { color: var(--muted); }
        .controls { background: transparent; }
        .btn { color: #fff; }
        .btn-start { background: linear-gradient(135deg, var(--ok), #2cc79a); }
        .btn-pause { background: linear-gradient(135deg, var(--warn), #ff9f43); }
        .btn-stop { background: linear-gradient(135deg, var(--danger), #ff4d6d); }
        .add-btn { background: linear-gradient(135deg, var(--brand), #5b87ff); }
        .btn, .add-btn {
            box-shadow: 0 14px 34px rgba(124,92,255,0.22);
            border: 1px solid rgba(255,255,255,0.08);
        }
        .btn:hover, .add-btn:hover {
            transform: translateY(-2px) scale(1.01);
            box-shadow: 0 18px 48px rgba(124,92,255,0.32);
        }
        .content { padding: 26px; }
        .section-title { color: var(--text); letter-spacing: .3px; }
        .positions-list {
            background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02));
            border: 1px solid var(--border);
        }
        .position-item {
            background: rgba(255,255,255,0.02);
            border-bottom: 1px solid var(--border);
        }
        .position-item:hover { background: rgba(124,92,255,0.08); }
        .position-name { color: var(--text); }
        .position-details { color: var(--muted); }
        .btn-edit { background: rgba(124,92,255,0.18); color: #d7d0ff; }
        .btn-delete { background: rgba(255,93,93,0.15); color: #ffb1b1; }
        .settings { background: var(--surface-2); border: 1px solid var(--border); }
        .modal { background: rgba(6, 8, 14, 0.6); backdrop-filter: blur(8px); }
        .modal-content {
            background: var(--surface);
            border: 1px solid var(--border);
            color: var(--text);
        }
        .form-input { background: rgba(255,255,255,0.06); border: 1px solid var(--border); color: var(--text); }
        .form-input:focus { border-color: var(--ring); box-shadow: 0 0 0 4px rgba(124,92,255,0.12); }
        .capture-info { background: rgba(124,92,255,0.14); color: #e8e2ff; }
        .current-position { color: #c8b9ff; }
        kbd { background: rgba(255,255,255,0.08); border: 1px solid var(--border); color: var(--text); }
    </style>
</head>
<body>
    <!-- Inline SVG sprite for icons -->
    <svg xmlns="http://www.w3.org/2000/svg" style="position:absolute;width:0;height:0;overflow:hidden">
      <symbol id="i-mouse" viewBox="0 0 24 24">
        <path fill="currentColor" d="M12 2a6 6 0 016 6v8a6 6 0 01-12 0V8a6 6 0 016-6zm0 2a4 4 0 00-4 4v2h8V8a4 4 0 00-4-4z"/>
      </symbol>
      <symbol id="i-play" viewBox="0 0 24 24">
        <path fill="currentColor" d="M8 5v14l11-7z"/>
      </symbol>
      <symbol id="i-pause" viewBox="0 0 24 24">
        <rect x="6" y="5" width="5" height="14" fill="currentColor"/>
        <rect x="13" y="5" width="5" height="14" fill="currentColor"/>
      </symbol>
      <symbol id="i-stop" viewBox="0 0 24 24">
        <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"/>
      </symbol>
      <symbol id="i-plus" viewBox="0 0 24 24">
        <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </symbol>
      <symbol id="i-edit" viewBox="0 0 24 24">
        <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25z" fill="currentColor"/>
        <path d="M20.71 7.04a1 1 0 000-1.41L18.37 3.29a1 1 0 00-1.41 0l-1.84 1.84 3.75 3.75 1.84-1.84z" fill="currentColor"/>
      </symbol>
      <symbol id="i-trash" viewBox="0 0 24 24">
        <path d="M6 7h12M9 7V5a2 2 0 012-2h2a2 2 0 012 2v2M7 7l1 12a2 2 0 002 2h4a2 2 0 002-2l1-12" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
      </symbol>
      <symbol id="i-pin" viewBox="0 0 24 24">
        <path fill="currentColor" d="M12 2a7 7 0 00-7 7c0 5.5 7 13 7 13s7-7.5 7-13a7 7 0 00-7-7zm0 9a2 2 0 110-4 2 2 0 010 4z"/>
      </symbol>
      <symbol id="i-loop" viewBox="0 0 24 24">
        <path d="M17 1l4 4-4 4" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M3 11a8 8 0 0113-6l5 4" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
        <path d="M7 23l-4-4 4-4" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M21 13a8 8 0 01-13 6l-5-4" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
      </symbol>
      <symbol id="i-disk" viewBox="0 0 24 24">
        <path fill="currentColor" d="M4 4h12l4 4v12a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2zm3 0v5h8V4H7zm0 9h10v7H7v-7z"/>
      </symbol>
      <symbol id="i-folder" viewBox="0 0 24 24">
        <path fill="currentColor" d="M3 6a2 2 0 012-2h5l2 2h7a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V6z"/>
      </symbol>
    </svg>
    <div class="container">
        <div class="header">
            <h1><svg class="icon" aria-hidden="true"><use href="#i-mouse"></use></svg>Auto Clicker Pro</h1>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value" id="total-clicks">0</div>
                    <div class="stat-label">Total Clicks</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="session-time">00:00:00</div>
                    <div class="stat-label">Session Time</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="active-positions">0</div>
                    <div class="stat-label">Active Positions</div>
                </div>
            </div>
        </div>
        
        <div class="controls">
            <button class="btn btn-start" id="start-btn" onclick="startClicking()"><svg class="icon" aria-hidden="true"><use href="#i-play"></use></svg>Start</button>
            <button class="btn btn-pause" id="pause-btn" onclick="pauseClicking()" disabled><svg class="icon" aria-hidden="true"><use href="#i-pause"></use></svg>Pause</button>
            <button class="btn btn-stop" id="stop-btn" onclick="stopClicking()" disabled><svg class="icon" aria-hidden="true"><use href="#i-stop"></use></svg>Stop</button>
        </div>
        
        <div class="content">
            <div class="section">
                <div class="section-header">
                    <h2 class="section-title">Click Positions</h2>
                    <button class="add-btn" id="add-position-btn" onclick="showAddModal()"><svg class="icon" aria-hidden="true"><use href="#i-plus"></use></svg>Add Position</button>
                </div>
                
                <div id="positions-container">
                    <div class="empty-state">
                        <div class="empty-state-icon"><svg class="icon" aria-hidden="true"><use href="#i-pin"></use></svg></div>
                        <div class="empty-state-text">No positions added yet</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-header">
                    <h2 class="section-title">Sequences</h2>
                    <button class="add-btn" id="add-seq-btn" onclick="showSequenceModal()"><svg class="icon" aria-hidden="true"><use href="#i-plus"></use></svg>Add Sequence</button>
                </div>
                
                <div id="sequences-container">
                    <div class="empty-state">
                        <div class="empty-state-icon"><svg class="icon" aria-hidden="true"><use href="#i-loop"></use></svg></div>
                        <div class="empty-state-text">No sequences created yet</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2 class="section-title">Settings</h2>
                <div class="settings">
                    <div class="checkbox-group">
                        <input type="checkbox" id="variance-enabled" checked onchange="updateVariance()">
                        <label for="variance-enabled">Enable anti-detection variance (±3px position, ±10% timing)</label>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Start Delay (seconds)</label>
                        <input type="number" class="form-input" id="start-delay" value="0" min="0" step="1">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Global Jitter (px)</label>
                        <input type="number" class="form-input" id="global-jitter-px" value="3" min="0">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Global Timing Jitter (%)</label>
                        <input type="number" class="form-input" id="global-jitter-time" value="10" min="0" max="100">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Max Total Clicks (optional)</label>
                        <input type="number" class="form-input" id="max-total-clicks" min="0" placeholder="e.g., 1000">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Max Session Minutes (optional)</label>
                        <input type="number" class="form-input" id="max-session-mins" min="0" placeholder="e.g., 60">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Hotkeys</label>
                        <div>
                            Pause <input type="text" class="form-input" id="hotkey-pause" maxlength="1" style="width:60px; display:inline-block;"> 
                            Stop <input type="text" class="form-input" id="hotkey-stop" maxlength="1" style="width:60px; display:inline-block;">
                        </div>
                    </div>
                    <div style="margin-top: 15px;">
                        <strong>Global Keyboard Shortcuts:</strong><br>
                        <kbd id="kbd-pause">P</kbd> = Pause/Resume | <kbd id="kbd-stop">Q</kbd> = Stop | <kbd>1-9</kbd> = Trigger Sequences
                    </div>
                    <div class="checkbox-group">
                        <button class="add-btn" onclick="saveConfig()"><svg class="icon" aria-hidden="true"><use href="#i-disk"></use></svg>Save Config</button>
                        <button class="add-btn" onclick="loadConfig()" style="margin-left: 10px;"><svg class="icon" aria-hidden="true"><use href="#i-folder"></use></svg>Load Config</button>
                        <button class="add-btn" onclick="saveSettings()" style="margin-left: 10px;"><svg class="icon" aria-hidden="true"><use href="#i-disk"></use></svg>Save Settings</button>
                        <button class="add-btn" onclick="resetStats()" style="margin-left: 10px;"><svg class="icon" aria-hidden="true"><use href="#i-loop"></use></svg>Reset Stats</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Add Position Modal -->
    <div class="modal" id="add-modal">
        <div class="modal-content">
            <h2 class="modal-header">Add Click Position</h2>
            
            <div class="capture-info">
                <strong>Step 1:</strong> Move your mouse over the target (anywhere on screen)<br>
                <strong>Step 2:</strong> Press <kbd>ENTER</kbd> to capture that position
                <div class="current-position" id="current-position">Current: (0, 0)</div>
                <div id="capture-status" style="margin-top: 10px; font-weight: bold;"></div>
            </div>
            
            <div class="form-group">
                <label class="form-label">Position Name</label>
                <input type="text" class="form-input" id="position-name" placeholder="e.g., Button 1">
            </div>
            
            <div class="form-group">
                <label class="form-label">X Position</label>
                <input type="number" class="form-input" id="position-x" readonly>
            </div>
            
            <div class="form-group">
                <label class="form-label">Y Position</label>
                <input type="number" class="form-input" id="position-y" readonly>
            </div>
            
            <div class="form-group">
                <label class="form-label">Click Interval (seconds)</label>
                <input type="number" class="form-input" id="position-interval" value="1.0" step="0.1" min="0.1">
            </div>
            <div class="form-group">
                <label class="form-label">Mouse Button</label>
                <select class="form-input" id="position-button">
                    <option value="left">Left</option>
                    <option value="middle">Middle</option>
                    <option value="right">Right</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Click Type</label>
                <select class="form-input" id="position-click-type" onchange="toggleHold()">
                    <option value="single">Single</option>
                    <option value="double">Double</option>
                    <option value="hold">Hold</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Hold Duration (seconds)</label>
                <input type="number" class="form-input" id="position-hold" value="0.2" step="0.05" min="0" disabled>
            </div>
            <div class="form-group">
                <label class="form-label">Per-position Jitter (px)</label>
                <input type="number" class="form-input" id="position-jitter-px" value="3" min="0">
            </div>
            <div class="form-group">
                <label class="form-label">Per-position Timing Jitter (%)</label>
                <input type="number" class="form-input" id="position-jitter-time" value="10" min="0" max="100">
            </div>
            
            <div class="form-actions">
                <button class="btn" onclick="retakePosition()" id="retake-btn" style="display: none;"><svg class="icon" aria-hidden="true"><use href="#i-loop"></use></svg>Retake</button>
                <button class="btn btn-start" onclick="savePosition()" id="save-btn" disabled><svg class="icon" aria-hidden="true"><use href="#i-disk"></use></svg>Save</button>
                <button class="btn" onclick="closeModal()">Cancel</button>
            </div>
        </div>
    </div>
    
    <!-- Add Sequence Modal -->
    <div class="modal" id="sequence-modal">
        <div class="modal-content">
            <h2 class="modal-header">Create Sequence</h2>
            
            <div class="form-group">
                <label class="form-label">Sequence Name</label>
                <input type="text" class="form-input" id="sequence-name" placeholder="e.g., Combo Attack">
            </div>
            
            <div class="form-group">
                <label class="form-label">Trigger Key (1-9)</label>
                <select class="form-input" id="sequence-key">
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="3">3</option>
                    <option value="4">4</option>
                    <option value="5">5</option>
                    <option value="6">6</option>
                    <option value="7">7</option>
                    <option value="8">8</option>
                    <option value="9">9</option>
                </select>
            </div>
            
            <div class="form-group">
                <div class="checkbox-group">
                    <input type="checkbox" id="sequence-auto-enabled" onchange="toggleAutoInterval()">
                    <label for="sequence-auto-enabled">Run automatically on timer</label>
                </div>
            </div>
            
            <div class="form-group" id="auto-interval-group" style="display: none;">
                <label class="form-label">Auto Interval (seconds)</label>
                <input type="number" class="form-input" id="sequence-auto-interval" value="30.0" step="0.5" min="1.0">
                <small style="color: #666;">How often to automatically run this sequence</small>
            </div>
            
            <div class="form-group">
                <label class="form-label">Sequence Steps</label>
                <div id="sequence-steps">
                    <div class="empty-state" style="padding: 20px;">
                        <div class="empty-state-text">No steps added yet</div>
                    </div>
                </div>
                <button type="button" class="add-btn" onclick="addSequenceStep()" style="margin-top: 10px;">+ Add Step</button>
            </div>
            
            <div class="form-actions">
                <button class="btn btn-start" onclick="saveSequence()"><svg class="icon" aria-hidden="true"><use href="#i-disk"></use></svg>Save Sequence</button>
                <button class="btn" onclick="closeSequenceModal()">Cancel</button>
            </div>
        </div>
    </div>
    
    <!-- Add Step Modal -->
    <div class="modal" id="step-modal">
        <div class="modal-content">
            <h2 class="modal-header">Add Step</h2>
            
            <div class="form-group">
                <label class="form-label">Click Position</label>
                <select class="form-input" id="step-position">
                    <!-- Will be populated with positions -->
                </select>
            </div>
            
            <div class="form-group">
                <label class="form-label">Delay before next step (seconds)</label>
                <input type="number" class="form-input" id="step-next-delay" value="1.0" step="0.1" min="0.0">
                <small style="color: #666;">Time to wait after clicking before the next step (0 = instant)</small>
            </div>
            
            <div class="form-actions">
                <button class="btn btn-start" onclick="saveStep()">Add Step</button>
                <button class="btn" onclick="closeStepModal()">Cancel</button>
            </div>
        </div>
    </div>
    
    <script>
        let positions = [];
        let sequences = [];
        let updateTimer;
        let mouseUpdateTimer;
        let captureMode = false;
        let captured = false;
        let currentSequenceSteps = [];
        let editingStepIndex = -1;
        
        // Update mouse position in modal
        function startMouseTracking() {
            captureMode = true;
            captured = false;
            document.getElementById('capture-status').textContent = 'Ready to capture - move mouse and press ENTER';
            document.getElementById('capture-status').style.color = '#2196F3';
            document.getElementById('save-btn').disabled = true;
            document.getElementById('retake-btn').style.display = 'none';
            
            mouseUpdateTimer = setInterval(() => {
                if (!captureMode) return;
                
                fetch('/api/mouse-position')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('current-position').textContent = `Current: (${data.x}, ${data.y})`;
                        document.getElementById('position-x').value = data.x;
                        document.getElementById('position-y').value = data.y;
                    });
            }, 50);
        }
        
        function stopMouseTracking() {
            captureMode = false;
            if (mouseUpdateTimer) {
                clearInterval(mouseUpdateTimer);
            }
        }
        
        function captureCurrentPosition() {
            if (!captureMode) return;
            
            captured = true;
            captureMode = false;
            
            document.getElementById('capture-status').textContent = 'Position captured!';
            document.getElementById('capture-status').style.color = '#4CAF50';
            document.getElementById('save-btn').disabled = false;
            document.getElementById('retake-btn').style.display = 'inline-block';
            
            // Stop live updates
            if (mouseUpdateTimer) {
                clearInterval(mouseUpdateTimer);
            }
        }
        
        function retakePosition() {
            // Remove edit mode listener and start normal capture mode
            document.removeEventListener('keydown', handleEditKeyPress);
            startMouseTracking();
        }
        
        function showAddModal() {
            document.getElementById('add-modal').classList.add('active');
            document.getElementById('position-name').value = `Position ${positions.length + 1}`;
            startMouseTracking();
            
            // Set up Enter key listener for capture
            document.addEventListener('keydown', handleKeyPress);
        }
        
        function closeModal() {
            document.getElementById('add-modal').classList.remove('active');
            stopMouseTracking();
            // Clean up both possible event listeners
            document.removeEventListener('keydown', handleKeyPress);
            document.removeEventListener('keydown', handleEditKeyPress);
            
            // Reset save button to default behavior
            document.getElementById('save-btn').onclick = savePosition;
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter' && captureMode) {
                event.preventDefault();
                captureCurrentPosition();
            } else if (event.key === 'Escape') {
                closeModal();
            }
        }
        
        function handleEditKeyPress(event) {
            // In edit mode, Enter just submits the form (normal behavior)
            // Don't capture new position unless user clicks "Retake"
            if (event.key === 'Escape') {
                closeModal();
            }
            // Enter key works normally in input fields during edit
        }
        
        function savePosition() {
            if (!captured) {
                alert('Please capture a position first by pressing ENTER while hovering over your target');
                return;
            }
            const name = document.getElementById('position-name').value;
            const x = parseInt(document.getElementById('position-x').value);
            const y = parseInt(document.getElementById('position-y').value);
            const interval = parseFloat(document.getElementById('position-interval').value);
            const button = document.getElementById('position-button').value;
            const click_type = document.getElementById('position-click-type').value;
            const hold_duration = parseFloat(document.getElementById('position-hold').value || '0');
            const pos_jitter = parseInt(document.getElementById('position-jitter-px').value || '0');
            const time_jitter = parseFloat(document.getElementById('position-jitter-time').value || '0') / 100.0;
            if (!name.trim()) {
                alert('Please enter a position name');
                return;
            }
            fetch('/api/add-position', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, x, y, interval, button, click_type, hold_duration, pos_jitter, time_jitter})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    loadPositions();
                    closeModal();
                } else if (data.message) {
                    alert(data.message);
                }
            });
        }
        
        function editPosition(index) {
            const pos = positions[index];
            document.getElementById('add-modal').classList.add('active');
            document.getElementById('position-name').value = pos.name;
            document.getElementById('position-x').value = pos.x;
            document.getElementById('position-y').value = pos.y;
            document.getElementById('position-interval').value = pos.interval;
            document.getElementById('position-button').value = pos.button || 'left';
            document.getElementById('position-click-type').value = pos.click_type || 'single';
            document.getElementById('position-hold').value = pos.hold_duration || 0;
            document.getElementById('position-jitter-px').value = (pos.pos_jitter ?? 3);
            document.getElementById('position-jitter-time').value = Math.round(((pos.time_jitter ?? 0.1) * 100));
            toggleHold();
            captured = true;
            captureMode = false;
            document.getElementById('capture-status').textContent = 'Position loaded for editing';
            document.getElementById('capture-status').style.color = '#4CAF50';
            document.getElementById('save-btn').disabled = false;
            document.getElementById('retake-btn').style.display = 'inline-block';
            document.addEventListener('keydown', handleEditKeyPress);
            const saveBtn = document.getElementById('save-btn');
            saveBtn.onclick = function() { updatePosition(index); };
        }
        
        function updatePosition(index) {
            const name = document.getElementById('position-name').value;
            const x = parseInt(document.getElementById('position-x').value);
            const y = parseInt(document.getElementById('position-y').value);
            const interval = parseFloat(document.getElementById('position-interval').value);
            const button = document.getElementById('position-button').value;
            const click_type = document.getElementById('position-click-type').value;
            const hold_duration = parseFloat(document.getElementById('position-hold').value || '0');
            const pos_jitter = parseInt(document.getElementById('position-jitter-px').value || '0');
            const time_jitter = parseFloat(document.getElementById('position-jitter-time').value || '0') / 100.0;
            if (!name.trim()) {
                alert('Please enter a position name');
                return;
            }
            fetch(`/api/update-position/${index}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, x, y, interval, button, click_type, hold_duration, pos_jitter, time_jitter})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    loadPositions();
                    closeModal();
                    document.getElementById('save-btn').onclick = savePosition;
                } else if (data.message) {
                    alert(data.message);
                }
            });
        }
        
        function deletePosition(index) {
            if (confirm('Delete this position?')) {
                fetch(`/api/delete-position/${index}`, {method: 'DELETE'})
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            loadPositions();
                        } else if (data.message) { alert(data.message); }
                    });
            }
        }
        
        function loadPositions() {
            fetch('/api/positions')
                .then(r => r.json())
                .then(data => {
                    positions = data.positions;
                    renderPositions();
                    document.getElementById('active-positions').textContent = positions.length;
                });
        }
        
        function renderPositions() {
            const container = document.getElementById('positions-container');
            
            if (positions.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon"><svg class="icon" aria-hidden="true"><use href="#i-pin"></use></svg></div>
                        <div class="empty-state-text">No positions added yet</div>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = '<div class="positions-list">' +
                positions.map((pos, i) => `
                    <div class="position-item">
                        <div class="position-info">
                            <div class="position-name">${pos.name}</div>
                            <div class="position-details">
                                (${pos.x}, ${pos.y}) · ${pos.button || 'left'} · ${pos.click_type || 'single'}${pos.click_type==='hold' ? ' ' + (pos.hold_duration||0)+'s' : ''} · every ${pos.interval}s · jitter ${pos.pos_jitter ?? 3}px/${Math.round(((pos.time_jitter ?? 0.1)*100))}% · clicks ${pos.clicks || 0}
                            </div>
                        </div>
                        <div class="position-actions">
                            <button class="icon-btn btn-edit" onclick="editPosition(${i})" title="Edit"><svg class="icon" aria-hidden="true"><use href="#i-edit"></use></svg></button>
                            <button class="icon-btn btn-delete" onclick="deletePosition(${i})" title="Delete"><svg class="icon" aria-hidden="true"><use href="#i-trash"></use></svg></button>
                        </div>
                    </div>
                `).join('') +
                '</div>';
        }
        
        function startClicking() {
            const start_delay = parseInt(document.getElementById('start-delay').value || '0');
            fetch('/api/start', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({start_delay})})
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('start-btn').disabled = true;
                        document.getElementById('pause-btn').disabled = false;
                        document.getElementById('stop-btn').disabled = false;
                        startUpdates();
                    } else {
                        alert(data.message);
                    }
                });
        }
        
        function pauseClicking() {
            fetch('/api/pause', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    const btn = document.getElementById('pause-btn');
                    setPauseButton(data.paused);
                });
        }

        function setPauseButton(isPaused) {
            const btn = document.getElementById('pause-btn');
            if (isPaused) {
                btn.innerHTML = '<svg class="icon" aria-hidden="true"><use href="#i-play"></use></svg>Resume';
            } else {
                btn.innerHTML = '<svg class="icon" aria-hidden="true"><use href="#i-pause"></use></svg>Pause';
            }
        }
        
        function stopClicking() {
            fetch('/api/stop', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('pause-btn').disabled = true;
                    document.getElementById('stop-btn').disabled = true;
                    setPauseButton(false);
                    stopUpdates();
                });
        }
        
        function updateVariance() {
            const variance_enabled = document.getElementById('variance-enabled').checked;
            fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({variance_enabled})
            });
        }

        function saveSettings() {
            const variance_enabled = document.getElementById('variance-enabled').checked;
            const global_jitter_px = parseInt(document.getElementById('global-jitter-px').value || '0');
            const global_jitter_time = parseFloat(document.getElementById('global-jitter-time').value || '0') / 100.0;
            const max_total_clicks = document.getElementById('max-total-clicks').value;
            const max_session_minutes = document.getElementById('max-session-mins').value;
            const default_start_delay = parseInt(document.getElementById('start-delay').value || '0');
            const pauseKey = (document.getElementById('hotkey-pause').value || 'p').toLowerCase();
            const stopKey = (document.getElementById('hotkey-stop').value || 'q').toLowerCase();
            fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    variance_enabled,
                    global_jitter_px,
                    global_time_jitter: global_jitter_time,
                    max_total_clicks: max_total_clicks === '' ? null : parseInt(max_total_clicks),
                    max_session_minutes: max_session_minutes === '' ? null : parseInt(max_session_minutes),
                    default_start_delay,
                    hotkeys: { pause: pauseKey, stop: stopKey }
                })
            }).then(() => loadStatsOnce());
        }

        function resetStats() {
            fetch('/api/reset-stats', {method: 'POST'})
                .then(() => loadStatsOnce());
        }

        function loadStatsOnce() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('variance-enabled').checked = !!data.variance_enabled;
                    document.getElementById('global-jitter-px').value = data.global_jitter_px ?? 3;
                    document.getElementById('global-jitter-time').value = Math.round(((data.global_time_jitter ?? 0.1) * 100));
                    document.getElementById('max-total-clicks').value = data.max_total_clicks ?? '';
                    document.getElementById('max-session-mins').value = data.max_session_minutes ?? '';
                    document.getElementById('start-delay').value = data.default_start_delay ?? 0;
                    document.getElementById('hotkey-pause').value = (data.hotkeys?.pause || 'p');
                    document.getElementById('hotkey-stop').value = (data.hotkeys?.stop || 'q');
                    document.getElementById('kbd-pause').textContent = (data.hotkeys?.pause || 'p').toUpperCase();
                    document.getElementById('kbd-stop').textContent = (data.hotkeys?.stop || 'q').toUpperCase();
                });
        }
        
        function startUpdates() {
            updateTimer = setInterval(() => {
                fetch('/api/stats')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('total-clicks').textContent = data.total_clicks;
                        document.getElementById('session-time').textContent = data.session_time;
                        
                        // Update button states based on server state
                        if (data.running !== undefined) {
                            document.getElementById('start-btn').disabled = data.running;
                            document.getElementById('pause-btn').disabled = !data.running;
                            document.getElementById('stop-btn').disabled = !data.running;
                            
                            setPauseButton(data.paused);
                            // Disable mutating controls while running
                            const disable = data.running;
                            const posContainer = document.getElementById('positions-container');
                            posContainer.querySelectorAll('.btn-edit,.btn-delete').forEach(b => b.disabled = disable);
                            const addButtons = [document.getElementById('add-position-btn'), document.getElementById('add-seq-btn')];
                            addButtons.forEach(btn => { if (btn) btn.disabled = disable; });
                            // Reflect settings
                            document.getElementById('variance-enabled').checked = !!data.variance_enabled;
                            document.getElementById('global-jitter-px').value = data.global_jitter_px ?? 3;
                            document.getElementById('global-jitter-time').value = Math.round(((data.global_time_jitter ?? 0.1) * 100));
                            document.getElementById('max-total-clicks').value = data.max_total_clicks ?? '';
                            document.getElementById('max-session-mins').value = data.max_session_minutes ?? '';
                            document.getElementById('start-delay').value = data.default_start_delay ?? 0;
                            document.getElementById('hotkey-pause').value = (data.hotkeys?.pause || 'p');
                            document.getElementById('hotkey-stop').value = (data.hotkeys?.stop || 'q');
                            document.getElementById('kbd-pause').textContent = (data.hotkeys?.pause || 'p').toUpperCase();
                            document.getElementById('kbd-stop').textContent = (data.hotkeys?.stop || 'q').toUpperCase();
                        }
                        
                        if (data.positions) {
                            positions = data.positions;
                            renderPositions();
                        }
                        
                        if (data.sequences) {
                            sequences = data.sequences;
                            renderSequences();
                        }
                    });
            }, 1000);
        }
        
        function stopUpdates() {
            if (updateTimer) {
                clearInterval(updateTimer);
            }
        }
        
        function saveConfig() {
            const name = prompt('Enter configuration name:');
            if (name) {
                fetch('/api/save-config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name})
                })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                });
            }
        }
        
        function loadConfig() {
            fetch('/api/configs')
                .then(r => r.json())
                .then(data => {
                    if (data.configs.length === 0) {
                        alert('No saved configurations found');
                        return;
                    }
                    const config = prompt('Available configs:\\n' + data.configs.join('\\n') + '\\n\\nEnter config name:');
                    if (config) {
                        fetch('/api/load-config', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({name: config})
                        })
                        .then(r => r.json())
                        .then(data => {
                            if (data.success) {
                                loadPositions();
                                alert('Configuration loaded');
                            } else {
                                alert(data.message);
                            }
                        });
                    }
                });
        }
        
        function triggerSequence(index) {
            fetch(`/api/trigger-sequence/${index}`, {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        console.log(`Triggered sequence ${index + 1}`);
                    }
                });
        }
        
        // Sequence Management Functions
        function showSequenceModal() {
            if (positions.length === 0) {
                alert('Please add at least one position first');
                return;
            }
            
            document.getElementById('sequence-modal').classList.add('active');
            document.getElementById('sequence-name').value = `Sequence ${sequences.length + 1}`;
            currentSequenceSteps = [];
            updateSequenceSteps();
        }
        
        function closeSequenceModal() {
            document.getElementById('sequence-modal').classList.remove('active');
        }
        
        function addSequenceStep() {
            document.getElementById('step-modal').classList.add('active');
            populatePositionsSelect();
            updateStepForm();
        }
        
        function closeStepModal() {
            document.getElementById('step-modal').classList.remove('active');
        }
        
        function toggleAutoInterval() {
            const enabled = document.getElementById('sequence-auto-enabled').checked;
            const group = document.getElementById('auto-interval-group');
            group.style.display = enabled ? 'block' : 'none';
        }
        
        function populatePositionsSelect() {
            const select = document.getElementById('step-position');
            select.innerHTML = '';
            
            positions.forEach((pos, i) => {
                const option = document.createElement('option');
                option.value = i;
                option.textContent = `${pos.name} (${pos.x}, ${pos.y})`;
                select.appendChild(option);
            });
        }
        
        function saveStep() {
            const positionIndex = parseInt(document.getElementById('step-position').value);
            const nextDelay = parseFloat(document.getElementById('step-next-delay').value);
            
            const step = {
                type: 'click',
                position_index: positionIndex,
                position_name: positions[positionIndex].name,
                next_delay: nextDelay
            };
            
            currentSequenceSteps.push(step);
            updateSequenceSteps();
            closeStepModal();
        }
        
        function updateSequenceSteps() {
            const container = document.getElementById('sequence-steps');
            
            if (currentSequenceSteps.length === 0) {
                container.innerHTML = `
                    <div class="empty-state" style="padding: 20px;">
                        <div class="empty-state-text">No steps added yet</div>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = '<div class="positions-list">' +
                currentSequenceSteps.map((step, i) => `
                    <div class="position-item">
                        <div class="position-info">
                            <div class="position-name">Step ${i + 1}: Click ${step.position_name}</div>
                            <div class="position-details">Then wait ${step.next_delay}s before next step</div>
                        </div>
                        <div class="position-actions">
                            <button class="icon-btn btn-delete" onclick="removeSequenceStep(${i})"><svg class="icon" aria-hidden="true"><use href="#i-trash"></use></svg></button>
                        </div>
                    </div>
                `).join('') +
                '</div>';
        }
        
        function removeSequenceStep(index) {
            currentSequenceSteps.splice(index, 1);
            updateSequenceSteps();
        }
        
        function saveSequence() {
            const name = document.getElementById('sequence-name').value;
            const key = document.getElementById('sequence-key').value;
            const autoEnabled = document.getElementById('sequence-auto-enabled').checked;
            const autoInterval = parseFloat(document.getElementById('sequence-auto-interval').value);
            
            if (!name.trim()) {
                alert('Please enter a sequence name');
                return;
            }
            
            if (currentSequenceSteps.length === 0) {
                alert('Please add at least one step');
                return;
            }
            
            fetch('/api/add-sequence', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name,
                    steps: currentSequenceSteps,
                    key: parseInt(key),
                    manual_trigger_only: !autoEnabled,
                    auto_interval: autoEnabled ? autoInterval : 0
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    loadSequences();
                    closeSequenceModal();
                }
            });
        }
        
        function loadSequences() {
            fetch('/api/sequences')
                .then(r => r.json())
                .then(data => {
                    sequences = data.sequences;
                    renderSequences();
                });
        }
        
        function renderSequences() {
            const container = document.getElementById('sequences-container');
            
            if (sequences.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon"><svg class="icon" aria-hidden="true"><use href="#i-loop"></use></svg></div>
                        <div class="empty-state-text">No sequences created yet</div>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = '<div class="positions-list">' +
                sequences.map((seq, i) => `
                    <div class="position-item">
                        <div class="position-info">
                            <div class="position-name">${seq.name}</div>
                            <div class="position-details">
                                Key: ${i + 1} | Steps: ${seq.steps.length} | Executions: ${seq.executions || 0} | 
                                ${seq.manual_trigger_only ? 'Manual Only' : 'Auto every ' + seq.auto_interval + 's'}
                            </div>
                        </div>
                        <div class="position-actions">
                            <button class="icon-btn btn-edit" onclick="testSequence(${i})" title="Test"><svg class="icon" aria-hidden="true"><use href="#i-play"></use></svg></button>
                            <button class="icon-btn" onclick="editSequence(${i})" title="Edit" style="background: #fff3e0; color: #ff9800;"><svg class="icon" aria-hidden="true"><use href="#i-edit"></use></svg></button>
                            <button class="icon-btn btn-delete" onclick="deleteSequence(${i})" title="Delete"><svg class="icon" aria-hidden="true"><use href="#i-trash"></use></svg></button>
                        </div>
                    </div>
                `).join('') +
                '</div>';
        }
        
        function testSequence(index) {
            triggerSequence(index);
        }
        
        function editSequence(index) {
            const seq = sequences[index];
            
            // Show sequence modal with existing values
            document.getElementById('sequence-modal').classList.add('active');
            document.getElementById('sequence-name').value = seq.name;
            document.getElementById('sequence-key').value = index + 1;
            
            // Set auto settings
            const isManual = !!seq.manual_trigger_only;
            document.getElementById('sequence-auto-enabled').checked = !isManual;
            if (!isManual) {
                document.getElementById('sequence-auto-interval').value = seq.auto_interval || 30;
            }
            toggleAutoInterval();
            
            // Load existing steps
            currentSequenceSteps = seq.steps.slice(); // Copy array
            updateSequenceSteps();
            
            // Change save function to update
            document.querySelector('#sequence-modal .btn-start').onclick = function() {
                updateSequence(index);
            };
        }
        
        function updateSequence(index) {
            const name = document.getElementById('sequence-name').value;
            const key = document.getElementById('sequence-key').value;
            const autoEnabled = document.getElementById('sequence-auto-enabled').checked;
            const autoInterval = parseFloat(document.getElementById('sequence-auto-interval').value);
            
            if (!name.trim()) {
                alert('Please enter a sequence name');
                return;
            }
            
            if (currentSequenceSteps.length === 0) {
                alert('Please add at least one step');
                return;
            }
            
            fetch(`/api/update-sequence/${index}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name,
                    steps: currentSequenceSteps,
                    key: parseInt(key),
                    manual_trigger_only: !autoEnabled,
                    auto_interval: autoEnabled ? autoInterval : 0
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    loadSequences();
                    closeSequenceModal();
                    // Reset save button
                    document.querySelector('#sequence-modal .btn-start').onclick = saveSequence;
                }
            });
        }
        
        function deleteSequence(index) {
            if (confirm('Delete this sequence?')) {
                fetch(`/api/delete-sequence/${index}`, {method: 'DELETE'})
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            loadSequences();
                        } else if (data.message) { alert(data.message); }
                    });
            }
        }
        
        // Load positions, sequences and settings on start
        loadPositions();
        loadSequences();
        loadStatsOnce();
    </script>
</body>
</html>
    '''

@app.route('/api/mouse-position')
def get_mouse_position():
    """Get current mouse position"""
    x, y = pyautogui.position()
    return jsonify({'x': x, 'y': y})

@app.route('/api/positions')
def get_positions():
    """Get all positions"""
    return jsonify({'positions': [
        {
            'name': p.get('name', f'Position {i+1}'),
            'x': p['position'][0],
            'y': p['position'][1],
            'interval': p['interval'],
            'clicks': p.get('clicks', 0),
            'button': p.get('button', 'left'),
            'click_type': p.get('click_type', 'single'),
            'hold_duration': p.get('hold_duration', 0.0),
            'pos_jitter': p.get('pos_jitter', clicker.global_jitter_px),
            'time_jitter': p.get('time_jitter', clicker.global_time_jitter)
        } for i, p in enumerate(clicker.positions)
    ]})

@app.route('/api/add-position', methods=['POST'])
def add_position():
    """Add a new position"""
    if clicker.running:
        return jsonify({'success': False, 'message': 'Cannot add while running'}), 400
    data = request.json or {}
    position = {
        'name': data.get('name', f'Position {len(clicker.positions)+1}'),
        'position': (int(data.get('x', 0)), int(data.get('y', 0))),
        'interval': float(data.get('interval', 1.0)),
        'button': data.get('button', 'left'),  # left, middle, right
        'click_type': data.get('click_type', 'single'),  # single, double, hold
        'hold_duration': float(data.get('hold_duration', 0.0)),
        'pos_jitter': int(data.get('pos_jitter', clicker.global_jitter_px)),
        'time_jitter': float(data.get('time_jitter', clicker.global_time_jitter)),
        'enabled': True,
        'clicks': 0
    }
    with clicker.lock:
        clicker.positions.append(position)
    return jsonify({'success': True})

@app.route('/api/update-position/<int:index>', methods=['PUT'])
def update_position(index):
    """Update a position"""
    if clicker.running:
        return jsonify({'success': False, 'message': 'Cannot edit while running'}), 400
    if 0 <= index < len(clicker.positions):
        data = request.json or {}
        with clicker.lock:
            clicker.positions[index].update({
                'name': data.get('name', clicker.positions[index].get('name')),
                'position': (int(data.get('x', clicker.positions[index]['position'][0])), int(data.get('y', clicker.positions[index]['position'][1]))),
                'interval': float(data.get('interval', clicker.positions[index]['interval'])),
                'button': data.get('button', clicker.positions[index].get('button', 'left')),
                'click_type': data.get('click_type', clicker.positions[index].get('click_type', 'single')),
                'hold_duration': float(data.get('hold_duration', clicker.positions[index].get('hold_duration', 0.0))),
                'pos_jitter': int(data.get('pos_jitter', clicker.positions[index].get('pos_jitter', clicker.global_jitter_px))),
                'time_jitter': float(data.get('time_jitter', clicker.positions[index].get('time_jitter', clicker.global_time_jitter))),
            })
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/delete-position/<int:index>', methods=['DELETE'])
def delete_position(index):
    """Delete a position"""
    if clicker.running:
        return jsonify({'success': False, 'message': 'Cannot delete while running'}), 400
    if 0 <= index < len(clicker.positions):
        with clicker.lock:
            del clicker.positions[index]
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/start', methods=['POST'])
def start_clicking():
    """Start auto-clicking"""
    if not clicker.positions:
        return jsonify({'success': False, 'message': 'No positions added'})
    
    if clicker.running:
        return jsonify({'success': False, 'message': 'Already running'})
    
    # Prepare run flags
    clicker.running = True
    clicker.paused = False
    clicker.stop_event.clear()
    clicker.pause_event.set()

    # Determine delay
    req = request.json or {}
    start_delay = int(req.get('start_delay') or clicker.default_start_delay or 0)

    def _start_threads():
        # session start time begins when threads start
        clicker.session_start_time = time.time()
        # Clear any leftover lists
        clicker.threads.clear()
        clicker.sequence_threads.clear()
        # Start clicking threads
        for i, position in enumerate(clicker.positions):
            if position.get('enabled', True):
                th = threading.Thread(target=click_loop, args=(i,))
                th.daemon = True
                th.start()
                clicker.threads.append(th)
        # Start automatic sequence threads
        for i, sequence in enumerate(clicker.sequences):
            if not sequence.get('manual_trigger_only', True) and sequence.get('auto_interval', 0) > 0:
                th = threading.Thread(target=auto_sequence_loop, args=(i,))
                th.daemon = True
                th.start()
                clicker.sequence_threads.append(th)

    if start_delay > 0:
        threading.Timer(start_delay, _start_threads).start()
    else:
        _start_threads()

    return jsonify({'success': True, 'scheduled_in': start_delay})

@app.route('/api/pause', methods=['POST'])
def pause_clicking():
    """Pause/resume clicking"""
    if clicker.paused:
        clicker.pause_event.set()
        clicker.paused = False
    else:
        clicker.pause_event.clear()
        clicker.paused = True
    
    return jsonify({'success': True, 'paused': clicker.paused})

@app.route('/api/stop', methods=['POST'])
def stop_clicking():
    """Stop clicking"""
    clicker.running = False
    clicker.stop_event.set()
    clicker.pause_event.set()
    
    # Wait for threads
    for thread in clicker.threads:
        thread.join(timeout=1)
    for thread in clicker.sequence_threads:
        thread.join(timeout=1)
    
    clicker.threads.clear()
    clicker.sequence_threads.clear()
    clicker.session_start_time = None
    clicker.paused = False
    
    return jsonify({'success': True})

@app.route('/api/stats')
def get_stats():
    """Get current statistics"""
    session_time = "00:00:00"
    if clicker.session_start_time:
        elapsed = int(time.time() - clicker.session_start_time)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        session_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    return jsonify({
        'total_clicks': clicker.total_clicks,
        'session_time': session_time,
        'running': clicker.running,
        'paused': clicker.paused,
        'variance_enabled': clicker.variance_enabled,
        'global_jitter_px': clicker.global_jitter_px,
        'global_time_jitter': clicker.global_time_jitter,
        'max_total_clicks': clicker.max_total_clicks,
        'max_session_minutes': clicker.max_session_minutes,
        'default_start_delay': clicker.default_start_delay,
        'hotkeys': clicker.hotkeys,
        'positions': [
            {
                'name': p.get('name', f'Position {i+1}'),
                'x': p['position'][0],
                'y': p['position'][1],
                'interval': p['interval'],
                'clicks': p.get('clicks', 0)
            } for i, p in enumerate(clicker.positions)
        ],
        'sequences': [
            {
                'name': s.get('name', f'Sequence {i+1}'),
                'steps': len(s.get('steps', [])),
                'executions': s.get('executions', 0),
                'auto_interval': s.get('auto_interval', 0),
                'manual_only': s.get('manual_trigger_only', True)
            } for i, s in enumerate(clicker.sequences)
        ]
    })

@app.route('/api/variance', methods=['POST'])
def set_variance():
    """Set variance enabled/disabled"""
    clicker.variance_enabled = request.json['enabled']
    return jsonify({'success': True})

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update global settings including variance, jitter, limits and hotkeys"""
    data = request.json or {}
    with clicker.lock:
        if 'variance_enabled' in data:
            clicker.variance_enabled = bool(data['variance_enabled'])
        if 'global_jitter_px' in data:
            try:
                clicker.global_jitter_px = max(0, int(data['global_jitter_px']))
            except Exception:
                pass
        if 'global_time_jitter' in data:
            try:
                jt = float(data['global_time_jitter'])
                clicker.global_time_jitter = max(0.0, jt)
            except Exception:
                pass
        if 'max_total_clicks' in data:
            mtc = data['max_total_clicks']
            clicker.max_total_clicks = int(mtc) if mtc not in (None, '', 'null') else None
        if 'max_session_minutes' in data:
            msm = data['max_session_minutes']
            clicker.max_session_minutes = int(msm) if msm not in (None, '', 'null') else None
        if 'default_start_delay' in data:
            try:
                clicker.default_start_delay = max(0, int(data['default_start_delay']))
            except Exception:
                pass
        if 'hotkeys' in data and isinstance(data['hotkeys'], dict):
            hk = data['hotkeys']
            pause = str(hk.get('pause', clicker.hotkeys['pause'])).lower()[:1] or clicker.hotkeys['pause']
            stop = str(hk.get('stop', clicker.hotkeys['stop'])).lower()[:1] or clicker.hotkeys['stop']
            clicker.hotkeys = {'pause': pause, 'stop': stop}
    return jsonify({'success': True})

@app.route('/api/reset-stats', methods=['POST'])
def reset_stats():
    """Reset total and per-position click counters"""
    with clicker.lock:
        clicker.total_clicks = 0
        for p in clicker.positions:
            p['clicks'] = 0
    return jsonify({'success': True})

@app.route('/api/save-config', methods=['POST'])
def save_config():
    """Save configuration"""
    name = request.json['name']
    # Sanitize filename to avoid traversal/invalid chars
    name = re.sub(r'[^A-Za-z0-9._-]', '_', name).strip('_') or 'config'
    filename = os.path.join(CONFIG_DIR, f"{name}.json")
    
    with clicker.lock:
        data = {
            'positions': clicker.positions,
            'sequences': clicker.sequences,
            'variance_enabled': clicker.variance_enabled,
            'global_jitter_px': clicker.global_jitter_px,
            'global_time_jitter': clicker.global_time_jitter,
            'max_total_clicks': clicker.max_total_clicks,
            'max_session_minutes': clicker.max_session_minutes,
            'default_start_delay': clicker.default_start_delay,
            'hotkeys': clicker.hotkeys,
            'timestamp': datetime.now().isoformat()
        }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    return jsonify({'success': True, 'message': f'Configuration saved as {name}'})

@app.route('/api/configs')
def get_configs():
    """Get list of saved configs"""
    configs = []
    for filename in os.listdir(CONFIG_DIR):
        if filename.endswith('.json'):
            configs.append(filename[:-5])
    return jsonify({'configs': configs})

@app.route('/api/load-config', methods=['POST'])
def load_config():
    """Load configuration"""
    name = request.json['name']
    name = re.sub(r'[^A-Za-z0-9._-]', '_', name).strip('_') or 'config'
    filename = os.path.join(CONFIG_DIR, f"{name}.json")
    
    if not os.path.exists(filename):
        return jsonify({'success': False, 'message': 'Configuration not found'})
    
    with open(filename, 'r') as f:
        data = json.load(f)
    
    with clicker.lock:
        clicker.positions = data.get('positions', [])
        clicker.sequences = data.get('sequences', [])
        clicker.variance_enabled = data.get('variance_enabled', True)
        clicker.global_jitter_px = data.get('global_jitter_px', 3)
        clicker.global_time_jitter = data.get('global_time_jitter', 0.10)
        clicker.max_total_clicks = data.get('max_total_clicks')
        clicker.max_session_minutes = data.get('max_session_minutes')
        clicker.default_start_delay = data.get('default_start_delay', 0)
        hk = data.get('hotkeys') or {}
        # sanitize hotkeys to single lower-case chars
        clicker.hotkeys = {
            'pause': str(hk.get('pause', 'p')).lower()[:1] or 'p',
            'stop': str(hk.get('stop', 'q')).lower()[:1] or 'q',
        }
    
    return jsonify({'success': True})

@app.route('/api/sequences')
def get_sequences():
    """Get all sequences"""
    return jsonify({'sequences': clicker.sequences})

@app.route('/api/add-sequence', methods=['POST'])
def add_sequence():
    """Add a new sequence"""
    if clicker.running:
        return jsonify({'success': False, 'message': 'Cannot add while running'}), 400
    data = request.json or {}
    sequence = {
        'name': data.get('name', f'Sequence {len(clicker.sequences)+1}'),
        'steps': data.get('steps', []),
        'manual_trigger_only': data.get('manual_trigger_only', True),
        'auto_interval': data.get('auto_interval', 0),
        'executions': 0
    }
    with clicker.lock:
        clicker.sequences.append(sequence)
    
    # Start automatic sequence thread if needed
    if not sequence['manual_trigger_only'] and sequence['auto_interval'] > 0:
        seq_index = len(clicker.sequences) - 1
        thread = threading.Thread(target=auto_sequence_loop, args=(seq_index,))
        thread.daemon = True
        thread.start()
        clicker.sequence_threads.append(thread)
        
    return jsonify({'success': True})

@app.route('/api/update-sequence/<int:index>', methods=['PUT'])
def update_sequence(index):
    """Update a sequence"""
    if clicker.running:
        return jsonify({'success': False, 'message': 'Cannot edit while running'}), 400
    if 0 <= index < len(clicker.sequences):
        data = request.json or {}
        with clicker.lock:
            clicker.sequences[index].update({
                'name': data.get('name', clicker.sequences[index].get('name')),
                'steps': data.get('steps', clicker.sequences[index].get('steps', [])),
                'manual_trigger_only': data.get('manual_trigger_only', clicker.sequences[index].get('manual_trigger_only', True)),
                'auto_interval': data.get('auto_interval', clicker.sequences[index].get('auto_interval', 0))
            })
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/delete-sequence/<int:index>', methods=['DELETE'])
def delete_sequence(index):
    """Delete a sequence"""
    if clicker.running:
        return jsonify({'success': False, 'message': 'Cannot delete while running'}), 400
    if 0 <= index < len(clicker.sequences):
        with clicker.lock:
            del clicker.sequences[index]
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/trigger-sequence/<int:index>', methods=['POST'])
def trigger_sequence(index):
    """Manually trigger a sequence"""
    if 0 <= index < len(clicker.sequences):
        thread = threading.Thread(target=execute_sequence, args=(index, True))
        thread.daemon = True
        thread.start()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Sequence not found'})

def click_loop(position_index):
    """Clicking loop for a position"""
    position = clicker.positions[position_index]
    
    while not clicker.stop_event.is_set():
        clicker.pause_event.wait()
        
        if clicker.stop_event.is_set():
            break
        
        # Snapshot current settings
        btn = position.get('button', 'left')
        ctype = position.get('click_type', 'single')
        hold = float(position.get('hold_duration', 0.0) or 0.0)
        base_x, base_y = position['position']
        base_interval = float(position.get('interval', 1.0) or 1.0)
        # Apply variance
        x, y = base_x, base_y
        if clicker.variance_enabled:
            jitter_px = int(position.get('pos_jitter', clicker.global_jitter_px) or 0)
            if jitter_px > 0:
                x += random.randint(-jitter_px, jitter_px)
                y += random.randint(-jitter_px, jitter_px)
        try:
            if ctype == 'double':
                pyautogui.click(x=x, y=y, button=btn, clicks=2, interval=0.05)
            elif ctype == 'hold' and hold > 0:
                pyautogui.mouseDown(x=x, y=y, button=btn)
                time.sleep(hold)
                pyautogui.mouseUp(x=x, y=y, button=btn)
            else:
                pyautogui.click(x=x, y=y, button=btn)
            # Update statistics
            position['clicks'] = position.get('clicks', 0) + 1
            clicker.total_clicks += 1
        except Exception as e:
            logging.warning(f"Click error at ({x}, {y}): {e}")
        
        # Check global limits
        if clicker.max_total_clicks is not None and clicker.total_clicks >= clicker.max_total_clicks:
            logging.info("Max total clicks reached; stopping")
            clicker.running = False
            clicker.stop_event.set()
            clicker.pause_event.set()
            break
        if clicker.max_session_minutes is not None and clicker.session_start_time:
            if (time.time() - clicker.session_start_time) >= clicker.max_session_minutes * 60:
                logging.info("Max session minutes reached; stopping")
                clicker.running = False
                clicker.stop_event.set()
                clicker.pause_event.set()
                break
        
        # Sleep with optional variance
        interval = base_interval
        if clicker.variance_enabled:
            tj = float(position.get('time_jitter', clicker.global_time_jitter) or 0.0)
            if tj > 0:
                interval *= random.uniform(max(0.0, 1 - tj), 1 + tj)
        time.sleep(max(0.0, interval))

def setup_global_keyboard_listener():
    """Setup global keyboard listener that works even when browser isn't focused"""
    def on_key_press(key):
        try:
            if hasattr(key, 'char') and key.char:
                char = key.char.lower()
                
                if char == clicker.hotkeys.get('pause', 'p'):
                    # Toggle pause/resume
                    if clicker.running:
                        if clicker.paused:
                            clicker.pause_event.set()
                            clicker.paused = False
                            print("\n[P] Resumed clicking")
                        else:
                            clicker.pause_event.clear()
                            clicker.paused = True
                            print("\n[P] Paused clicking")
                
                elif char == clicker.hotkeys.get('stop', 'q'):
                    # Stop everything
                    if clicker.running:
                        print("\n[Q] Stopping auto-clicker...")
                        clicker.running = False
                        clicker.stop_event.set()
                        clicker.pause_event.set()
                        
                        # Wait for threads
                        for thread in clicker.threads:
                            thread.join(timeout=1)
                        for thread in clicker.sequence_threads:
                            thread.join(timeout=1)
                            
                        clicker.threads.clear()
                        clicker.sequence_threads.clear()
                        print("[Q] Auto-clicker stopped")
                
                elif char in '123456789':
                    # Trigger sequence
                    seq_index = int(char) - 1
                    if seq_index < len(clicker.sequences):
                        print(f"\n[{char}] Triggering sequence: {clicker.sequences[seq_index]['name']}")
                        thread = threading.Thread(target=execute_sequence, args=(seq_index, True))
                        thread.daemon = True
                        thread.start()
                        clicker.sequence_threads.append(thread)
                    
        except AttributeError:
            pass
    
    listener = keyboard.Listener(on_press=on_key_press)
    listener.daemon = True
    listener.start()
    print("Global keyboard listener started (pause={}, stop={}, 1-9=sequences)".format(
        clicker.hotkeys.get('pause', 'p').upper(), clicker.hotkeys.get('stop', 'q').upper()
    ))

def auto_sequence_loop(sequence_index):
    """Automatic sequence loop that runs on a timer"""
    if sequence_index >= len(clicker.sequences):
        return
        
    sequence = clicker.sequences[sequence_index]
    interval = sequence.get('auto_interval', 30)
    
    print(f"Starting automatic sequence: {sequence['name']} (every {interval}s)")
    
    while not clicker.stop_event.is_set():
        # Wait for the interval or stop
        if clicker.stop_event.wait(timeout=interval):
            break
        # Skip if not running or paused
        if not clicker.running or clicker.paused or clicker.stop_event.is_set():
            continue
        # Execute sequence
        execute_sequence(sequence_index, manual_trigger=False)

def execute_sequence(sequence_index, manual_trigger=False):
    """Execute a sequence of clicks"""
    if sequence_index >= len(clicker.sequences):
        return
    
    sequence = clicker.sequences[sequence_index]
    
    # If this is manual trigger only and not a manual trigger, skip
    if sequence.get('manual_trigger_only', True) and not manual_trigger:
        return
    
    try:
        print(f"Executing sequence: {sequence['name']}")
        
        for i, step in enumerate(sequence['steps']):
            if clicker.stop_event.is_set():
                break
            # Respect pause
            clicker.pause_event.wait()
            
            # All steps are clicks with next_delay
            pos_index = step['position_index']
            if pos_index < len(clicker.positions):
                position = clicker.positions[pos_index]
                base_x, base_y = position['position']
                x, y = base_x, base_y
                if clicker.variance_enabled:
                    jitter_px = int(position.get('pos_jitter', clicker.global_jitter_px) or 0)
                    if jitter_px > 0:
                        x += random.randint(-jitter_px, jitter_px)
                        y += random.randint(-jitter_px, jitter_px)
                btn = position.get('button', 'left')
                ctype = position.get('click_type', 'single')
                hold = float(position.get('hold_duration', 0.0) or 0.0)
                try:
                    if ctype == 'double':
                        pyautogui.click(x=x, y=y, button=btn, clicks=2, interval=0.05)
                    elif ctype == 'hold' and hold > 0:
                        pyautogui.mouseDown(x=x, y=y, button=btn)
                        time.sleep(hold)
                        pyautogui.mouseUp(x=x, y=y, button=btn)
                    else:
                        pyautogui.click(x=x, y=y, button=btn)
                    clicker.total_clicks += 1
                    print(f"  Step {i+1}: Clicked {position.get('name', 'position')} at ({x}, {y})")
                except Exception as e:
                    print(f"  Step {i+1}: Click error at ({x}, {y}): {e}")
                
                # Wait before next step (unless this is the last step)
                if i < len(sequence['steps']) - 1:
                    delay = step.get('next_delay', 0)
                    if delay > 0:
                        if clicker.variance_enabled:
                            tj = float(position.get('time_jitter', clicker.global_time_jitter) or 0.0)
                            if tj > 0:
                                delay *= random.uniform(max(0.0, 1 - tj), 1 + tj)
                        # Sleep in small increments to remain pause/stop responsive
                        end_time = time.time() + max(0.0, delay)
                        while time.time() < end_time and not clicker.stop_event.is_set():
                            # If paused, wait
                            if clicker.paused:
                                clicker.pause_event.wait()
                            time.sleep(0.01)
                
        # Update execution count
        sequence['executions'] = sequence.get('executions', 0) + 1
        print(f"Sequence '{sequence['name']}' completed (execution #{sequence['executions']})")
        
    except Exception as e:
        print(f"Error executing sequence {sequence_index}: {e}")

if __name__ == '__main__':
    print("\n" + "="*50)
    print("AUTO CLICKER WEB INTERFACE")
    print("="*50)
    print("\nStarting web server...")
    print("\n✅ Open your browser to: http://localhost:8080")
    print("\n🎹 Global keyboard shortcuts:")
    print(f"   {clicker.hotkeys.get('pause','p').upper()} = Pause/Resume clicking")
    print(f"   {clicker.hotkeys.get('stop','q').upper()} = Stop clicking")
    print("   1-9 = Trigger sequences")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Start global keyboard listener
    setup_global_keyboard_listener()
    
    # Auto-open browser
    threading.Timer(1.5, lambda: webbrowser.open('http://localhost:8080')).start()
    
    # Run server
    app.run(debug=False, port=8080, host='127.0.0.1')
