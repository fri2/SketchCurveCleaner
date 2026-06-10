# Sketch Curve Cleaner for Autodesk Fusion 360

## Version

Current version: **15.0.0**

**Sketch Curve Cleaner** is an Autodesk Fusion 360 add-in that helps preview and clean duplicated or overlapping sketch curves.

The source code, comments, installation documentation, and repository documentation are written in English.  
The Fusion 360 command UI is localized at runtime according to the language selected by the user in Fusion 360, when that language can be detected.

## Author

**RICHARD Francois**

## License

This project is licensed under **GPL-3.0-only**.

SPDX identifier:

```text
GPL-3.0-only
```

See the [`LICENSE`](LICENSE) file for the full license text.

## Features

The add-in provides a Fusion 360 command named:

```text
Clean Sketch Overlaps
```

The command includes:

- **Test**: preview the cleanup without applying permanent changes.
- **Apply**: apply the cleanup to the active or selected sketch.
- **Cancel**: close the command and remove the temporary preview.

The preview works by:

1. deleting any previous temporary preview curves;
2. analyzing the target sketch;
3. selecting the source curves that would be deleted or replaced;
4. drawing replacement curves as temporary construction geometry directly in the target sketch.

## Cleanup options

The command dialog includes these options:

- Delete exact duplicate curves.
- Split/merge partially overlapping straight lines.
- Split/merge partially overlapping circular curves: arcs and circles.
- Also delete projected/reference geometry.
- Merge/delete constrained or dimensioned geometry.
- Merge construction and normal geometry together.
- Set geometric tolerance in centimeters.

## Geometry support

### Exact duplicate detection

The add-in can detect exact or near-exact duplicates for:

- Lines
- Circles
- Arcs
- Ellipses
- Elliptical arcs
- Fitted splines

### Partial split/merge

The add-in can split/merge partially overlapping geometry for:

- Straight lines
- Circular arcs
- Circles

### Current limitations

Partial split/merge is not currently implemented for:

- Ellipses
- Elliptical arcs
- Splines

These entities are handled only as exact or near-exact duplicates.

## Safety defaults

By default, the add-in is conservative:

- projected/reference geometry is protected;
- constrained or dimensioned geometry is protected from merge/delete operations;
- construction geometry is kept separate from normal geometry.

You can override these behaviors in the command dialog.

Be careful when enabling the following options:

- **Also delete projected/reference geometry**
- **Merge/delete constrained or dimensioned geometry**
- **Merge construction and normal geometry together**

These options can affect design intent, projected associativity, constraints, or dimensions. Test on a copy of the design first.


## Correct Fusion 360 installation path on Windows

The correct Windows installation path for this add-in is:

```text
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\SketchCurveCleanerLocalizedAddIn
```

In other words, the complete add-in folder must be named:

```text
SketchCurveCleanerLocalizedAddIn
```

and placed inside:

```text
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns
```

Do not use the older/wrong path:

```text
%APPDATA%\Autodesk\Autodesk Fusion\API\AddIns
```

## Installation on Windows

1. Close Fusion 360.
2. Copy the full folder `SketchCurveCleanerLocalizedAddIn` to:

   ```text
   %APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns
   ```

3. Start Fusion 360.
4. Open:

   ```text
   Utilities > Scripts and Add-Ins > Add-Ins
   ```

5. Select `SketchCurveCleanerLocalizedAddIn`.
6. Click **Run**.
7. Enable **Run on Startup** if you want the command to be loaded automatically.

## Installation on macOS

1. Close Fusion 360.
2. Copy the full folder `SketchCurveCleanerLocalizedAddIn` to the Fusion 360 AddIns folder.

Typical location:

```text
~/Library/Application Support/Autodesk/Autodesk Fusion/API/AddIns
```

3. Start Fusion 360.
4. Open:

```text
Utilities > Scripts and Add-Ins > Add-Ins
```

