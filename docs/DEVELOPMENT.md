## Maintenance
    
    **Database Maintenance**
    This bot uses a SQLite database (`felipe.db`) to store user preferences and other data. Over time, this database can grow and may require maintenance.
    
    - **Backup:** Regularly back up the `felipe.db` file to prevent data loss.
    - **Vacuum:** To optimize the database and reduce its size, you can run the `VACUUM;` SQL command. This can be done using the `sqlite3` command-line tool: `sqlite3 felipe.db "VACUUM;"`
    
    **Code Maintenance/Improvement**
    - Pull latest changes from the main branch regularly.
    - Run tests after pulling changes to ensure everything works as expected.
    - Consider contributing to the project if you find bugs or have ideas for improvements.
    
    **Bot Hosting**
    The bot is designed to be hosted on a server where it can run continuously.
    
    1.  **Environment:** Ensure you have Python 3.8+ and the required dependencies installed (`pip install -r requirements.txt`).
    2.  **Configuration:**
        * Copy `.env.example` to `.env`.
        * Fill in the `DISCORD_TOKEN` and `DATABASE_PATH` in the `.env` file. `DATABASE_PATH` should be the path to your `felipe.db` file (e.g., `/home/user/felipe/felipe.db`).
        * You might need to create `felipe.db` initially if it doesn't exist (`sqlite3 felipe.db "VACUUM;"` can create it).
    3.  **Running:**
        * You can run the bot directly using `python main.py`.
        * For continuous operation, it's recommended to use a process manager like `systemd` or `supervisor`, or run it within a `screen` or `tmux` session.
    
        Example `systemd` service file (`felipe.service`):
        ```ini
        [Unit]
        Description=Felipe Discord Bot
        After=network.target
    
        [Service]
        User=your_user
        WorkingDirectory=/path/to/felipe
        ExecStart=/usr/bin/python3 /path/to/felipe/main.py
        Restart=always
    
        [Install]
        WantedBy=multi-user.target
        ```
        Replace `your_user` and `/path/to/felipe` accordingly. Then enable and start the service: `sudo systemctl enable felipe.service && sudo systemctl start felipe.service`.
    
    
