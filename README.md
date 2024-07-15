# Home Assistant Statistics Backup and Restore

This is a script to import a backup of Home Assistant's long-term statistics into a Home Assistant sqlite3 database. This might be useful in the event of the old database being lost.

## How to make a backup

Long-term statistics can be backed up at any time using the `sqlite3` command. First, SSH into Home Assistant and change to the `/config` directory. Then run

```bash
sqlite3 home-assistant_v2.db ".dump statistics_meta statistics " | sqlite3 statistics_backup.db
```

This produces a new sqlite database "statistics_backup.db" containing just the `statistics_meta` and `statistics` tables - i.e., a copy of the long-term statistics. 


## How to restore a backup

The reason restoring is complicated is that long-term statistics are referred to numerical ID. If you have a fresh Home Assistant database (e.g., because your old one was lost) and you want to import your long-term statistics, the numerical statistics IDs in the backup will not match the ones in your fresh database. For example, you might have a statistic for "sensor.tv_power" that has ID 389 in your backup, but ID 281 in your fresh database. Therefore, to import the backup, we need a script that cross-references the numerical IDs in the backup to the ones in the current database via their entity IDs ("sensor.tv_power" in the example above).

The python script in this repository can be run at the command line, and should be given a source database (e.g., the `statistics_backup.db` created above) and a target database (i.e., your current Home Assistant db). It will import each statistic from the source database into the target database, while taking care to remap the IDs as it goes.  When it encounters a stat in the old database that it can't find in the new one, it stops to ask for instructions on how to proceed (you can tell it to skip, or provide an entity ID that it should remap it to).

You can also do a dry run.

Stop Home Assistant:
```bash
ha core stop
```


Take a backup:

```bash
cp home-assistant_v2.db home-assistant_v2.db.bak
```

Either copy the script `import-long-term-stats.py` to the Home Assistant machine, or copy the backup and current databases to somewhere where you can run the script.

Do a dry-run
```bash
python import-long-term-stats.py statistics_backup.db home-assistant_v2.db --dry-run
```

Take note of output describing entities it can't find. You may want to make a list of new corresponding entities that you want it to remap these to. You can also choose to skip them all.

Run it for real
```bash
python import-long-term-stats.py statistics_backup.db assistant_v2.db
```

Restart Home Assistant
```bash
ha core start
```

At this point, the statistics in the backup should have been imported into the new database, and you should be able to view the old data in Home Assistant, e.g., in the energy dashboard.
