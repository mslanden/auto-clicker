#!/usr/bin/env python3
"""
Advanced Auto Clicker - A terminal program that clicks multiple buttons at user-defined intervals
and supports sequences of clicks. Can be easily stopped with the 'q' key.
"""

import pyautogui
import time
import random
import threading
import sys
import os
import signal
import json
import glob
from pynput import keyboard
from datetime import datetime

# Disable PyAutoGUI's fail-safe feature
pyautogui.FAILSAFE = False

# Global flags to control program execution
running = True
pause_regular_clicks = False

# Store button data (position, interval, click count)
buttons = []

# Store sequence data
sequences = []

# Lock for thread synchronization
print_lock = threading.Lock()

# Directory for saved configurations
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_configs")

# Ensure the config directory exists
os.makedirs(CONFIG_DIR, exist_ok=True)

def save_config(config_name=None):
    """Save the current configuration to a file"""
    # Create a configuration object
    config = {
        'buttons': [],
        'sequences': []
    }
    
    # Save button data (excluding click counts and runtime data)
    for button in buttons:
        button_data = {
            'position': button['position'],
            'interval': button['interval'],
            'name': button.get('name', ''),
            'is_sequence_only': button.get('is_sequence_only', False)
        }
        config['buttons'].append(button_data)
    
    # Save sequence data (excluding click counts and runtime data)
    for sequence in sequences:
        sequence_data = {
            'interval': sequence.get('interval', 5.0),
            'pause_regular': sequence.get('pause_regular', False),
            'manual_trigger_only': sequence.get('manual_trigger_only', False),
            'steps': []
        }
        
        # Save steps
        for step in sequence['steps']:
            step_data = {
                'button_name': step['button_name'],
                'position': step['position'],
                'delay': step.get('delay', 0.0)
            }
            sequence_data['steps'].append(step_data)
            
        config['sequences'].append(sequence_data)
    
    # Generate a filename if none provided
    if not config_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_name = f"config_{timestamp}"
    
    # Ensure the filename has the .json extension
    if not config_name.endswith('.json'):
        config_name += '.json'
    
    # Save to file
    config_path = os.path.join(CONFIG_DIR, config_name)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    return config_path

def load_config(config_path):
    """Load a configuration from a file"""
    global buttons, sequences
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Load button data
        buttons = []
        for button_data in config.get('buttons', []):
            button = {
                'position': button_data['position'],
                'interval': button_data['interval'],
                'name': button_data.get('name', ''),
                'is_sequence_only': button_data.get('is_sequence_only', False),
                'clicks': 0  # Initialize click count
            }
            buttons.append(button)
        
        # Load sequence data
        sequences = []
        for sequence_data in config.get('sequences', []):
            sequence = {
                'interval': sequence_data.get('interval', 5.0),
                'pause_regular': sequence_data.get('pause_regular', False),
                'manual_trigger_only': sequence_data.get('manual_trigger_only', False),
                'executions': 0,  # Initialize execution count
                'steps': []
            }
            
            # Load steps
            for step_data in sequence_data.get('steps', []):
                step = {
                    'button_name': step_data['button_name'],
                    'position': step_data['position'],
                    'delay': step_data.get('delay', 0.0),
                    'clicks': 0  # Initialize click count
                }
                sequence['steps'].append(step)
                
            sequences.append(sequence)
            
        return True
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return False

def list_saved_configs():
    """List all saved configurations"""
    config_files = glob.glob(os.path.join(CONFIG_DIR, "*.json"))
    configs = []
    
    for i, path in enumerate(config_files):
        filename = os.path.basename(path)
        # Get file creation/modification time
        mod_time = os.path.getmtime(path)
        mod_time_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
        
        # Try to get a summary of what's in the config
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                num_buttons = len(config.get('buttons', []))
                num_sequences = len(config.get('sequences', []))
                summary = f"{num_buttons} buttons, {num_sequences} sequences"
        except:
            summary = "(Error reading file)"
        
        configs.append({
            'index': i + 1,
            'filename': filename,
            'path': path,
            'modified': mod_time_str,
            'summary': summary
        })
    
    return configs

