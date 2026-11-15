# glock

Made this to keep my mouse on the monitor screen ``PRIMARILY`` while playing LEGO Universe with two monitors.

## Run it

On Windows 10 or 11, open PowerShell in this folder. Python 3.10 or newer with Tkinter is all you need.

```powershell
python glock.py
```

Leave `legouniverse.exe` selected, click **Start**, and open LEGO Universe. The boomchikaUI panel shows your connected screens and highlights the game monitor. The lock follows the game if you move it to another screen.

For another game, click **Browse**, pick its `.exe`, and click **Start** on your first run or **Apply** after that. You can use it in fullscreen, borderless, or windowed mode.

**Alt+Tab** frees the mouse. Use the panel or **Ctrl+Alt+F10** to pause or resume the lock. Closing the panel sends glock to the tray. Right-click the cursor-and-lock icon by the clock to open **Settings** again or choose **Exit**.

If you're updating, put the new files in the same folder as `GameCursorLock.settings` to keep your game selection.
