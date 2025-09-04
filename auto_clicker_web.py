#!/usr/bin/env python3
"""
Auto Clicker Web - Beautiful web-based interface
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import pyautogui
import threading
import time
import json
import os
import random
import webbrowser
from datetime import datetime
from pynput import keyboard

# Disable PyAutoGUI's fail-safe
pyautogui.FAILSAFE = False

app = Flask(__name__)
CORS(app)

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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖱️ Auto Clicker Pro</h1>
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
            <button class="btn btn-start" id="start-btn" onclick="startClicking()">
                ▶️ Start
            </button>
            <button class="btn btn-pause" id="pause-btn" onclick="pauseClicking()" disabled>
                ⏸️ Pause
            </button>
            <button class="btn btn-stop" id="stop-btn" onclick="stopClicking()" disabled>
                ⏹️ Stop
            </button>
        </div>
        
        <div class="content">
            <div class="section">
                <div class="section-header">
                    <h2 class="section-title">Click Positions</h2>
                    <button class="add-btn" onclick="showAddModal()">
                        ➕ Add Position
                    </button>
                </div>
                
                <div id="positions-container">
                    <div class="empty-state">
                        <div class="empty-state-icon">📍</div>
                        <div class="empty-state-text">No positions added yet</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-header">
                    <h2 class="section-title">Sequences</h2>
                    <button class="add-btn" onclick="showSequenceModal()">
                        ➕ Add Sequence
                    </button>
                </div>
                
                <div id="sequences-container">
                    <div class="empty-state">
                        <div class="empty-state-icon">🔄</div>
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
                    <div style="margin-top: 15px;">
                        <strong>Global Keyboard Shortcuts:</strong><br>
                        <kbd>P</kbd> = Pause/Resume | <kbd>Q</kbd> = Stop | <kbd>1-9</kbd> = Trigger Sequences
                    </div>
                    <div class="checkbox-group">
                        <button class="add-btn" onclick="saveConfig()">💾 Save Config</button>
                        <button class="add-btn" onclick="loadConfig()" style="margin-left: 10px;">📁 Load Config</button>
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
            
            <div class="form-actions">
                <button class="btn" onclick="retakePosition()" id="retake-btn" style="display: none;">🔄 Retake</button>
                <button class="btn btn-start" onclick="savePosition()" id="save-btn" disabled>💾 Save</button>
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
                <button class="btn btn-start" onclick="saveSequence()">💾 Save Sequence</button>
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
            
            if (!name.trim()) {
                alert('Please enter a position name');
                return;
            }
            
            fetch('/api/add-position', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, x, y, interval})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    loadPositions();
                    closeModal();
                }
            });
        }
        
        function editPosition(index) {
            const pos = positions[index];
            
            // Pre-fill the add modal with existing values
            document.getElementById('add-modal').classList.add('active');
            document.getElementById('position-name').value = pos.name;
            document.getElementById('position-x').value = pos.x;
            document.getElementById('position-y').value = pos.y;
            document.getElementById('position-interval').value = pos.interval;
            
            // Show as captured already - DISABLE capture mode for editing
            captured = true;
            captureMode = false;  // Important: disable Enter key capture
            document.getElementById('capture-status').textContent = 'Position loaded for editing';
            document.getElementById('capture-status').style.color = '#4CAF50';
            document.getElementById('save-btn').disabled = false;
            document.getElementById('retake-btn').style.display = 'inline-block';
            
            // Set up Enter key listener for edit mode (different behavior)
            document.addEventListener('keydown', handleEditKeyPress);
            
            // Change save function to update instead of create
            const saveBtn = document.getElementById('save-btn');
            saveBtn.onclick = function() {
                updatePosition(index);
            };
        }
        
        function updatePosition(index) {
            const name = document.getElementById('position-name').value;
            const x = parseInt(document.getElementById('position-x').value);
            const y = parseInt(document.getElementById('position-y').value);
            const interval = parseFloat(document.getElementById('position-interval').value);
            
            if (!name.trim()) {
                alert('Please enter a position name');
                return;
            }
            
            fetch(`/api/update-position/${index}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, x, y, interval})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    loadPositions();
                    closeModal();
                    // Reset save button for normal use
                    document.getElementById('save-btn').onclick = savePosition;
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
                        }
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
                        <div class="empty-state-icon">📍</div>
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
                                Position: (${pos.x}, ${pos.y}) | Interval: ${pos.interval}s | Clicks: ${pos.clicks || 0}
                            </div>
                        </div>
                        <div class="position-actions">
                            <button class="icon-btn btn-edit" onclick="editPosition(${i})" title="Edit">✏️</button>
                            <button class="icon-btn btn-delete" onclick="deletePosition(${i})" title="Delete">🗑️</button>
                        </div>
                    </div>
                `).join('') +
                '</div>';
        }
        
        function startClicking() {
            fetch('/api/start', {method: 'POST'})
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
                    if (data.paused) {
                        btn.textContent = '▶️ Resume';
                    } else {
                        btn.textContent = '⏸️ Pause';
                    }
                });
        }
        
        function stopClicking() {
            fetch('/api/stop', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('pause-btn').disabled = true;
                    document.getElementById('stop-btn').disabled = true;
                    document.getElementById('pause-btn').textContent = '⏸️ Pause';
                    stopUpdates();
                });
        }
        
        function updateVariance() {
            const enabled = document.getElementById('variance-enabled').checked;
            fetch('/api/variance', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({enabled})
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
                            
                            if (data.paused) {
                                document.getElementById('pause-btn').textContent = '▶️ Resume';
                            } else {
                                document.getElementById('pause-btn').textContent = '⏸️ Pause';
                            }
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
                            <button class="icon-btn btn-delete" onclick="removeSequenceStep(${i})">🗑️</button>
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
                        <div class="empty-state-icon">🔄</div>
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
                                ${seq.manual_only ? 'Manual Only' : 'Auto every ' + seq.auto_interval + 's'}
                            </div>
                        </div>
                        <div class="position-actions">
                            <button class="icon-btn btn-edit" onclick="testSequence(${i})" title="Test">▶️</button>
                            <button class="icon-btn" onclick="editSequence(${i})" title="Edit" style="background: #fff3e0; color: #ff9800;">✏️</button>
                            <button class="icon-btn btn-delete" onclick="deleteSequence(${i})" title="Delete">🗑️</button>
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
            const isManual = seq.manual_only;
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
                        }
                    });
            }
        }
        
        // Load positions and sequences on start
        loadPositions();
        loadSequences();
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
            'clicks': p.get('clicks', 0)
        } for i, p in enumerate(clicker.positions)
    ]})

@app.route('/api/add-position', methods=['POST'])
def add_position():
    """Add a new position"""
    data = request.json
    position = {
        'name': data['name'],
        'position': (data['x'], data['y']),
        'interval': data['interval'],
        'enabled': True,
        'clicks': 0
    }
    clicker.positions.append(position)
    return jsonify({'success': True})

@app.route('/api/update-position/<int:index>', methods=['PUT'])
def update_position(index):
    """Update a position"""
    if 0 <= index < len(clicker.positions):
        data = request.json
        clicker.positions[index].update({
            'name': data['name'],
            'position': (data['x'], data['y']),
            'interval': data['interval']
        })
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/delete-position/<int:index>', methods=['DELETE'])
def delete_position(index):
    """Delete a position"""
    if 0 <= index < len(clicker.positions):
        del clicker.positions[index]
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/start', methods=['POST'])
def start_clicking():
    """Start auto-clicking"""
    if not clicker.positions:
        return jsonify({'success': False, 'message': 'No positions added'})
    
    if clicker.running:
        return jsonify({'success': False, 'message': 'Already running'})
    
    clicker.running = True
    clicker.paused = False
    clicker.stop_event.clear()
    clicker.pause_event.set()
    clicker.session_start_time = time.time()
    
    # Start clicking threads
    for i, position in enumerate(clicker.positions):
        if position['enabled']:
            thread = threading.Thread(target=click_loop, args=(i,))
            thread.daemon = True
            thread.start()
            clicker.threads.append(thread)
    
    # Start automatic sequence threads
    for i, sequence in enumerate(clicker.sequences):
        if not sequence.get('manual_trigger_only', True) and sequence.get('auto_interval', 0) > 0:
            thread = threading.Thread(target=auto_sequence_loop, args=(i,))
            thread.daemon = True
            thread.start()
            clicker.sequence_threads.append(thread)
    
    return jsonify({'success': True})

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
    
    clicker.threads.clear()
    clicker.session_start_time = None
    
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

@app.route('/api/save-config', methods=['POST'])
def save_config():
    """Save configuration"""
    name = request.json['name']
    filename = os.path.join(CONFIG_DIR, f"{name}.json")
    
    data = {
        'positions': clicker.positions,
        'sequences': clicker.sequences,
        'variance_enabled': clicker.variance_enabled,
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
    filename = os.path.join(CONFIG_DIR, f"{name}.json")
    
    if not os.path.exists(filename):
        return jsonify({'success': False, 'message': 'Configuration not found'})
    
    with open(filename, 'r') as f:
        data = json.load(f)
    
    clicker.positions = data.get('positions', [])
    clicker.sequences = data.get('sequences', [])
    clicker.variance_enabled = data.get('variance_enabled', True)
    
    return jsonify({'success': True})

@app.route('/api/sequences')
def get_sequences():
    """Get all sequences"""
    return jsonify({'sequences': clicker.sequences})

@app.route('/api/add-sequence', methods=['POST'])
def add_sequence():
    """Add a new sequence"""
    data = request.json
    sequence = {
        'name': data['name'],
        'steps': data['steps'],
        'manual_trigger_only': data.get('manual_trigger_only', True),
        'auto_interval': data.get('auto_interval', 0),
        'executions': 0
    }
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
    if 0 <= index < len(clicker.sequences):
        data = request.json
        clicker.sequences[index].update({
            'name': data['name'],
            'steps': data['steps'],
            'manual_trigger_only': data.get('manual_trigger_only', True),
            'auto_interval': data.get('auto_interval', 0)
        })
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/delete-sequence/<int:index>', methods=['DELETE'])
def delete_sequence(index):
    """Delete a sequence"""
    if 0 <= index < len(clicker.sequences):
        del clicker.sequences[index]
        return jsonify({'success': True})
    return jsonify({'success': False})

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
        
        # Click with optional variance
        x, y = position['position']
        if clicker.variance_enabled:
            x += random.randint(-3, 3)
            y += random.randint(-3, 3)
        
        try:
            pyautogui.click(x, y)
            # Update statistics
            position['clicks'] = position.get('clicks', 0) + 1
            clicker.total_clicks += 1
        except Exception as e:
            print(f"Click error at ({x}, {y}): {e}")
            # Continue running despite click errors
        
        # Sleep with optional variance
        interval = position['interval']
        if clicker.variance_enabled:
            interval *= random.uniform(0.9, 1.1)
        
        time.sleep(interval)

def setup_global_keyboard_listener():
    """Setup global keyboard listener that works even when browser isn't focused"""
    def on_key_press(key):
        try:
            if hasattr(key, 'char') and key.char:
                char = key.char.lower()
                
                if char == 'p':
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
                
                elif char == 'q':
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
    print("Global keyboard listener started (P=pause, Q=stop, 1-9=sequences)")