def stop_program():
    """Stop the program gracefully"""
    global running
    print("\n\nStopping auto clicker...")
    
    # Print statistics for each button
    print("\nRegular Button Click Statistics:")
    for i, button in enumerate(buttons):
        print(f"Button {i+1}: {button['clicks']} clicks")
    
    # Print statistics for each sequence
    if sequences:
        print("\nSequence Statistics:")
        for i, seq in enumerate(sequences):
            print(f"Sequence {i+1}: {seq['executions']} executions")
            for j, step in enumerate(seq['steps']):
                print(f"  Step {j+1} (Button {step['button_name']}): {step['clicks']} clicks")
    
    # Ask if user wants to save this configuration
    save_option = input("\nDo you want to save this configuration for future use? (y/n) [n]: ").strip().lower()
    if save_option == 'y':
        config_name = input("Enter a name for this configuration (or press Enter for auto-generated name): ").strip()
        config_path = save_config(config_name)
        print(f"Configuration saved to: {config_path}")
    
    running = False
    sys.exit(0)

def signal_handler(sig, frame):
    """Handle Ctrl+C to stop the program gracefully"""
    stop_program()
    
def execute_sequence(sequence_index, manual_trigger=False):
    """Execute a sequence of button clicks"""
    global pause_regular_clicks
    sequence = sequences[sequence_index]
    
    # If this is a manual trigger but the sequence is already running, just return
    if manual_trigger and hasattr(sequence, 'is_running') and sequence.get('is_running', False):
        with print_lock:
            print(f"\n\nSequence {sequence_index+1} is already running!")
        return
    
    # If this sequence should only be manually triggered and this is not a manual trigger, return
    if sequence.get('manual_trigger_only', False) and not manual_trigger:
        return
    
    # For manual triggers, just execute once
    if manual_trigger:
        try:
            # Mark sequence as running
            sequence['is_running'] = True
            
            # Check if we should pause regular clicks during sequence execution
            was_paused = pause_regular_clicks
            if sequence['pause_regular']:
                pause_regular_clicks = True
            
            with print_lock:
                print(f"\n\nExecuting Sequence {sequence_index+1}...")
            
            # Execute each step in the sequence
            for step_index, step in enumerate(sequence['steps']):
                if not running:
                    break
                    
                # Get the button position
                button_pos = step['position']
                
                # Add small random variation to position (±3 pixels)
                random_x = button_pos[0] + random.randint(-3, 3)
                random_y = button_pos[1] + random.randint(-3, 3)
                
                # Click at the position
                pyautogui.click(random_x, random_y)
                step['clicks'] += 1
                
                with print_lock:
                    print(f"Sequence {sequence_index+1}, Step {step_index+1} (Button {step['button_name']}): Clicked")
                
                # Wait for the specified delay before the next step
                if step_index < len(sequence['steps']) - 1:  # Don't wait after the last step
                    time.sleep(step['delay'])
            
            # Increment sequence execution counter
            sequence['executions'] += 1
            
            # Reset pause_regular_clicks if it was set by this sequence
            if sequence['pause_regular']:
                pause_regular_clicks = was_paused
            
            # Mark sequence as not running
            sequence['is_running'] = False
            
        except Exception as e:
            with print_lock:
                print(f"\nError executing sequence {sequence_index+1}: {e}")
            # Mark sequence as not running
            sequence['is_running'] = False
            # Reset pause state if needed
            if sequence['pause_regular']:
                pause_regular_clicks = was_paused
    else:
        # For automatic sequences, run in a loop
        while running:
            try:
                # Check if we should pause regular clicks during sequence execution
                was_paused = pause_regular_clicks
                if sequence['pause_regular']:
                    pause_regular_clicks = True
                
                with print_lock:
                    print(f"\n\nExecuting Sequence {sequence_index+1} (automatic)...")
                
                # Execute each step in the sequence
                for step_index, step in enumerate(sequence['steps']):
                    if not running:
                        break
                        
                    # Get the button position
                    button_pos = step['position']
                    
                    # Add small random variation to position (±3 pixels)
                    random_x = button_pos[0] + random.randint(-3, 3)
                    random_y = button_pos[1] + random.randint(-3, 3)
                    
                    # Click at the position
                    pyautogui.click(random_x, random_y)
                    step['clicks'] += 1
                    
                    with print_lock:
                        print(f"Sequence {sequence_index+1}, Step {step_index+1} (Button {step['button_name']}): Clicked")
                    
                    # Wait for the specified delay before the next step
                    if step_index < len(sequence['steps']) - 1:  # Don't wait after the last step
                        time.sleep(step['delay'])
                
                # Increment sequence execution counter
                sequence['executions'] += 1
                
                # Reset pause_regular_clicks if it was set
                if sequence['pause_regular']:
                    pause_regular_clicks = was_paused
                
                # Wait for the sequence interval before repeating
                time.sleep(sequence['interval'])
                
            except Exception as e:
                with print_lock:
                    print(f"\nError executing sequence {sequence_index+1}: {e}")
                time.sleep(1)

