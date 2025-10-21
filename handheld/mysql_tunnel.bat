@echo off
echo Starting MySQL SSH Tunnel to Raspberry Pi...
echo Connect MySQL Workbench to localhost:3307 while this is running
echo Press Ctrl+C to stop the tunnel
echo.
ssh -L 3307:localhost:3306 binslibal@192.168.50.149
pause