5. Select `SketchCurveCleanerLocalizedAddIn`.
6. Click **Run**.
7. Enable **Run on Startup** if desired.

## Usage

1. Open a Fusion 360 design.
2. Edit the sketch you want to clean, or select a sketch in the browser.
3. Run **Clean Sketch Overlaps** from the toolbar.
4. Choose the cleanup options.
5. Click **Test** to preview the changes.
6. Review the selected curves and the temporary preview sketch.
7. Click **Apply** to modify the sketch, or **Cancel** to leave it unchanged.

## Localization

The code uses a small internal localization table.

Currently included UI languages:

- English
- French

English is used as fallback if Fusion 360's language cannot be detected.

The implementation attempts to read Fusion 360's user language through the application preferences. The command labels, option labels, result summaries, warnings, and messages are then selected from the localization dictionary.

## Repository structure

```text
SketchCurveCleanerLocalizedAddIn/
├── SketchCurveCleanerLocalizedAddIn.py
├── SketchCurveCleanerLocalizedAddIn.manifest
├── README.md
└── LICENSE
```

## Development notes

The Python source file is intentionally documented with detailed docstrings.

The comments and docstrings describe:

- the role of each major class;
- the role of each function;
- the parameters passed to functions;
- return values when applicable;
- the geometry planning flow;
- the preview flow;
- the Fusion 360 command registration flow.

The add-in is structured around a non-destructive planning step:

```text
Read command options
↓
Analyze the target sketch
↓
Build a CleanupPlan
↓
Preview the CleanupPlan
↓
Apply the CleanupPlan only if the user confirms
```

## Important technical notes

Fusion 360's API uses centimeters internally.

Default tolerance:

```python
DEFAULT_TOLERANCE_CM = 0.001
```

This corresponds to:

```text
0.001 cm = 0.01 mm
```

For low-precision imported DXF sketches, a larger tolerance may be useful, for example:

```text
0.01 cm = 0.1 mm
```

## Disclaimer

This add-in modifies sketch geometry. Always test on a copy of the design before using it on production work.

Projected geometry, constrained geometry, dimensions, and construction geometry may carry design intent. Enabling aggressive cleanup options can break that intent.


## Reliable construction-geometry preview

Version 11 deliberately avoids Custom Graphics and dialog SVG previews.

In practice, those preview methods can be invisible or misleading depending on
the Fusion 360 sketch editing context. Version 11 uses a more robust approach:

- curves that would be deleted or replaced are selected in the active sketch;
- replacement curves are created as temporary construction geometry directly in
  the target sketch;
- these temporary curves are marked with an internal Fusion attribute;
- they are automatically removed before a new **Test**, before **Apply**, on
  **Cancel**, and when the command closes.

This preview does not provide red/green coloring, but it is designed to be
visible and geometrically aligned with the actual sketch.


## Versioning

The add-in version is defined in the Python source:

```python
ADDIN_VERSION = "15.0.0"
```

The same version is also stored in the Fusion manifest file and displayed in the
Fusion 360 command dialog. This makes it easier to check which installed version
is currently running.




## Installation helper files

This repository/package keeps the installation helper files directly inside the
`SketchCurveCleanerLocalizedAddIn` folder:

```text
SketchCurveCleanerLocalizedAddIn/
├── SketchCurveCleanerLocalizedAddIn.py
├── SketchCurveCleanerLocalizedAddIn.manifest
├── README.md
├── LICENSE
├── .gitignore
├── install_to_fusion360.bat
├── uninstall_from_fusion360.bat
└── INSTALL.md
```

The installer copies only the real Fusion 360 add-in files.

The following helper files are **excluded** during installation and are not copied
to Fusion 360:

```text
install_to_fusion360.bat
uninstall_from_fusion360.bat
INSTALL.md
```

The final Fusion 360 installation path is:

```text
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\SketchCurveCleanerLocalizedAddIn
```
