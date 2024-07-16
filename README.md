# Home Assistant Statistics Backup and Restore

> *Warning* This script is still under development and has a bug. Right now it can successfully import old statistics, but it causes large negative values to appear in the energy dashboard at the point in time where normal statistics start being generated after the backed up data. I'm working on it.

This is a script to import a backup of Home Assistant's long-term statistics into a Home Assistant sqlite3 database. This might be useful in the event of the old database being lost.

## How to make a backup

Long-term statistics can be backed up at any time using the `sqlite3` command. First, SSH into Home Assistant and change to the `/config` directory. Then run

```bash
sqlite3 home-assistant_v2.db ".dump statistics_meta statistics_short_term statistics" | sqlite3 statistics_backup.db
```

This produces a new sqlite database "statistics_backup.db" containing just the `statistics_meta`, `statistics_short_term` and `statistics` tables - i.e., a copy of the statistics. 


## How to restore a statistics backup

The reason restoring is complicated is that long-term statistics are referred to numerical ID. If you have a fresh Home Assistant database (e.g., because your old one was lost) and you want to import your long-term statistics, the numerical statistics IDs in the backup will not match the ones in your fresh database. For example, you might have a statistic for "sensor.tv_power" that has ID 389 in your backup, but ID 281 in your fresh database. Therefore, to import the backup, we need a script that cross-references the numerical IDs in the backup to the ones in the current database via their entity IDs ("sensor.tv_power" in the example above).

The python script in this repository can be run at the command line, and should be given a source database (e.g., the `statistics_backup.db` created above) and a target database (i.e., your current Home Assistant db). It will import each statistic from the source database into the target database, while taking care to remap the IDs as it goes.  When it encounters a stat in the old database that it can't find in the new one, it stops to ask for instructions on how to proceed (you can tell it to skip, or provide an entity ID that it should remap it to).

You can also do a dry run.

Stop Home Assistant:
```bash
ha core stop
```


Backup your current Home Assistant database, so you can start over is something goes wrong.

```bash
cp home-assistant_v2.db home-assistant_v2.db.bak
```

Doublecheck that your backup completed safely, and put the backup somewhere safe.

If you are restoring data into a fresh Home Assistant database, we must delete any interim statistics Home Assistant has written since the database was created. The reason for this is that a `sum` column is tracked for each entity in short term statistics (representing the all-time total of the statistic), which Home Assistant will have reset to 0 when it recreated the database. This column in the short-term table is used to update a corresponding `sum` column in the long-term `statistics` table during each statistics run. If we do not get rid of the interim statistics, the `sum` of each statistic will reset to 0, despite having large historical values. This will short up as massive negative spikes in the statistics values in the energy dashboard, for example.

To wipe the interim statistics, verified that your backup was successful, and run this command from the command line:

```bash
sqlite3 home-assistant_v2.db "delete from statistics_short_term; delete from statistics;"
```

Either copy the script `import-long-term-stats.py` to the Home Assistant machine, or copy the backup and current databases to somewhere where you can run the script.

Do a dry-run
```bash
python import-long-term-stats.py statistics_backup.db home-assistant_v2.db --dry-run
```

Take note of output describing entities it can't find. You may want to make a list of new corresponding entities that you want it to remap these to. You can also choose to skip them all.

Run it for real
```bash
python import-long-term-stats.py statistics_backup.db home-assistant_v2.db
```

Restart Home Assistant
```bash
ha core start
```

At this point, the statistics in the backup should have been imported into the new database, and you should be able to view the old data in Home Assistant, e.g., in the energy dashboard.