def on_key_press(key):
    """Handle key press events"""
    global pause_regular_clicks
    
    try:
        # Check if 'q' key is pressed to exit
        if key.char.lower() == 'q':
            print("\n\nQ key pressed. Exiting...")
            stop_program()
        
        # Check if 'p' key is pressed to toggle pause
        elif key.char.lower() == 'p':
            pause_regular_clicks = not pause_regular_clicks
            print(f"\n\nRegular clicks {'paused' if pause_regular_clicks else 'resumed'}")
        
        # Check if 's' key is pressed to save configuration
        elif key.char.lower() == 's':
            print("\n\nSaving configuration...")
            config_path = save_config()
            print(f"Configuration saved to: {os.path.basename(config_path)}")
        
        # Check if number keys 1-9 are pressed to trigger sequences
        elif key.char in [str(i) for i in range(1, 10)]:
            seq_index = int(key.char) - 1
            if seq_index < len(sequences):
                # Start the sequence in a new thread with manual_trigger=True
                seq_thread = threading.Thread(target=execute_sequence, args=(seq_index, True))
                seq_thread.daemon = True
                seq_thread.start()
                print(f"\n\nManually triggered Sequence {seq_index+1} with key {key.char}")
            
    except AttributeError:
        # Special keys like function keys don't have a char attribute
        pass
    return True  # Continue listening

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

def get_current_mouse_position():
    """Get the current mouse position"""
    return pyautogui.position()

def get_button_position(button_name, countdown=5):
    """Capture the mouse position for a button using a timer"""
    print(f"\n>>> SETUP: You have {countdown} seconds to position your mouse over {button_name} <<<")
    
    # Countdown timer
    for i in range(countdown, 0, -1):
        print(f"Time remaining: {i} seconds...")
        time.sleep(1)
    
    # Capture position
    pos = get_current_mouse_position()
    print(f"{button_name} position set to {pos}")
    return pos

