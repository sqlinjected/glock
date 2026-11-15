# glock

Made this to keep my mouse on the game screen while playing LEGO Universe with two monitors.

## Run it

On Windows 10 or 11, open PowerShell in this folder and run the command below. You'll need Python 3.10 or newer with Tkinter.

```powershell
python glock.py
```

Leave `legouniverse.exe` selected, click **Start**, and open LEGO Universe. The mouse stays on the game's monitor while the game has focus. The lock follows the game if you move it to another screen.

**Alt+Tab** frees the mouse. **Ctrl+Alt+F10** pauses or resumes the lock. Right-click the cursor icon with the lock by the clock for **Settings**, **Pause**, or **Exit**. Check under the up arrow if you don't see it.

For another game, go to **Settings**, use **Browse** to pick its `.exe`, and click **Start**. This works in fullscreen, borderless, or windowed mode.

Settings are saved in the same folder as `glock.py`. You can also start it with `pythonw glock.py` to run it as a background app.
