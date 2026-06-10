# Sketch Curve Cleaner v22.0.0 - Installation

## Package layout

The installation helper files are stored directly inside:

```text
SketchCurveCleanerLocalizedAddIn
```

There is no separate `install/` subdirectory.

## Automatic installation

Run:

```text
SketchCurveCleanerLocalizedAddIn\install_to_fusion360.bat
```

The script copies the add-in to:

```text
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\SketchCurveCleanerLocalizedAddIn
```

The script deliberately excludes these helper files from the installed Fusion 360
folder:

```text
install_to_fusion360.bat
uninstall_from_fusion360.bat
INSTALL.md
```

## Manual installation

If you install manually, copy only the actual add-in files to:

```text
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\SketchCurveCleanerLocalizedAddIn
```

Do not copy:

```text
install_to_fusion360.bat
uninstall_from_fusion360.bat
INSTALL.md
```

## Uninstall

Run:

```text
SketchCurveCleanerLocalizedAddIn\uninstall_from_fusion360.bat
```

or delete manually:

```text
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\SketchCurveCleanerLocalizedAddIn
```


## External helper files

The source folder also contains:

```text
clean_svg.py
SVG_PRE_CLEANER.md
```

These files are kept in the same directory as the add-in source, but they are not
copied into the Fusion 360 AddIns folder by the installer.
