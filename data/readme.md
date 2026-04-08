Folder struture

- *source* contains two subfolders
    - *automatic* Folder for automatically downloaded files. Files in this folder
    are not under version control
    - *manual* Inputs manually created. These files are under version control. Sources
    are documented in the Readme.md in the folder
- *normalized* Downloaded data after some initial normalization of the column names
and types. Files in this folder are automatically created and not under version control
- *extracted* Data extracted from normalized data. These data are meant to mimic the
final tables. Files in this folder are automatically created and mostly not under version
control.