def click_button(button_index):
    """Thread function to click a button at its specified interval"""
    button = buttons[button_index]
    
    # Skip sequence-only buttons (they shouldn't be clicked on a timer)
    if button.get('is_sequence_only', False):
        return
    
    # Skip buttons with interval=0 (they shouldn't be clicked on a timer)
    if button['interval'] <= 0:
        return
    
    while running:
        try:
            # Check if regular clicks are paused
            if not pause_regular_clicks:
                # Add small random variation to position (±3 pixels)
                random_x = button['position'][0] + random.randint(-3, 3)
                random_y = button['position'][1] + random.randint(-3, 3)
                
                # Click at the position
                pyautogui.click(random_x, random_y)
                button['clicks'] += 1
                
                # Print feedback (overwrite the same line)
                with print_lock:
                    # Only show non-sequence-only buttons in the status line
                    status_parts = []
                    for i, b in enumerate(buttons):
                        if not b.get('is_sequence_only', False):
                            status_parts.append(f"Button {i+1}: {b['clicks']}")
                    
                    status_line = " | ".join(status_parts)
                    sys.stdout.write(f"\r{status_line}")
                    sys.stdout.flush()
            
            # Wait according to the interval with small random variation (±10%)
            interval = button['interval']
            variation = interval * 0.1  # 10% variation
            sleep_time = interval - variation + (random.random() * variation * 2)
            time.sleep(max(0.1, sleep_time))  # Ensure minimum sleep time
            
        except Exception as e:
            with print_lock:
                print(f"\nError clicking button {button_index+1}: {e}")
            time.sleep(1)

def get_valid_number(prompt, min_val=1, max_val=100, default=None):
    """Get a valid number from the user"""
    while True:
        try:
            if default is not None:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if user_input == "":
                    return default
            else:
                user_input = input(f"{prompt}: ").strip()
                
            value = float(user_input)
            if value < min_val or value > max_val:
                print(f"Please enter a value between {min_val} and {max_val}")
                continue
            return value
        except ValueError:
            print("Please enter a valid number")

def setup_sequence_only_buttons():
    """Set up buttons that are only used in sequences (not clicked on a timer)"""
    global buttons
    
    # Ask if user wants to set up sequence-only buttons
    want_seq_buttons = input("\nDo you want to set up additional buttons that are ONLY used in sequences? (y/n) [n]: ").strip().lower()
    if want_seq_buttons != 'y':
        return
    
    # Get number of sequence-only buttons
    num_seq_buttons = int(get_valid_number("How many sequence-only buttons do you want to add", min_val=1, max_val=10, default=1))
    
    # Current number of buttons
    current_button_count = len(buttons)
    
    # Add sequence-only buttons
    for i in range(num_seq_buttons):
        button_num = current_button_count + i + 1
        print(f"\n--- Setting up Sequence-Only Button {button_num} ---")
        
        # Add a new button with is_sequence_only=True and interval=0 (not clicked on timer)
        buttons.append({
            'position': None,
            'interval': 0,  # 0 means it's not clicked on a timer
            'clicks': 0,
            'name': f"Button {button_num}",
            'is_sequence_only': True
        })
        
        # Get button position
        buttons[-1]['position'] = get_button_position(f"SEQUENCE-ONLY BUTTON {button_num}", countdown=7)
        
        print(f"Sequence-only Button {button_num} set up successfully.")