def auto_sequence_loop(sequence_index):
    """Automatic sequence loop that runs on a timer"""
    if sequence_index >= len(clicker.sequences):
        return
        
    sequence = clicker.sequences[sequence_index]
    interval = sequence.get('auto_interval', 30)
    
    print(f"Starting automatic sequence: {sequence['name']} (every {interval}s)")
    
    while not clicker.stop_event.is_set():
        # Wait for the interval
        if clicker.stop_event.wait(timeout=interval):
            break
            
        # Execute the sequence if clicker is running
        if clicker.running and not clicker.stop_event.is_set():
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
            
            # All steps are clicks with next_delay
            pos_index = step['position_index']
            if pos_index < len(clicker.positions):
                position = clicker.positions[pos_index]
                x, y = position['position']
                
                # Apply variance if enabled
                if clicker.variance_enabled:
                    x += random.randint(-3, 3)
                    y += random.randint(-3, 3)
                
                try:
                    pyautogui.click(x, y)
                    clicker.total_clicks += 1
                    print(f"  Step {i+1}: Clicked {position.get('name', 'position')} at ({x}, {y})")
                except Exception as e:
                    print(f"  Step {i+1}: Click error at ({x}, {y}): {e}")
                
                # Wait before next step (unless this is the last step)
                if i < len(sequence['steps']) - 1:
                    delay = step.get('next_delay', 0)
                    if delay > 0:
                        if clicker.variance_enabled:
                            delay *= random.uniform(0.9, 1.1)
                        time.sleep(delay)
                
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
    print("   P = Pause/Resume clicking")
    print("   Q = Stop clicking")
    print("   1-9 = Trigger sequences")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Start global keyboard listener
    setup_global_keyboard_listener()
    
    # Auto-open browser
    threading.Timer(1.5, lambda: webbrowser.open('http://localhost:8080')).start()
    
    # Run server
    app.run(debug=False, port=8080, host='127.0.0.1')