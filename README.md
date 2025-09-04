# Auto Clicker Web

A powerful web-based auto clicker application with a beautiful interface for automating mouse clicks.

## Features

- **Web Interface**: Clean, modern web UI accessible via browser at `http://localhost:8080`
- **Multiple Click Positions**: Add unlimited click positions with custom intervals
- **Click Sequences**: Create complex click patterns with precise timing control
- **Anti-Detection**: Built-in position and timing variance to avoid detection
- **Global Hotkeys**: Control the clicker even when browser isn't focused
  - `P` - Pause/Resume
  - `Q` - Stop
  - `1-9` - Trigger sequences
- **Configuration Management**: Save and load click configurations
- **Real-time Statistics**: Track total clicks, session time, and active positions

## Migration from Previous Version

If you're updating from the terminal-based `auto_clicker.py` to the new web version:

1. **Backup your configurations**: Your old config files in `saved_configs/` will still work
2. **Uninstall old dependencies** (if you had a virtual environment):
   ```bash
   pip uninstall python-time
   ```
3. **Install new dependencies**: Follow the installation steps below to get Flask
4. **Run the new version**: Use `python auto_clicker_web.py` instead of `auto_clicker.py`

## Installation

### Prerequisites
- Python 3.6 or higher
- pip (Python package manager)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/mslanden/auto-clicker.git
cd auto-clicker
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### macOS Permissions
On macOS, you'll need to grant accessibility permissions:
1. Go to System Preferences > Security & Privacy > Privacy > Accessibility
2. Add Terminal (or your Python interpreter) to the allowed apps

## Usage

1. Start the application:
```bash
python auto_clicker_web.py
```

2. The web interface will automatically open in your browser at `http://localhost:8080`

3. **Add Click Positions**:
   - Click "Add Position"
   - Move your mouse to the desired location
   - Press ENTER to capture the position
   - Set the click interval
   - Save the position

4. **Create Sequences**:
   - Click "Add Sequence"
   - Add steps (click positions with delays)
   - Assign a trigger key (1-9)
   - Optional: Set automatic interval

5. **Start Clicking**:
   - Click the Start button
   - Use keyboard shortcuts for control
   - Monitor statistics in real-time

## Configuration Files

Configurations are saved in the `saved_configs/` directory as JSON files containing:
- Click positions
- Sequences
- Settings

## Important Notes

- **Local Only**: This application runs locally and cannot be deployed to cloud platforms like Vercel
- **System Access**: Requires direct access to mouse/keyboard hardware
- **Security**: The app disables PyAutoGUI's fail-safe for continuous operation

## Project Structure

```
auto-clicker/
├── auto_clicker_web.py    # Main application
├── requirements.txt       # Python dependencies
├── saved_configs/         # Configuration files
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Troubleshooting

- **Permission Denied**: Grant accessibility permissions to Python/Terminal
- **Port Already in Use**: Change the port in the last line of `auto_clicker_web.py`
- **Click Not Working**: Ensure the target window is not blocking automated input

## License

This project is for educational purposes. Use responsibly and in accordance with the terms of service of any applications you interact with