def setup_sequences():
    """Set up sequences of button clicks"""
    global sequences
    
    # Ask if user wants to set up sequences
    want_sequences = input("\nDo you want to set up click sequences? (y/n) [n]: ").strip().lower()
    if want_sequences != 'y':
        return
    
    # Set up sequence-only buttons first
    setup_sequence_only_buttons()
    
    # Get number of sequences
    num_sequences = int(get_valid_number("How many sequences do you want to set up", min_val=1, max_val=9, default=1))
    
    # Initialize sequences list
    sequences = [{
        'steps': [],
        'interval': 5.0,  # Default interval between sequence executions
        'executions': 0,
        'pause_regular': False,  # Whether to pause regular clicks during sequence execution
        'manual_trigger_only': False  # Whether this sequence only runs when manually triggered
    } for _ in range(num_sequences)]
    
    # Set up each sequence
    for i in range(num_sequences):
        print(f"\n--- Setting up Sequence {i+1} ---")
        
        # Ask if regular clicks should be paused during this sequence
        pause_option = input(f"Pause regular clicks during Sequence {i+1}? (y/n) [n]: ").strip().lower()
        sequences[i]['pause_regular'] = (pause_option == 'y')
        
        # Ask if this sequence should only be triggered manually
        manual_option = input(f"Should Sequence {i+1} only run when manually triggered? (y/n) [n]: ").strip().lower()
        sequences[i]['manual_trigger_only'] = (manual_option == 'y')
        
        # Get sequence interval if not manual trigger only
        if not sequences[i]['manual_trigger_only']:
            sequences[i]['interval'] = get_valid_number(
                f"How often to execute Sequence {i+1} (seconds)", 
                min_val=0.5, 
                max_val=300, 
                default=5.0
            )
        
        # Get number of steps in the sequence
        num_steps = int(get_valid_number(f"How many steps in Sequence {i+1}", min_val=1, max_val=20, default=2))
        
        # For each step, get the button name and delay
        for j in range(num_steps):
            print(f"\nStep {j+1} of Sequence {i+1}:")
            
            # Create a list of available buttons to choose from (all buttons, including sequence-only ones)
            button_options = [f"Button {k+1}" for k in range(len(buttons))]
            
            # Mark sequence-only buttons
            button_display = []
            for k, btn in enumerate(buttons):
                if btn.get('is_sequence_only', False):
                    button_display.append(f"Button {k+1} (sequence-only)")
                else:
                    button_display.append(f"Button {k+1}")
            
            print("Available buttons: " + ", ".join(button_display))
            
            # Get the button for this step
            button_choice = ""
            while not any(button_choice == f"Button {k+1}" for k in range(len(buttons))):
                button_choice = input(f"Which button for Step {j+1}? (e.g., 'Button 1'): ").strip()
                if not any(button_choice == f"Button {k+1}" for k in range(len(buttons))):
                    print(f"Invalid choice. Please select from: {', '.join(button_options)}")
            
            # Get the button index
            button_index = int(button_choice.split()[1]) - 1
            
            # Get the delay after this step
            delay = 0.0
            if j < num_steps - 1:  # Don't ask for delay after the last step
                delay = get_valid_number(
                    f"Delay after Step {j+1} (seconds)", 
                    min_val=0.1, 
                    max_val=10, 
                    default=0.5
                )
            
            # Add the step to the sequence
            sequences[i]['steps'].append({
                'button_name': button_choice,
                'position': buttons[button_index]['position'],
                'delay': delay,
                'clicks': 0
            })
        
        trigger_info = "only when you press" if sequences[i]['manual_trigger_only'] else "automatically and when you press"
        print(f"\nSequence {i+1} setup complete. It will run {trigger_info} the '{i+1}' key.")

def setup_new_config():
    """Set up a new configuration from scratch"""
    global buttons
    
    # Get number of buttons
    num_buttons = int(get_valid_number("How many buttons do you want to click", min_val=1, max_val=10, default=2))
    
    # Initialize buttons list
    buttons = [{'position': None, 'interval': 1.0, 'clicks': 0, 'name': f"Button {i+1}", 'is_sequence_only': False} for i in range(num_buttons)]
    
    # Get interval for each button
    for i in range(num_buttons):
        interval = get_valid_number(f"How often to click Button {i+1} (seconds)", min_val=0.1, max_val=60, default=1.0)
        buttons[i]['interval'] = interval
    
    print("\n>>> IMPORTANT INSTRUCTIONS <<<")
    print("1. The program will now ask you to position your mouse for each button")
    print("2. Switch to your target application when prompted")
    print("3. Position your mouse over each button when the countdown starts")
    print("4. After capturing all positions, you'll have the option to set up sequences")
    print("5. The program will automatically start clicking after setup")
    
    print("\nReady to capture button positions? Starting in 5 seconds...")
    time.sleep(5)
    
    # Get button positions
    for i in range(num_buttons):
        buttons[i]['position'] = get_button_position(f"BUTTON {i+1}", countdown=7)
        
    # Set up sequences after capturing all button positions
    setup_sequences()

