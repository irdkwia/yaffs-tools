# yaffs-tools
Extract file system from YAFFS dumps

## extract.py
Extracts from a specified dump to a folder using a configuration file.
Sample configuration files can be found in `config`.

## detect.py
Tries to detect YAFFS partitions from a specified dump.
Needs a minimal configuration file (e.g. `config/config_mini.json`).
Returns in standard output the guessed `partitions` that should be in
the configuration file.

## listapps.py
Lists apps in dump in standard output.