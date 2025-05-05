# Advanced Auto Clicker

A flexible auto-clicking tool that can click multiple buttons at custom intervals and execute sequences of clicks with precise timing.

## Features

- Click multiple buttons at customizable intervals
- Create sequences of clicks that maintain precise timing relationships
- Set up buttons that are only used in sequences (not clicked on a timer)
- Save and load configurations for quick setup
- Pause/resume clicking with a single key press
- Trigger sequences manually with number keys

## Requirements

- Python 3.6 or higher
- Dependencies listed in `requirements.txt`

## Installation

1. Clone this repository:
   ```
   git clone [repository-url]
   ```

2. Navigate to the project directory:
   ```
   cd [repository-name]
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the auto clicker:
   ```
   python auto_clicker.py
   ```

2. Follow the on-screen instructions to:
   - Load a saved configuration or create a new one
   - Set up buttons and their clicking intervals
   - Create sequences of clicks (optional)

3. Keyboard controls during execution:
   - `q` - Exit the program
   - `p` - Pause/resume regular clicks
   - `s` - Save the current configuration
   - `1-9` - Trigger sequences (if configured)

## How Saving Works

The auto clicker saves:
- Button positions (x, y coordinates)
- Button intervals (how often each button is clicked)
- Sequence-only button settings
- Sequence configurations (steps, timing, trigger settings)

Saved configurations are stored as JSON files in the `saved_configs` directory.

## Cross-Platform Support

This tool works on:
- Windows
- macOS
- Linux

## Tips

- For the most accurate button positions, position your mouse precisely over the center of each button when setting up
- Use sequence-only buttons for actions that should only happen as part of a sequence
- Save your configurations with descriptive names for easy identification
- If a sequence needs precise timing, set it to pause regular clicks during execution

## Troubleshooting

- If clicks aren't registering, try running the program with administrator privileges
- On macOS, you may need to grant accessibility permissions to Terminal/Python
- On Windows, some applications may block automated clicks for security reasons