def main():
    """Main function to run the auto clicker"""
    global buttons, sequences
    
    print("===== ADVANCED AUTO CLICKER =====")
    print("This program allows you to click multiple buttons at custom intervals")
    print("and set up sequences of clicks that maintain precise timing relationships.")
    
    print("\nControls:")
    print("- Press 'q' key anywhere to exit")
    print("- Press 'p' key to pause/resume regular clicks")
    print("- Press number keys (1-9) to trigger sequences")
    
    # Check if there are any saved configurations
    saved_configs = list_saved_configs()
    
    if saved_configs:
        print("\nSaved configurations found:")
        for config in saved_configs:
            print(f"{config['index']}. {config['filename']} - {config['summary']} (Modified: {config['modified']})")
        
        # Ask if user wants to load a saved configuration
        load_option = input("\nDo you want to load a saved configuration? (y/n) [n]: ").strip().lower()
        
        if load_option == 'y':
            while True:
                config_choice = input("Enter the number of the configuration to load (or 'n' for new): ").strip().lower()
                
                if config_choice == 'n':
                    setup_new_config()
                    break
                
                try:
                    choice_index = int(config_choice) - 1
                    if 0 <= choice_index < len(saved_configs):
                        config_path = saved_configs[choice_index]['path']
                        if load_config(config_path):
                            print(f"Configuration loaded successfully from: {saved_configs[choice_index]['filename']}")
                            break
                    else:
                        print("Invalid selection. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number or 'n'.")
        else:
            setup_new_config()
    else:
        print("\nNo saved configurations found. Setting up a new configuration.")
        setup_new_config()
    
    # The setup is now handled in setup_new_config() or by loading a saved configuration
    
    print("\n>>> Starting auto clicker in 3 seconds... <<<")
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    
    print("\nAuto clicker is now running!")
    print("-------------------------------------------")
    
    # Start keyboard listener
    listener = keyboard.Listener(on_press=on_key_press)
    listener.daemon = True
    listener.start()
    print("Keyboard listener started")
    print("- Press 'q' anywhere to exit")
    print("- Press 'p' to pause/resume regular clicks")
    
    # Start automatic sequences
    for i, sequence in enumerate(sequences):
        if not sequence.get('manual_trigger_only', False):
            seq_thread = threading.Thread(target=execute_sequence, args=(i, False))
            seq_thread.daemon = True
            seq_thread.start()
            print(f"Started automatic sequence thread for Sequence {i+1} (every {sequence['interval']} seconds)")
    
    # Create and start the clicking threads for regular buttons
    threads = []
    for i in range(len(buttons)):
        thread = threading.Thread(target=click_button, args=(i,))
        thread.daemon = True
        threads.append(thread)
        thread.start()
        
        # Only print for non-sequence-only buttons with interval > 0
        if not buttons[i].get('is_sequence_only', False) and buttons[i]['interval'] > 0:
            print(f"Started clicking thread for Button {i+1} (every {buttons[i]['interval']} seconds)")
    
    # Display sequence information if any were set up
    if sequences:
        print("\nSequences available:")
        for i, sequence in enumerate(sequences):
            steps_info = ", ".join([step['button_name'] for step in sequence['steps']])
            
            if sequence.get('manual_trigger_only', False):
                print(f"Sequence {i+1}: Press '{i+1}' key to trigger. Steps: {steps_info}")
                print(f"  Manual trigger only: Yes")
            else:
                print(f"Sequence {i+1}: Press '{i+1}' key to trigger. Steps: {steps_info}")
                print(f"  Automatic interval: {sequence['interval']} seconds")
                
            print(f"  Pauses regular clicks: {'Yes' if sequence['pause_regular'] else 'No'}")
            
    # Display sequence-only buttons if any were set up
    seq_only_buttons = [i+1 for i, b in enumerate(buttons) if b.get('is_sequence_only', False)]
    if seq_only_buttons:
        print("\nSequence-only buttons (not clicked on timer):")
        print(", ".join([f"Button {i}" for i in seq_only_buttons]))
    
    print("\nAll systems ready!")
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()
